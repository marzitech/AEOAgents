"""Pull the live Marzi blog from S3 into site/public/.

Run before the pipeline so discover_existing_pages() has real content to index.
Pages are ephemeral — never committed to git.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings
from app.agents.compiler import DEFAULT_OUTPUT_DIR
from app.services.s3_deploy import pull_site


def fetch_pages() -> int:
    try:
        pull_site(settings.s3_bucket, DEFAULT_OUTPUT_DIR)
    except Exception as e:
        print(f"[fetch_pages] Failed to pull s3://{settings.s3_bucket}: {e}", file=sys.stderr)
        return 1
    count = len([p for p in DEFAULT_OUTPUT_DIR.glob("*.html") if p.name != "index.html"])
    print(f"[fetch_pages] {count} pages in {DEFAULT_OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(fetch_pages())
