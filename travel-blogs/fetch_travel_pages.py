"""Pull the live Marzi Travel blog from S3 into travel-blogs/site/public/.

Run before the pipeline so discover_existing_pages() has real content to index.
Pages are ephemeral — never committed to git.
"""

import sys
from pathlib import Path

_TRAVEL_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_TRAVEL_ROOT.parent / "backend"))
sys.path.insert(0, str(_TRAVEL_ROOT))

from app.services.s3_deploy import pull_site
from marzi_travel import site_config


def fetch_pages() -> int:
    try:
        pull_site(site_config.S3_BUCKET, site_config.OUTPUT_DIR)
    except Exception as e:
        print(f"[fetch_travel_pages] Failed to pull s3://{site_config.S3_BUCKET}: {e}", file=sys.stderr)
        return 1
    count = len([p for p in site_config.OUTPUT_DIR.glob("*.html") if p.name != "index.html"])
    print(f"[fetch_travel_pages] {count} pages in {site_config.OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(fetch_pages())
