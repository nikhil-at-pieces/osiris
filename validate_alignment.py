#!/usr/bin/env python3
"""
validate_alignment.py

Checks that the number of text chunks matches metadata entries.
"""

import json
import sys

TEXTS_FILE = "texts.json"
METADATA_FILE = "metadata.json"

def main():
    with open(TEXTS_FILE, "r", encoding="utf-8") as f1:
        texts = json.load(f1)

    with open(METADATA_FILE, "r", encoding="utf-8") as f2:
        metadata = json.load(f2)

    if len(texts) != len(metadata):
        print(f"❌ Mismatch: {len(texts)} texts vs {len(metadata)} metadata entries")
        sys.exit(1)

    print(f"✅ texts.json and metadata.json are aligned ({len(texts)} entries)")

if __name__ == "__main__":
    main()
