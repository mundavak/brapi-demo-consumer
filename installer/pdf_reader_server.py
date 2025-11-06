#!/usr/bin/env python3
"""
MCP PDF Reader Server
Provides PDF reading capabilities for AI assistants via Model Context Protocol
"""

import os
import sys
import json
import fitz  # PyMuPDF
from pathlib import Path
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Tool, TextContent

# Configuration
PDF_SOURCE_DIR = os.getenv('PDF_SOURCE_DIR', '.')

app = Server("pdf-reader")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="extract_pdf_text",
            description="Extract text from PDF files",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the PDF file to read"
                    },
                    "page_range": {
                        "type": "string", 
                        "description": "Page range (e.g., '1-5' or 'all')",
                        "default": "all"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="list_pdfs",
            description="List available PDF files in the source directory",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "list_pdfs":
        try:
            pdf_files = list(Path(PDF_SOURCE_DIR).glob("*.pdf"))
            file_list = [{"name": f.name, "size": f.stat().st_size} for f in pdf_files]
            return [TextContent(
                type="text",
                text=json.dumps({"pdfs": file_list, "count": len(file_list)}, indent=2)
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing PDFs: {str(e)}")]
    
    elif name == "extract_pdf_text":
        filename = arguments.get("filename")
        page_range = arguments.get("page_range", "all")
        
        try:
            pdf_path = Path(PDF_SOURCE_DIR) / filename
            if not pdf_path.exists():
                return [TextContent(type="text", text=f"PDF file not found: {filename}")]
            
            doc = fitz.open(str(pdf_path))
            
            # Parse page range
            if page_range == "all":
                pages = range(len(doc))
            else:
                # Handle ranges like "1-5"
                if "-" in page_range:
                    start, end = map(int, page_range.split("-"))
                    pages = range(start-1, min(end, len(doc)))  # Convert to 0-based
                else:
                    page_num = int(page_range) - 1  # Convert to 0-based
                    pages = [page_num] if 0 <= page_num < len(doc) else []
            
            extracted_text = ""
            page_info = []
            
            for page_num in pages:
                page = doc[page_num]
                text = page.get_text()
                extracted_text += f"\n\n--- Page {page_num + 1} ---\n{text}"
                page_info.append({
                    "page": page_num + 1,
                    "text_length": len(text),
                    "has_images": len(page.get_images()) > 0
                })
            
            doc.close()
            
            result = {
                "filename": filename,
                "total_pages": len(doc),
                "extracted_pages": len(pages),
                "page_info": page_info,
                "text": extracted_text.strip()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error extracting PDF: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())