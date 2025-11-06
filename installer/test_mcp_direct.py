#!/usr/bin/env python3
"""
Direct test script for MCP document reader
Tests the server functionality without MCP protocol overhead
"""

import asyncio
import json
import os
from pathlib import Path

# Set environment
os.environ['PDF_SOURCE_DIR'] = r'F:\TradingAgent\deaProjects\brapi-demo-consumer\KnowledgeBase'

# Import after setting env
from pdf_reader_server import call_tool

async def test_list_documents():
    """Test listing documents"""
    print("\n" + "="*60)
    print("TEST 1: Listing documents in KnowledgeBase")
    print("="*60)
    
    result = await call_tool('list_documents', {})
    data = json.loads(result[0].text)
    
    print(f"\nFound {data['count']} documents:")
    
    # Group by type
    by_type = {}
    for doc in data['documents']:
        doc_type = doc['type']
        if doc_type not in by_type:
            by_type[doc_type] = []
        by_type[doc_type].append(doc)
    
    for doc_type, docs in by_type.items():
        print(f"\n  {doc_type.upper()} files: {len(docs)}")
        for doc in docs[:3]:  # Show first 3 of each type
            size_mb = doc['size'] / (1024 * 1024)
            print(f"    - {doc['name'][:60]}... ({size_mb:.2f} MB)")
        if len(docs) > 3:
            print(f"    ... and {len(docs) - 3} more")
    
    return data

async def test_extract_pdf():
    """Test extracting text from a specific PDF"""
    print("\n" + "="*60)
    print("TEST 2: Extracting text from ICT Mentorship PDF (pages 1-2)")
    print("="*60)
    
    result = await call_tool('extract_document_text', {
        'filename': '443878056-ICT-Mentorship-Month-1-Notes.pdf',
        'page_range': '1-2'
    })
    
    data = json.loads(result[0].text)
    
    print(f"\nFilename: {data['filename']}")
    print(f"Total pages: {data['total_pages']}")
    print(f"Extracted pages: {data['extracted_pages']}")
    print(f"\nFirst 500 characters of extracted text:")
    print("-" * 60)
    print(data['text'][:500])
    print("-" * 60)
    
    return data

async def test_extract_bookmap_guide():
    """Test extracting text from Bookmap User Guide"""
    print("\n" + "="*60)
    print("TEST 3: Extracting from Bookmap User Guide (pages 1-3)")
    print("="*60)
    
    result = await call_tool('extract_document_text', {
        'filename': '430196357-Bookmap-User-Guide-6-1.pdf',
        'page_range': '1-3'
    })
    
    data = json.loads(result[0].text)
    
    print(f"\nFilename: {data['filename']}")
    print(f"Total pages: {data['total_pages']}")
    print(f"Extracted pages: {data['extracted_pages']}")
    
    for page in data['page_info']:
        print(f"  Page {page['page']}: {page['text_length']} chars, Images: {page['has_images']}")
    
    print(f"\nFirst 300 characters:")
    print("-" * 60)
    print(data['text'][:300])
    print("-" * 60)
    
    return data

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MCP Document Reader - Direct Function Test")
    print("="*60)
    
    try:
        # Test 1: List documents
        list_result = await test_list_documents()
        
        # Test 2: Extract ICT PDF
        ict_result = await test_extract_pdf()
        
        # Test 3: Extract Bookmap Guide
        bookmap_result = await test_extract_bookmap_guide()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print(f"\nSummary:")
        print(f"  - Documents found: {list_result['count']}")
        print(f"  - ICT PDF pages: {ict_result['total_pages']}")
        print(f"  - Bookmap Guide pages: {bookmap_result['total_pages']}")
        print(f"\n✅ MCP server is working correctly!")
        print(f"   Restart VS Code to enable Copilot integration.\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
