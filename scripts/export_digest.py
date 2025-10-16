#!/usr/bin/env python3
"""
Oracle Weekly Digest Export Script

Generates a markdown digest of top trending topics for sharing.
"""

import datetime as dt
import sys
from pathlib import Path

import requests


def main():
    base = "http://localhost:8000"

    try:
        # Get all topics
        print("Fetching topics...")
        topics_response = requests.get(f"{base}/topics")
        topics_response.raise_for_status()
        topics = topics_response.json()

        # Generate digest
        lines = [f"# Oracle Weekly Digest — {dt.date.today()}"]
        lines.append("")
        lines.append("## Top Trending Topics")
        lines.append("")

        for i, t in enumerate(topics[:12], 1):
            topic_id = t['id']

            # Get detailed topic data
            detail_response = requests.get(f"{base}/topics/{topic_id}")
            detail_response.raise_for_status()
            d = detail_response.json()

            # Format topic entry
            surge_pct = d.get('surge_score_pct', t.get('surge_score_pct', 'N/A'))
            narrative = d.get('narrative', '(no narrative available)')

            lines.append(f"### {i}. {d['name']} — Surge {surge_pct}%")
            lines.append("")
            lines.append(narrative)
            lines.append("")

        # Write to file
        output_path = Path("artifacts/digest.md")
        output_path.parent.mkdir(exist_ok=True)

        digest_content = "\n".join(lines)
        output_path.write_text(digest_content, encoding="utf-8")

        print(f"Wrote digest to {output_path}")
        print(f"Covered {len(topics[:12])} topics")
        print(f"Generated on {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API at http://localhost:8000")
        print("   Make sure the API server is running with: python3 simple_api.py")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
