#!/usr/bin/env python3
"""
generate_metadata.py

1. Reads latest transcripts_*.jsonl
2. Extracts speaker, timestamp, and text from each chunk
3. Saves a consolidated metadata.json with environment overrides and logging
"""

import os
import json
import logging
from pathlib import Path

# === CONFIGURATION ===
OUTPUT_FILE = os.getenv('OUTPUT_FILE', 'metadata.json')

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def get_latest_transcript_file(pattern="transcripts_*.jsonl") -> str:
    """Return the most recent transcript file based on modification time."""
    files = sorted(Path().glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(files[0]) if files else None

def main():
    input_file = os.getenv('INPUT_FILE') or get_latest_transcript_file()
    if not input_file:
        logging.error("❌ No transcript files found.")
        return

    input_path = Path(input_file)
    output_path = Path(OUTPUT_FILE)

    logging.info(f"📥 Loading transcript: {input_path}")

    if not input_path.exists():
        logging.error(f"❌ Input file not found: {input_path}")
        return

    metadata = []
    with input_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                logging.warning(f"⚠️ Skipping line {line_num} due to JSON error: {e}")
                continue

            chunks = entry.get('chunks', [])
            if not isinstance(chunks, list):
                logging.warning(f"⚠️ Line {line_num} has invalid 'chunks' format. Skipping.")
                continue

            for i, chunk in enumerate(chunks):
                metadata.append({
                    'speaker': chunk.get('speaker', 'Unknown'),
                    'timestamp': chunk.get('timestamp', ''),
                    'text': chunk.get('text', ''),
                    'source_id': entry.get('file_id', None),  # updated to match fetch_and_chunk.py
                    'chunk_index': i
                })

    with output_path.open('w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logging.info(f"✅ Saved {len(metadata)} metadata entries to '{OUTPUT_FILE}'")

if __name__ == '__main__':
    main()
