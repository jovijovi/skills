# Amazon Extract Output Schema

## Purpose

Define the normalized JSON contract returned by `scripts/amazon_extract.py`.

## Input

- URL input example: `https://www.amazon.com/dp/B0FTTF3RB5`
- ASIN input example: `B0FSMZ57LP`

## Top-Level Shape

```json
{
  "schema_version": "1.0.0",
  "status": "success|partial_success|error",
  "input": {
    "type": "url|asin",
    "value": "string",
    "marketplace": "amazon.com"
  },
  "asin": "string",
  "canonical_url": "string",
  "product": {},
  "offer": {},
  "content": {},
  "specs": {},
  "media": {},
  "variant": {},
  "rating": {},
  "diagnostics": {}
}
```

## Field Definitions

- `product.title`: Product title text.
- `product.brand`: Brand text.
- `product.category_path`: Reserved for future category extraction.
- `offer.price`: Numeric price string when available.
- `offer.currency`: Currency symbol (`$`, `€`, etc.) when detected.
- `offer.availability`: Availability text.
- `offer.seller`: Seller/merchant text.
- `offer.sold_by`: Seller name when parsed separately.
- `offer.ships_from`: Fulfillment source when parsed separately.
- `content.bullets`: Bullet list from feature bullets.
- `content.description`: Product description snippet.
- `specs`: Key/value map for technical specifications and detail bullets.
- `media.product_main_image`: Preferred hero image URL. Prioritize high-resolution variant (`hiRes`, typically `_AC_SL1500_`) when available or derivable.
- `media.product_images`: Main product gallery image URLs from the product detail media set.
- `media.other_images`: Other captured image URLs after filtering out tiny images and obvious non-product assets.
- `media.variant_images`: Reserved for future variant image mapping.
- `variant.colors`: Extracted color options.
- `variant.sizes`: Extracted size options.
- `variant.selected_variant`: Reserved for future selected variant details.
- `rating.star`: Numeric star rating string.
- `rating.review_count`: Review count string.

## Diagnostics

- `diagnostics.fetch_mode`: `requests`, `headless`, or composed mode such as `headless+extract`.
- `diagnostics.final_url`: Final resolved URL after redirects.
- `diagnostics.http_status`: HTTP status code.
- `diagnostics.confidence`: Coverage ratio from 0 to 1.
- `diagnostics.missing_fields`: List of missing core fields.
- `diagnostics.error_code`: Error or status code.
- `diagnostics.fallback_source`: `extract` when Tavily/extract fallback was used, else empty string.
- `diagnostics.main_image_verified`: Boolean; true when `product_main_image` passed URL reachability check.

## Status Rules

- `success`: Confidence >= 0.8, title present, and at least one image found.
- `partial_success`: Some fields found but confidence/coverage incomplete.
- `error`: Strong block/failure signal with very low field coverage.

## Error Codes

- `NOT_FOUND`: HTTP 404 detected.
- `BLOCKED_BY_BOT`: Anti-bot response or server block.
- `CAPTCHA_REQUIRED`: Captcha page detected.
- `PARTIAL_SUCCESS`: Partial extraction with no stronger block code.
- `EXTRACTION_FAILED`: Unexpected exception in extraction flow.
