#!/usr/bin/env python3
import asyncio
import json
import sys
from pdf_reader_server import call_tool

async def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else '841225157-Quarterly-Theory.pdf'
    page_range = sys.argv[2] if len(sys.argv) > 2 else 'all'
    
    result = await call_tool('extract_document_text', {
        'filename': filename,
        'page_range': page_range
    })
    
    print(f"DEBUG - Result type: {type(result)}")
    print(f"DEBUG - Result length: {len(result)}")
    print(f"DEBUG - First item: {result[0]}")
    print(f"DEBUG - Text content: {result[0].text[:200]}")
    
    data = json.loads(result[0].text)
    
    print(f"📄 Filename: {data['filename']}")
    print(f"📖 Total Pages: {data['total_pages']}")
    print(f"📄 Extracted Pages: {data['extracted_pages']}")
    print("\n" + "="*80)
    print("CONTENT:")
    print("="*80 + "\n")
    print(data['text'])

if __name__ == "__main__":
    asyncio.run(main())
