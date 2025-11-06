#!/usr/bin/env python3
import asyncio
import json
from pdf_reader_server import call_tool

async def main():
    result = await call_tool('extract_document_text', {
        'filename': '841225157-Quarterly-Theory.pdf',
        'page_range': 'all'
    })
    
    data = json.loads(result[0].text)
    
    print("="*80)
    print("📄 QUARTERLY THEORY - ICT Trading Framework")
    print("="*80)
    print(f"\n📊 Document Info:")
    print(f"   • Total Pages: {data['total_pages']}")
    print(f"   • Extracted Pages: {data['extracted_pages']}")
    print(f"   • OCR Available: {data['ocr_available']}")
    print(f"\n{'='*80}\n")
    print(data['text'])
    print(f"\n{'='*80}")

if __name__ == "__main__":
    asyncio.run(main())
