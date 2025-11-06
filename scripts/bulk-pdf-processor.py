#!/usr/bin/env python3
"""
AI Helper for bulk PDF processing
Handles "read all PDFs" requests with intelligent categorization
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

KNOWLEDGE_BASE = "F:/TradingAgent/deaProjects/brapi-demo-consumer/KnowledgeBase"

def categorize_pdfs() -> Dict[str, List[str]]:
    """Categorize PDFs by type for intelligent processing"""
    categories = {
        "technical": [],
        "trading": [], 
        "programming": [],
        "database": [],
        "api": []
    }
    
    pdf_files = list(Path(KNOWLEDGE_BASE).glob("*.pdf"))
    
    for pdf in pdf_files:
        name = pdf.name.lower()
        
        if any(term in name for term in ["bookmap", "api", "java-developers"]):
            categories["technical"].append(str(pdf))
        elif any(term in name for term in ["ict", "order-flow", "trading", "spoofing", "volume"]):
            categories["trading"].append(str(pdf))
        elif any(term in name for term in ["python", "javascript", "powershell"]):
            categories["programming"].append(str(pdf))
        elif any(term in name for term in ["timescale", "redis", "postgresql", "sqlite"]):
            categories["database"].append(str(pdf))
        else:
            categories["api"].append(str(pdf))
    
    return categories

def extract_pdf_summary(pdf_path: str) -> Dict[str, Any]:
    """Extract summary info from a single PDF"""
    try:
        result = subprocess.run([
            "mcp-pdf", "ocr", pdf_path
        ], capture_output=True, text=True, cwd=KNOWLEDGE_BASE)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "file": data.get("file", ""),
                "pages": len(data.get("ocr_pages", [])),
                "word_count": data.get("word_count", 0),
                "first_page_preview": data.get("ocr_pages", [{}])[0].get("text", "")[:200] + "..." if data.get("ocr_pages") else ""
            }
    except Exception as e:
        return {"error": str(e)}
    
    return {"error": "Failed to process"}

def bulk_summarize_pdfs() -> Dict[str, Any]:
    """Generate bulk summary of all PDFs by category"""
    categories = categorize_pdfs()
    summary = {}
    
    for category, files in categories.items():
        summary[category] = []
        for pdf_path in files:
            pdf_summary = extract_pdf_summary(pdf_path)
            summary[category].append(pdf_summary)
    
    return summary

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        summary = bulk_summarize_pdfs()
        print(json.dumps(summary, indent=2))
    else:
        categories = categorize_pdfs()
        for cat, files in categories.items():
            print(f"{cat.upper()}: {len(files)} files")