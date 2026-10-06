# Hosting infrastructure (AWS)

Both blogs are static sites: a private S3 bucket behind CloudFront, in `ap-south-1`.

| Site | Stack | Bucket | Distribution | URL |
|---|---|---|---|---|
| Marzi Life | `aeo-marzi-life` | `aeo-marzi-life-904233100956` | `E321IIF074LQON` | https://d12xiu8vvi5sts.cloudfront.net |
| Marzi Travel | `aeo-marzi-travel` | `aeo-marzi-travel-904233100956` | `E3UQ12NFR1INK9` | https://d3hytixpi5dxhx.cloudfront.net |

These values are hard-coded in `backend/app/config.py` and `travel-blogs/marzi_travel/site_config.py`.

## Files

- `static-site.yaml`: S3 bucket (versioned, private), CloudFront with an Origin Access Control, a CloudFront Function for Firebase-style clean URLs (`/slug` serves `slug.html`, `/slug.html` and `/slug/` 301 to `/slug`), and security headers. Robots directives come from each page's meta tag: `index.html` is `noindex, nofollow`, and blog pages are `index, follow`.
- `github-deploy-role.yaml`: the `aeo-blog-github-deploy` IAM role that GitHub Actions assumes through OIDC, so no AWS keys are stored in GitHub. It's scoped to the two buckets and distributions, and only for the `main` branch of `marzitech/AEOAgents`.
- `migrate_from_firebase.py`: the one-time copy of all pages and images from `*.web.app`. Already run on 2026-10-06.

## Deploying or updating the stacks

```bash
aws cloudformation deploy --template-file infra/static-site.yaml --stack-name aeo-marzi-life
aws cloudformation deploy --template-file infra/static-site.yaml --stack-name aeo-marzi-travel
aws cloudformation deploy --template-file infra/github-deploy-role.yaml \
  --stack-name aeo-blog-github-deploy --capabilities CAPABILITY_NAMED_IAM
```

## Adding a custom domain later

1. Request an ACM certificate in **us-east-1** (CloudFront requires that region) for, say, `blog.marzi.life`, and validate it through DNS.
2. Redeploy the stack with the domain:
   ```bash
   aws cloudformation deploy --template-file infra/static-site.yaml --stack-name aeo-marzi-life \
     --parameter-overrides DomainName=blog.marzi.life CertificateArn=arn:aws:acm:us-east-1:...
   ```
3. Point a DNS CNAME from `blog.marzi.life` to the distribution's `*.cloudfront.net` domain.
4. Update `site_url` in `config.py` (or `SITE_URL` in `site_config.py`) and re-run the pipeline so canonical URLs, the sitemap and `llms.txt` use the new domain.

## Notes

- Deploys never delete objects from S3. To take a page down, run `aws s3 rm s3://<bucket>/<slug>.html`, then invalidate `/*`.
- Bucket versioning keeps overwritten pages for 90 days, so a bad deploy can be rolled back.
