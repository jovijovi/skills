---
name: amazon-extract
description: Extract structured product details and image links from Amazon.com product pages without using cookies. Use when the user provides an Amazon URL or ASIN and asks for product metadata, pricing context, variations, specifications, or gallery image URLs in JSON format.
---

# Amazon Extract

Extract Amazon product information from a product URL or ASIN and return normalized JSON.

## Quick Start

Run the extractor:

```bash
python scripts/amazon_extract.py "<amazon_url_or_asin>" --pretty
```

Examples:

```bash
python scripts/amazon_extract.py "https://www.amazon.com/dp/B0FTTF3RB5" --pretty
python scripts/amazon_extract.py "B0FSMZ57LP" --pretty
python scripts/amazon_extract.py "B0FSMZ57LP" --output /tmp/amazon.json --pretty
python scripts/amazon_extract.py "B0FSMZ57LP" --error-json --pretty
python scripts/amazon_extract.py "B0FSMZ57LP" --extract-script /home/ubuntu/.codex/skills/extract/scripts/extract.sh --pretty
python scripts/amazon_extract.py "B0FSMZ57LP" --no-verify-main-image --pretty
```

## Workflow

1. Accept either Amazon product URL or ASIN.
2. Normalize to canonical `https://www.amazon.com/dp/<ASIN>` when possible.
3. Fetch HTML with no cookies.
4. Parse core product fields and image URLs.
5. If extraction confidence is low, use headless fallback (still no cookies).
6. If still blocked or low-confidence, call `extract` skill script for Tavily-assisted extraction and merge fields.
7. Return structured JSON with diagnostics and error code.

## Output

See `references/schema.md` for full field definitions and status semantics.

Top-level fields include:

- `schema_version`
- `status` (`success`, `partial_success`, `error`)
- `asin`
- `canonical_url`
- `product`, `offer`, `content`, `specs`, `media`, `variant`, `rating`
- `diagnostics` (confidence, missing fields, error code)

## Error Handling

Common `diagnostics.error_code` values:

- `BLOCKED_BY_BOT`
- `CAPTCHA_REQUIRED`
- `NOT_FOUND`
- `PARTIAL_SUCCESS`
- `EXTRACTION_FAILED`

## Notes

- Do not use cookies.
- Data completeness varies by anti-bot response and page layout.
- The script can call `extract`/Tavily fallback automatically unless `--no-extract-fallback` is set.
- The extract fallback script path is discovered in this order: `--extract-script`, env `AMAZON_EXTRACT_EXTRACT_SCRIPT`, sibling `../extract/scripts/extract.sh`, default absolute path.
- `media.product_main_image` prioritizes hi-res Amazon hero image variants (for example `_AC_SL1500_`).
- `media.product_images` stores the main product gallery image set.
- `media.other_images` stores other captured image URLs after filtering.
- `offer` includes `seller`, `sold_by`, and `ships_from` when available.
- `diagnostics.main_image_verified` indicates whether the selected main image URL passed reachability verification.
- Always rely on `status`, `confidence`, and `missing_fields` for downstream decisions.
