"""Static-site hosting on AWS S3 + CloudFront (replaces Firebase Hosting).

Shells out to the AWS CLI (preinstalled on GitHub runners; `brew install awscli`
locally) so credentials come from the standard chain: `aws configure`,
env vars, or GitHub OIDC.

Uploads never delete remote objects — a partial local checkout can't wipe
live pages. Remove a page by deleting its object in S3 explicitly.
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_HTML_CACHE = "public, max-age=3600"
_ASSET_CACHE = "public, max-age=86400"
_TIMEOUT = 300


def _aws(*args: str) -> str:
    """Run an AWS CLI command, returning combined output. Raises on failure."""
    result = subprocess.run(
        ["aws", *args],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args[:3])} failed: {output.strip()}")
    return output


def deploy_site(local_dir: str | Path, bucket: str, distribution_id: str = "") -> tuple[bool, str]:
    """Upload local_dir to s3://bucket and invalidate the CloudFront cache.

    Returns (success, output_text).
    """
    local_dir = Path(local_dir)
    if not bucket:
        msg = "S3 bucket not configured — set S3_BUCKET (see infra/README.md)"
        logger.error(f"[S3Deploy] {msg}")
        return False, msg

    target = f"s3://{bucket}"
    try:
        # HTML: explicit content type + short cache so new posts show up within the hour.
        out = _aws(
            "s3", "sync", str(local_dir), target,
            "--exclude", "*", "--include", "*.html",
            "--content-type", "text/html; charset=utf-8",
            "--cache-control", _HTML_CACHE,
        )
        # sitemap.xml, robots.txt, llms.txt — MIME type guessed from extension.
        out += _aws(
            "s3", "sync", str(local_dir), target,
            "--exclude", "*.html", "--exclude", "images/*",
            "--exclude", ".*", "--exclude", "*/.*",
            "--cache-control", _HTML_CACHE,
        )
        # Images rarely change — longer cache.
        if (local_dir / "images").is_dir():
            out += _aws(
                "s3", "sync", str(local_dir / "images"), f"{target}/images",
                "--exclude", ".*",
                "--cache-control", _ASSET_CACHE,
            )

        if distribution_id:
            out += _aws(
                "cloudfront", "create-invalidation",
                "--distribution-id", distribution_id,
                "--paths", "/*",
                "--query", "Invalidation.Id", "--output", "text",
            )
        else:
            logger.warning("[S3Deploy] CLOUDFRONT_DISTRIBUTION_ID not set — skipping cache invalidation")

        logger.info(f"[S3Deploy] Deployed {local_dir} → {target}")
        return True, out
    except FileNotFoundError:
        msg = "AWS CLI not found — install with: brew install awscli"
        logger.error(f"[S3Deploy] {msg}")
        return False, msg
    except subprocess.TimeoutExpired:
        msg = f"AWS deploy timed out after {_TIMEOUT}s"
        logger.error(f"[S3Deploy] {msg}")
        return False, msg
    except Exception as e:
        logger.error(f"[S3Deploy] {e}")
        return False, str(e)


def pull_site(bucket: str, local_dir: str | Path, retries: int = 2) -> None:
    """Download every live page from s3://bucket into local_dir.

    Run before the pipeline so discover_existing_pages() sees the full live site.
    Raises on failure — the pipeline must not run against a partial inventory.
    """
    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries + 1):
        try:
            _aws("s3", "sync", f"s3://{bucket}", str(local_dir))
            logger.info(f"[S3Deploy] Pulled s3://{bucket} → {local_dir}")
            return
        except RuntimeError:
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)
