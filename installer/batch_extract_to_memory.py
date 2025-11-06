#!/usr/bin/env python3
"""
Batch Document Extraction to AI Memory
Extracts all documents from KnowledgeBase and stores them in H:\AiMemory
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from pdf_reader_server import call_tool

# Configuration
# Use /memory when running in Docker, H:/AiMemory when running locally
import os
if os.path.exists("/memory"):
    MEMORY_PATH = Path("/memory")
else:
    MEMORY_PATH = Path("H:/AiMemory")

DOCUMENTS_PATH = MEMORY_PATH / "documents"
INDEX_PATH = MEMORY_PATH / "index"

# Ensure directories exist
DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
INDEX_PATH.mkdir(parents=True, exist_ok=True)

async def extract_all_documents():
    """Extract all documents and save to AI Memory"""
    
    print("🔍 Discovering documents...")
    
    # Get list of all documents
    result = await call_tool('list_documents', {})
    data = json.loads(result[0].text)
    documents = data['documents']
    
    print(f"📚 Found {data['count']} documents to extract\n")
    
    # Create index
    index = {
        "extraction_date": datetime.now().isoformat(),
        "total_documents": data['count'],
        "documents": []
    }
    
    # Extract each document
    for i, doc in enumerate(documents, 1):
        filename = doc['name']
        file_type = doc['type']
        
        print(f"[{i}/{data['count']}] Extracting: {filename}")
        
        try:
            # Extract document
            result = await call_tool('extract_document_text', {
                'filename': filename,
                'page_range': 'all'
            })
            
            extracted_data = json.loads(result[0].text)
            
            # Determine output filename (replace extension with .txt)
            output_filename = Path(filename).stem + '.txt'
            output_path = DOCUMENTS_PATH / output_filename
            
            # Save extracted text
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"=" * 80 + "\n")
                f.write(f"Document: {filename}\n")
                f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                if file_type == 'pdf':
                    f.write(f"Total Pages: {extracted_data.get('total_pages', 'N/A')}\n")
                    f.write(f"OCR Used: {any(p.get('ocr_used', False) for p in extracted_data.get('page_info', []))}\n")
                
                f.write("=" * 80 + "\n\n")
                f.write(extracted_data['text'])
            
            # Add to index
            doc_info = {
                "original_filename": filename,
                "extracted_filename": output_filename,
                "file_type": file_type,
                "size_bytes": doc['size'],
                "extraction_path": str(output_path),
                "text_length": len(extracted_data['text'])
            }
            
            if file_type == 'pdf':
                doc_info['total_pages'] = extracted_data.get('total_pages', 0)
                doc_info['ocr_used'] = any(p.get('ocr_used', False) for p in extracted_data.get('page_info', []))
            
            index['documents'].append(doc_info)
            
            print(f"   ✅ Saved to: {output_filename}")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            index['documents'].append({
                "original_filename": filename,
                "error": str(e)
            })
    
    # Save index
    index_file = INDEX_PATH / f"document_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)
    
    # Save latest index
    latest_index = INDEX_PATH / "latest_index.json"
    with open(latest_index, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)
    
    print("\n" + "=" * 80)
    print("✅ Extraction Complete!")
    print("=" * 80)
    print(f"📁 Documents saved to: {DOCUMENTS_PATH}")
    print(f"📋 Index saved to: {index_file}")
    print(f"📊 Total documents: {len(index['documents'])}")
    print(f"📄 Successful extractions: {sum(1 for d in index['documents'] if 'error' not in d)}")
    print(f"❌ Failed extractions: {sum(1 for d in index['documents'] if 'error' in d)}")

if __name__ == "__main__":
    asyncio.run(extract_all_documents())
