"""One-time migration: copy every live page + image from Firebase Hosting to S3.

For each site it downloads all sitemap URLs and the /images/* they reference,
rewrites the old *.web.app host to the new site URL (canonical, og:url, JSON-LD),
rebuilds index.html / sitemap.xml / robots.txt / llms.txt, and deploys to S3.

Usage (from repo root):
    poetry -C backend run python infra/migrate_from_firebase.py            # both sites, deploy
    poetry -C backend run python infra/migrate_from_firebase.py --no-deploy
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "travel-blogs"))

_IMAGE_RE = re.compile(r'(?:src|content|href)="(/images/[^"]+)"')


def _migrate_pages(old_host: str, new_url: str, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    old_url = f"https://{old_host}"
    sitemap = httpx.get(f"{old_url}/sitemap.xml", timeout=30)
    sitemap.raise_for_status()
    urls = [u for u in re.findall(r"<loc>(.*?)</loc>", sitemap.text) if u.rstrip("/") != old_url]

    images: set[str] = set()
    for url in urls:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        page = httpx.get(url, timeout=30, follow_redirects=True)
        page.raise_for_status()
        html = page.text.replace(old_url, new_url.rstrip("/"))
        (out_dir / f"{slug}.html").write_text(html, encoding="utf-8")
        images.update(_IMAGE_RE.findall(html))
        print(f"  ✓ {slug}")

    for path in sorted(images):
        dest = out_dir / path.lstrip("/")
        if dest.exists():
            continue
        resp = httpx.get(f"{old_url}{path}", timeout=60)
        if resp.status_code != 200:
            print(f"  ✗ image {path}: HTTP {resp.status_code}", file=sys.stderr)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        print(f"  ✓ {path}")
    return len(urls)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-deploy", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from dotenv import load_dotenv
    load_dotenv(ROOT / "backend" / ".env")

    from app.config import settings
    from app.agents.compiler import DEFAULT_OUTPUT_DIR
    from app.agents.distributor import DistributorAgent

    # ── Marzi Life ──
    print(f"\n== marziblogs.web.app → {settings.site_url}")
    n = _migrate_pages("marziblogs.web.app", settings.site_url, DEFAULT_OUTPUT_DIR)
    print(f"{n} pages")
    life = DistributorAgent(output_dir=DEFAULT_OUTPUT_DIR).run([], deploy=not args.no_deploy)

    # ── Marzi Travel (mutates settings — must run second) ──
    from marzi_travel import site_config
    from marzi_travel.distributor import TravelDistributorAgent
    site_config.apply_to_settings()
    print(f"\n== marzitravelblogs.web.app → {site_config.SITE_URL}")
    n = _migrate_pages("marzitravelblogs.web.app", site_config.SITE_URL, site_config.OUTPUT_DIR)
    print(f"{n} pages")
    travel = TravelDistributorAgent(output_dir=site_config.OUTPUT_DIR).run([], deploy=not args.no_deploy)

    if not args.no_deploy and not (life.deployed and travel.deployed):
        print(f"\nDeploy failed:\n{life.deploy_output[-500:]}\n{travel.deploy_output[-500:]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
