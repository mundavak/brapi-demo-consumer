"""
Extract PDF content to AI Memory location for persistent storage and retrieval.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

try:
    import PyPDF2
except ImportError:
    print("ERROR: PyPDF2 not installed. Installing...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
    import PyPDF2


def extract_pdf_to_memory(pdf_path: str, memory_base: str = "H:/AiMemory"):
    """Extract PDF content and save to AI Memory location."""

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_dir = Path(memory_base) / "documents"
    index_dir = Path(memory_base) / "index"

    # Create directories
    output_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading PDF: {pdf_path}")

    # Extract text
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        page_count = len(reader.pages)

        for page_num, page in enumerate(reader.pages, 1):
            print(f"  Extracting page {page_num}/{page_count}...")
            text += f"\n\n--- Page {page_num} ---\n\n"
            text += page.extract_text()

    # Save to memory
    output_filename = pdf_path.stem + ".txt"
    output_file = output_dir / output_filename

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\n✓ Extracted {len(text):,} characters to: {output_file}")

    # Update index
    index_file = index_dir / "latest_index.json"
    try:
        with open(index_file, "r", encoding="utf-8") as f:
            index = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        index = {"documents": [], "last_updated": None}

    # Create document entry
    doc_entry = {
        "filename": pdf_path.name,
        "text_file": output_filename,
        "type": "pdf",
        "pages": page_count,
        "characters": len(text),
        "extracted": datetime.now().isoformat(),
        "source_path": str(pdf_path.absolute()),
        "memory_path": str(output_file.absolute()),
    }

    # Remove old entry if exists
    index["documents"] = [
        d for d in index.get("documents", []) if d.get("filename") != pdf_path.name
    ]
    index["documents"].append(doc_entry)
    index["last_updated"] = datetime.now().isoformat()

    # Save index
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print(f"✓ Updated index: {index_file}")
    print(f"✓ Total documents in memory: {len(index['documents'])}")

    return output_file, doc_entry


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf_to_memory.py <pdf_path1> [pdf_path2] ...")
        print("\nExample:")
        print(
            "  python extract_pdf_to_memory.py KnowledgeBase/712330232-Daily-Bias.pdf"
        )
        sys.exit(1)

    for pdf_path in sys.argv[1:]:
        try:
            extract_pdf_to_memory(pdf_path)
            print()
        except Exception as e:
            print(f"ERROR processing {pdf_path}: {e}")
            continue

    print("\n✓ All PDFs processed successfully!")
