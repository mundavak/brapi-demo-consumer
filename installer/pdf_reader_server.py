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

try:
    import docx  # python-docx
except ImportError:
    docx = None

try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Configuration
PDF_SOURCE_DIR = os.getenv('PDF_SOURCE_DIR', '.')

app = Server("pdf-reader")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="extract_document_text",
            description="Extract text from PDF, DOCX, or TXT files",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the document file to read (supports .pdf, .docx, .txt)"
                    },
                    "page_range": {
                        "type": "string", 
                        "description": "Page range (e.g., '1-5' or 'all') - PDF only",
                        "default": "all"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="list_documents",
            description="List available document files (PDF, DOCX, TXT) in the source directory",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

async def extract_pdf_text(pdf_path, page_range):
    """Extract text from PDF file with OCR fallback for image-only pages"""
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
    total_pages = len(doc)  # Store before closing
    
    for page_num in pages:
        page = doc[page_num]
        text = page.get_text()
        has_images = len(page.get_images()) > 0
        ocr_used = False
        
        # If no text found but page has images, try OCR
        if not text.strip() and has_images and OCR_AVAILABLE:
            try:
                # Render page to image at 300 DPI for good OCR quality
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Run OCR
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text.strip():
                    text = ocr_text
                    ocr_used = True
            except Exception as ocr_error:
                text = f"[OCR Error: {str(ocr_error)}]"
        
        extracted_text += f"\n\n--- Page {page_num + 1} ---\n{text}"
        page_info.append({
            "page": page_num + 1,
            "text_length": len(text),
            "has_images": has_images,
            "ocr_used": ocr_used
        })
    
    doc.close()
    
    result = {
        "filename": pdf_path.name,
        "total_pages": total_pages,
        "extracted_pages": len(pages),
        "ocr_available": OCR_AVAILABLE,
        "page_info": page_info,
        "text": extracted_text.strip()
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def extract_docx_text(docx_path):
    """Extract text from DOCX file"""
    if docx is None:
        return [TextContent(type="text", text="Error: python-docx not installed. Run: pip install python-docx")]
    
    doc = docx.Document(str(docx_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)
    
    result = {
        "filename": docx_path.name,
        "paragraph_count": len(paragraphs),
        "text": text
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def extract_txt_text(txt_path):
    """Extract text from TXT file"""
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    result = {
        "filename": txt_path.name,
        "character_count": len(text),
        "text": text
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "list_documents":
        try:
            doc_extensions = ['*.pdf', '*.docx', '*.txt', '*.md']
            doc_files = []
            for ext in doc_extensions:
                doc_files.extend(Path(PDF_SOURCE_DIR).glob(ext))
            file_list = [{"name": f.name, "size": f.stat().st_size, "type": f.suffix[1:]} for f in doc_files]
            return [TextContent(
                type="text",
                text=json.dumps({"documents": file_list, "count": len(file_list)}, indent=2)
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing documents: {str(e)}")]
    
    elif name == "extract_document_text":
        filename = arguments.get("filename")
        page_range = arguments.get("page_range", "all")
        
        try:
            doc_path = Path(PDF_SOURCE_DIR) / filename
            if not doc_path.exists():
                return [TextContent(type="text", text=f"Document file not found: {filename}")]
            
            # Handle different file types
            if filename.lower().endswith('.pdf'):
                return await extract_pdf_text(doc_path, page_range)
            elif filename.lower().endswith('.docx'):
                return await extract_docx_text(doc_path)
            elif filename.lower().endswith(('.txt', '.md')):
                return await extract_txt_text(doc_path)
            else:
                return [TextContent(type="text", text=f"Unsupported file type: {filename}")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error extracting document: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())