"""Show recently added documents to AI Memory."""

import json

with open("H:/AiMemory/index/latest_index.json", "r") as f:
    index = json.load(f)

recent = sorted(index["documents"], key=lambda x: x.get("extracted", ""), reverse=True)[
    :3
]

print("=" * 80)
print("RECENTLY ADDED TO AI MEMORY")
print("=" * 80)

for i, doc in enumerate(recent, 1):
    print(f"\n{i}. {doc['filename']}")
    print(f"   Pages: {doc['pages']}")
    print(f"   Characters: {doc['characters']:,}")
    print(f"   Extracted: {doc['extracted']}")
    print(f"   Location: {doc['memory_path']}")

print(f"\n{'=' * 80}")
print(f"TOTAL DOCUMENTS IN AI MEMORY: {len(index['documents'])}")
print("=" * 80)
