"""Show summary of documents in AI Memory."""

import json
from pathlib import Path

index_file = Path("H:/AiMemory/index/latest_index.json")
with open(index_file, "r") as f:
    index = json.load(f)

print("=" * 80)
print("AI MEMORY SUMMARY")
print("=" * 80)
print(f"Total documents: {len(index['documents'])}")
print(f"Last updated: {index['last_updated']}")
print("\nMost recent additions:\n")

recent = sorted(index["documents"], key=lambda x: x.get("extracted", ""), reverse=True)[
    :5
]
for i, doc in enumerate(recent, 1):
    print(f"{i}. {doc['filename']}")
    print(f"   Pages: {doc.get('pages', 'N/A')}")
    print(f"   Characters: {doc.get('characters', 0):,}")
    print(f"   Extracted: {doc.get('extracted', 'Unknown')}")
    print(f"   Location: {doc['memory_path']}")
    print()

print("=" * 80)
