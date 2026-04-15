#!/usr/bin/env python3
"""
check-update.py — Detect if EuroPCR has released a new programme PDF.

Strategy:
    1. HEAD request to the PDF URL, compare Last-Modified and Content-Length
       against the last-known values stored in scripts/.last-check.json.
    2. If changed, download the PDF, compute SHA-256, compare to previously
       known hash.
    3. If content actually changed, output a structured summary for the caller
       (GitHub Action, cron, or manual). Exit code 0 for no change, 1 for
       change detected, 2 for error.

Outputs (on stdout, JSON):
    { "changed": bool, "reason": "...", "details": {...} }

Environment variables:
    EUROPCR_PDF_URL  override the default PDF URL
    CI               if set, skips interactive prompts

Designed to run in GitHub Actions (see .github/workflows/daily-check.yml).
"""

import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
STATE_FILE = Path(__file__).parent / ".last-check.json"
PDF_URL_DEFAULT = "https://interactive-programme.europa-organisation.com/pdf/europcr2026/programme_europcr2026.pdf"

USER_AGENT = "EuroPCR-2026-Guide/1.0 (https://github.com/alleneinstein0411-cyber/europcr-2026-guide)"


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def head(url):
    """Return (content_length, last_modified, etag) or None on failure."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {
                "content_length": resp.headers.get("Content-Length"),
                "last_modified": resp.headers.get("Last-Modified"),
                "etag": resp.headers.get("ETag"),
                "status": resp.status,
            }
    except (urllib.error.URLError, urllib.error.HTTPError) as err:
        return {"error": str(err)}


def download(url):
    """Download the PDF, return sha256 hash and size."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    h = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(req, timeout=120) as resp:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def main():
    url = os.environ.get("EUROPCR_PDF_URL", PDF_URL_DEFAULT)
    now = datetime.now(timezone.utc).isoformat()

    prev = load_state()
    result = {"changed": False, "reason": "", "details": {}, "checkedAt": now, "url": url}

    # Step 1: HEAD
    h = head(url)
    if "error" in h:
        result.update({"changed": False, "reason": f"HEAD request failed: {h['error']}"})
        print(json.dumps(result, indent=2))
        return 2

    result["details"]["head"] = h

    # Step 2: compare headers
    changed_header = (
        prev.get("content_length") != h.get("content_length")
        or prev.get("last_modified") != h.get("last_modified")
        or prev.get("etag") != h.get("etag")
    )

    if not changed_header and prev.get("content_length"):
        result["reason"] = "No change detected (headers match previous check)"
        save_state({**prev, "lastChecked": now})
        print(json.dumps(result, indent=2))
        return 0

    # Step 3: download and hash for certainty
    try:
        sha, size = download(url)
    except Exception as err:
        result.update({"changed": False, "reason": f"Download failed: {err}"})
        print(json.dumps(result, indent=2))
        return 2

    result["details"]["sha256"] = sha
    result["details"]["size"] = size

    if prev.get("sha256") == sha:
        # Headers changed but content didn't (e.g. CDN refresh)
        result["reason"] = "Headers changed but hash matches — likely CDN refresh"
        save_state({**h, "sha256": sha, "size": size, "lastChecked": now})
        print(json.dumps(result, indent=2))
        return 0

    # Real change!
    result["changed"] = True
    result["reason"] = "PDF content changed"
    if prev.get("sha256"):
        result["details"]["previousHash"] = prev.get("sha256")
        result["details"]["previousSize"] = prev.get("size")

    save_state({
        **h,
        "sha256": sha,
        "size": size,
        "lastChecked": now,
        "previousHash": prev.get("sha256"),
        "previousSize": prev.get("size"),
    })

    print(json.dumps(result, indent=2))
    return 1


if __name__ == "__main__":
    sys.exit(main())
