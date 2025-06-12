#!/usr/bin/env python3

"""
fetch_and_chunk.py

Fetch Google Docs → Normalize & Chunk → Save to timestamped JSONL
"""

import os
import re
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# === CONFIG ===
KEY_FILE         = os.getenv("KEY_FILE", "sa-credentials.json")
SCOPES           = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/documents.readonly']
INPUT_QUERY      = os.getenv("INPUT_QUERY", "mimeType='application/vnd.google-apps.document' and name contains 'Notes'")
MAX_TOKENS       = int(os.getenv("MAX_TOKENS", "512"))
OVERLAP_RATIO    = float(os.getenv("OVERLAP_RATIO", "0.2"))
RUN_ID           = os.getenv("RUN_ID") or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
VERSION_TAG      = f"v1-{RUN_ID}"
OUTPUT_JSONL     = f"transcripts_{RUN_ID}.jsonl"

# === AUTH ===
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

# === FUNCTIONS ===
def find_doc_files(service, query: str) -> List[dict]:
    results, token = [], None
    while True:
        resp = service.files().list(q=query, fields="nextPageToken, files(id, name)", pageSize=100, pageToken=token).execute()
        results += resp.get('files', [])
        token = resp.get('nextPageToken')
        if not token:
            break
    return results

def export_as_text(service, file_id: str) -> str:
    req = service.files().export_media(fileId=file_id, mimeType='text/plain')
    buf = BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    while not downloader.next_chunk()[1]:
        continue
    return buf.getvalue().decode('utf-8')

def recursive_chunk(text: str, max_words: int, overlap: float) -> List[str]:
    words = text.split()
    step = int(max_words * (1 - overlap))
    return [' '.join(words[i:i + max_words]) for i in range(0, len(words), step)]

def normalize_and_chunk(text: str, max_tokens=512, overlap=0.2) -> List[str]:
    cleaned = re.sub(r'\s+', ' ', text).strip()
    paras = re.split(r'\n\s*\n', cleaned)
    chunks = []
    for para in paras:
        if not para:
            continue
        buffer = ''
        for sentence in re.split(r'(?<=[.!?]) +', para):
            candidate = f"{buffer} {sentence}".strip()
            if len(candidate.split()) <= max_tokens:
                buffer = candidate
            else:
                if buffer:
                    chunks.extend(recursive_chunk(buffer, max_tokens, overlap))
                buffer = sentence
        if buffer:
            chunks.extend(recursive_chunk(buffer, max_tokens, overlap))
    return chunks

def write_jsonl(path, record):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

# === MAIN ===
def main():
    Path(OUTPUT_JSONL).unlink(missing_ok=True)
    Path(OUTPUT_JSONL).touch()

    drive = get_drive_service()
    files = find_doc_files(drive, INPUT_QUERY)
    print(f"📂 Found {len(files)} files")

    for f in files:
        print(f"→ Processing: {f['name']} ({f['id']})")
        text = export_as_text(drive, f['id'])
        chunks = normalize_and_chunk(text, MAX_TOKENS, OVERLAP_RATIO)

        record = {
            'version': VERSION_TAG,
            'timestamp': datetime.utcnow().isoformat(),
            'file_name': f['name'],
            'file_id': f['id'],
            'num_chunks': len(chunks),
            'chunks': [{'id': i + 1, 'text': c} for i, c in enumerate(chunks)]
        }
        write_jsonl(OUTPUT_JSONL, record)

    print(f"✅ Output written to: {OUTPUT_JSONL}")

if __name__ == '__main__':
    main()
