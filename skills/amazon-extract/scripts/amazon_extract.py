#!/usr/bin/env python3
"""Extract Amazon product details and image URLs without cookies.

Input: product URL or ASIN
Output: structured JSON with diagnostics
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
ASIN_IN_URL_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE)
PRICE_RE = re.compile(r"([\$£€¥])\s?([0-9][0-9,]*\.?[0-9]{0,2})")
URL_RE = re.compile(r"https?://[^\"'\s>]+")
ASIN_TEXT_RE = re.compile(r"\b([A-Z0-9]{10})\b")
DEFAULT_EXTRACT_SCRIPT = "/home/ubuntu/.codex/skills/extract/scripts/extract.sh"
EXTRACT_SCRIPT_ENV = "AMAZON_EXTRACT_EXTRACT_SCRIPT"


@dataclass
class FetchResult:
    html: str
    final_url: str
    status_code: int
    mode: str


class ExtractError(RuntimeError):
    pass


def is_probable_product_image_url(url: str) -> bool:
    low = url.lower()
    if not low.startswith("http"):
        return False
    if not any(low.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
        return False
    if "fls-na.amazon.com" in low or "aax-us-east-retail-direct.amazon.com" in low:
        return False
    if "m.media-amazon.com/images/g/" in low:
        return False
    if "m.media-amazon.com/images/s/" in low:
        return False
    if "images-na.ssl-images-amazon.com/images/g/" in low:
        return False
    if "/images/i/" in low:
        return True
    if "/aplus-media-library-service-media/" in low:
        return True
    return False


def normalize_json_like_text(text: str) -> str:
    return text.replace('\\"', '"').replace("\\u0026", "&")


def extract_buybox_price(raw: str) -> Tuple[str, str]:
    normalized = normalize_json_like_text(raw)

    m = re.search(
        r'"displayPrice"\s*:\s*"([$\u00A3€¥])?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)"',
        normalized,
        re.IGNORECASE,
    )
    if m:
        return (m.group(1) or "", m.group(2).replace(",", ""))

    m = re.search(r'"priceAmount"\s*:\s*([0-9]+(?:\.[0-9]{1,2})?)', normalized, re.IGNORECASE)
    if m:
        price = m.group(1)
        window_start = max(0, m.start() - 220)
        window_end = min(len(normalized), m.end() + 220)
        window = normalized[window_start:window_end]
        cm = re.search(r'"currencySymbol"\s*:\s*"([^"]+)"', window, re.IGNORECASE)
        currency = cm.group(1).strip() if cm else ""
        return (currency, price)

    return ("", "")


def parse_shipping_seller(text: str) -> Tuple[str, str]:
    clean = text.strip()
    sold_by = ""
    ships_from = ""

    m = re.search(r"Ships from\s+(.+?)(?:Sold by|Returns|$)", clean, re.IGNORECASE)
    if m:
        ships_from = m.group(1).strip(" -,:;")

    m = re.search(r"Sold by\s+(.+?)(?:Returns|$)", clean, re.IGNORECASE)
    if m:
        sold_by = m.group(1).strip(" -,:;")

    return sold_by, ships_from


def resolve_extract_script_path(cli_value: str) -> str:
    candidates: List[str] = []
    if cli_value:
        candidates.append(cli_value)

    env_value = os.environ.get(EXTRACT_SCRIPT_ENV, "").strip()
    if env_value:
        candidates.append(env_value)

    repo_relative = Path(__file__).resolve().parents[2] / "extract" / "scripts" / "extract.sh"
    candidates.append(str(repo_relative))
    candidates.append(DEFAULT_EXTRACT_SCRIPT)

    for path in candidates:
        p = Path(path)
        if p.is_file():
            return str(p)

    return candidates[0] if candidates else DEFAULT_EXTRACT_SCRIPT


def is_url_reachable(url: str, timeout: int = 5) -> bool:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    try:
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code < 400:
            return True
        if resp.status_code in {403, 405}:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
            try:
                return resp.status_code < 400
            finally:
                resp.close()
    except Exception:
        return False
    return False


def extract_image_resolution(url: str) -> int:
    low = url.lower()
    patterns = [
        r"_ac_sl(\d+)_",
        r"_sl(\d+)_",
        r"_ac_sx(\d+)_",
        r"_sx(\d+)_",
        r"_ac_sy(\d+)_",
        r"_sy(\d+)_",
        r"_ac_us(\d+)_",
        r"\.ss(\d+)_",
        r"_ss(\d+)_",
        r"_ac_ul(\d+)_",
        r"_ul(\d+)_",
    ]
    best = 0
    for pat in patterns:
        for m in re.finditer(pat, low):
            try:
                best = max(best, int(m.group(1)))
            except Exception:
                pass
    for m in re.finditer(r"_sr(\d+),(\d+)_", low):
        try:
            best = max(best, int(m.group(1)), int(m.group(2)))
        except Exception:
            pass
    return best


def is_too_small_image(url: str, min_side_px: int = 180) -> bool:
    side = extract_image_resolution(url)
    return side > 0 and side < min_side_px


def has_explicit_size_marker(url: str) -> bool:
    low = url.lower()
    if extract_image_resolution(url) > 0:
        return True
    if "_ac_" in low or "_sl" in low or "_sx" in low or "_sy" in low:
        return True
    return False


def looks_like_icon_asset(url: str) -> bool:
    low = url.lower()
    if "/aplus-media-library-service-media/" in low:
        return False
    if "cf-at-glance" in low:
        return True
    m = re.search(r"/images/i/([^/?#]+)$", low)
    if not m:
        return False
    filename = m.group(1)
    if filename.endswith((".png", ".jpg", ".jpeg")) and not has_explicit_size_marker(url):
        stem = filename.rsplit(".", 1)[0]
        if 8 <= len(stem) <= 16:
            return True
    return False


def image_quality_score(url: str) -> int:
    low = url.lower()
    score = 0

    if "m.media-amazon.com/images/i/" in low:
        score += 400
    elif "images-na.ssl-images-amazon.com/images/i/" in low:
        score += 300
    elif "/aplus-media-library-service-media/" in low:
        score += 120

    if "_ac_sl" in low:
        score += 300
    elif "_sl" in low:
        score += 220
    elif "_ac_sx" in low or "_ac_sy" in low:
        score += 120
    elif "_sx" in low or "_sy" in low:
        score += 80

    resolution = extract_image_resolution(url)
    score += min(resolution, 3000) // 10

    low_quality_markers = [
        "_ac_us40_",
        "_ac_us100_",
        "_ss100_",
        "_sr100,100_",
        "_sr160,134_",
        "_ul165_",
        "pkplay-button",
        "sprite",
        "loading-4x-gray",
    ]
    for marker in low_quality_markers:
        if marker in low:
            score -= 120

    return score


def is_product_gallery_image(url: str) -> bool:
    low = url.lower()
    if "/images/i/" not in low:
        return False
    if is_too_small_image(url):
        return False
    if not has_explicit_size_marker(url) and "/aplus-media-library-service-media/" not in low:
        return False
    if looks_like_icon_asset(url):
        return False
    if "aicid=community-reviews" in low:
        return False
    bad_markers = [
        "_ac_us",
        ".ss",
        "_ss",
        "_sr",
        "_ul",
        "pkdp-play-icon-overlay",
    ]
    if any(m in low for m in bad_markers):
        return False
    return True


def select_main_image(images: List[str]) -> str:
    if not images:
        return ""
    candidates = [u for u in images if is_probable_product_image_url(u)]
    if not candidates:
        return images[0]
    return max(candidates, key=lambda u: (image_quality_score(u), len(u)))


def to_hires_main_image(url: str) -> str:
    low = url.lower()
    if "m.media-amazon.com/images/i/" not in low and "images-na.ssl-images-amazon.com/images/i/" not in low:
        return url

    if re.search(r"\._AC_SL\d+_", url):
        return url

    upgraded = re.sub(r"\._AC_S[XY]\d+_", "._AC_SL1500_", url)
    if upgraded != url:
        return upgraded

    if "._AC_" in url and "._AC_SL" not in url:
        upgraded = re.sub(r"\._AC_[^\.]*\.", "._AC_SL1500_.", url)
        if upgraded != url:
            return upgraded

    upgraded = re.sub(r"\._AC_[A-Z]{1,3}\d+_", "._AC_SL1500_", url)
    if upgraded != url:
        return upgraded

    return url


def main_image_fallback_variants(url: str) -> List[str]:
    variants = [url]
    if re.search(r"\._AC_SL\d+_", url):
        variants.append(re.sub(r"\._AC_SL\d+_", "._AC_SX679_", url))
        variants.append(re.sub(r"\._AC_SL\d+_", "._AC_SY679_", url))
    return list(dict.fromkeys(variants))


def split_media_images(images: List[str]) -> Tuple[List[str], List[str]]:
    product_images_raw = [
        to_hires_main_image(u)
        for u in images
        if is_probable_product_image_url(u) and is_product_gallery_image(u)
    ]
    product_images = sorted(
        list(dict.fromkeys(product_images_raw)),
        key=lambda u: (-image_quality_score(u), u),
    )

    product_set = set(product_images)
    other_images_raw = [
        u
        for u in images
        if is_probable_product_image_url(u)
        and not is_too_small_image(u)
        and not looks_like_icon_asset(u)
        and (has_explicit_size_marker(u) or "/aplus-media-library-service-media/" in u.lower())
        and to_hires_main_image(u) not in product_set
    ]
    other_images = sorted(
        list(dict.fromkeys(other_images_raw)),
        key=lambda u: (-image_quality_score(u), u),
    )
    return product_images, other_images


def select_main_image_with_verification(
    product_images: List[str],
    fallback_images: List[str],
    verify: bool,
    timeout: int,
) -> Tuple[str, bool]:
    if product_images:
        candidates = product_images
    elif fallback_images:
        candidates = [to_hires_main_image(select_main_image(fallback_images))]
    else:
        return "", False

    if not verify:
        return candidates[0], False

    for candidate in candidates:
        for variant in main_image_fallback_variants(candidate):
            if is_url_reachable(variant, timeout=timeout):
                return variant, True
    return candidates[0], False


def normalize_input(value: str, marketplace: str) -> Tuple[str, str, str]:
    raw = value.strip()
    if ASIN_RE.match(raw.upper()):
        asin = raw.upper()
        url = f"https://{marketplace}/dp/{asin}"
        return "asin", asin, url

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ExtractError("Input must be a valid Amazon product URL or a 10-character ASIN.")

    host = parsed.netloc.lower()
    if "amazon.com" not in host:
        raise ExtractError("Only amazon.com URLs are supported in this skill.")

    m = ASIN_IN_URL_RE.search(parsed.path)
    asin = m.group(1).upper() if m else ""
    return "url", asin, raw


def fetch_with_requests(url: str, timeout: int) -> FetchResult:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
    }
    resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    return FetchResult(html=resp.text, final_url=resp.url, status_code=resp.status_code, mode="requests")


def fetch_with_playwright(url: str, timeout: int) -> Optional[FetchResult]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="en-US")
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        page.wait_for_timeout(3000)
        html_text = page.content()
        final_url = page.url
        browser.close()
        return FetchResult(html=html_text, final_url=final_url, status_code=200, mode="headless")


def parse_json_blob(text: str) -> Optional[Dict[str, Any]]:
    raw = text.strip()
    if not raw:
        return None

    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw[start : end + 1]
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except Exception:
            return None
    return None


def parse_specs_from_text(raw_content: str) -> Dict[str, str]:
    specs: Dict[str, str] = {}
    for line in raw_content.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 2:
            continue
        key, value = cols[0], cols[1]
        if not key or key.startswith("---") or not value:
            continue
        if key not in specs:
            specs[key] = value
    return specs


def parse_bullets_from_text(raw_content: str) -> List[str]:
    lines = raw_content.splitlines()
    bullets: List[str] = []
    capture = False
    stop_markers = [
        "item details",
        "product specifications",
        "materials & care",
        "report an issue",
        "consider a similar item",
        "frequently bought together",
        "customer reviews",
        "product summary",
        "product description",
        "additional details",
    ]
    noise_markers = [
        "keyboard shortcuts",
        "search opt",
        "cart shift",
        "returns& orders",
        "delivering to",
        "select the department",
        "image ",
        "video player",
        "play mute",
        "current time",
    ]

    for raw_line in lines:
        line = raw_line.strip()
        low = line.lower()
        if re.search(r"^about this item\b", low):
            capture = True
            continue
        if capture and any(stop in low for stop in stop_markers):
            break
        if capture:
            text = line.lstrip("-*• ").strip()
            if (
                text
                and 8 <= len(text) <= 260
                and any(ch.isalpha() for ch in text)
                and not any(marker in text.lower() for marker in noise_markers)
            ):
                bullets.append(text)
            if len(bullets) >= 20:
                break
    return list(dict.fromkeys(bullets))


def parse_core_from_text(raw_content: str, images: List[str]) -> Tuple[Dict[str, Any], str]:
    title = ""
    brand = ""
    availability = ""
    seller = ""
    sold_by = ""
    ships_from = ""
    description = ""
    rating = ""
    review_count = ""
    price = ""
    currency = ""
    asin = ""
    colors: List[str] = []
    sizes: List[str] = []

    lines = [ln.strip() for ln in raw_content.splitlines() if ln.strip()]

    m = re.search(r"\n([^\n]{12,240})\nBrand:\s*([^\n]+)", raw_content, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        brand = m.group(2).strip()

    if not title:
        m = re.search(r"Product Summary:\s*([^\n]{12,260})", raw_content, re.IGNORECASE)
        if m:
            title = m.group(1).strip()

    p_currency, p_price = extract_buybox_price(raw_content)
    if p_price:
        currency = p_currency
        price = p_price

    for i, line in enumerate(lines):
        low = line.lower()
        if not title and " at amazon " in low:
            title = re.sub(r"\s+at\s+amazon.*$", "", line, flags=re.IGNORECASE).strip()
        if not title and i < 12 and len(line) > 10 and "›" not in line and "image unavailable" not in low:
            if "brand:" not in low and "color:" not in low:
                title = line
        if not brand:
            m = re.search(r"Brand:\s*(.+)$", line, re.IGNORECASE)
            if m:
                brand = m.group(1).strip()
        if not brand:
            m = re.search(r"^Brand\s+(.+)$", line, re.IGNORECASE)
            if m:
                brand = m.group(1).strip()
        if not availability and ("in stock" in low or "currently unavailable" in low):
            availability = line
        if not sold_by and low == "sold by" and i + 1 < len(lines):
            sold_by = lines[i + 1].strip()
        elif not sold_by and low.startswith("sold by "):
            sold_by = re.sub(r"^sold by\s+", "", line, flags=re.IGNORECASE).strip()

        if not ships_from and low == "ships from" and i + 1 < len(lines):
            ships_from = lines[i + 1].strip()
        elif not ships_from and low.startswith("ships from "):
            ships_from = re.sub(r"^ships from\s+", "", line, flags=re.IGNORECASE).strip()
        if not rating:
            m = re.search(r"([0-9.]+)\s*out of 5 stars", line, re.IGNORECASE)
            if m:
                rating = m.group(1)
        if not review_count:
            m = re.search(r"([0-9,]+)\s+ratings?", line, re.IGNORECASE)
            if m:
                review_count = m.group(1).replace(",", "")
        if not asin:
            m = re.search(r"\bASIN\b[^A-Z0-9]*([A-Z0-9]{10})", line, re.IGNORECASE)
            if m:
                asin = m.group(1).upper()

        if not price:
            pm = PRICE_RE.search(line)
            if pm:
                currency = pm.group(1)
                price = pm.group(2).replace(",", "")

    bullets = parse_bullets_from_text(raw_content)
    specs = parse_specs_from_text(raw_content)
    if not asin:
        m = ASIN_TEXT_RE.search(raw_content)
        if m:
            asin = m.group(1).upper()

    if bullets:
        description = bullets[0]

    if title.lower() == "amazon.com":
        title = ""
    seller = sold_by or ships_from

    core = {
        "title": title,
        "brand": brand,
        "price": price,
        "currency": currency,
        "availability": availability,
        "seller": seller,
        "sold_by": sold_by,
        "ships_from": ships_from,
        "bullets": bullets,
        "description": description,
        "specs": specs,
        "images": images,
        "colors": colors,
        "sizes": sizes,
        "rating": rating,
        "review_count": review_count,
    }
    return core, asin


def fetch_with_extract_skill(url: str, timeout: int, script_path: str = DEFAULT_EXTRACT_SCRIPT) -> Optional[Dict[str, Any]]:
    if not script_path or not Path(script_path).is_file():
        return None

    payload = {
        "urls": [url],
        "extract_depth": "advanced",
        "format": "text",
        "include_images": True,
    }
    cmd = ["bash", script_path, json.dumps(payload, ensure_ascii=False)]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=max(30, timeout * 3),
        check=False,
    )
    if proc.returncode != 0:
        return None

    parsed = parse_json_blob(proc.stdout)
    if not parsed:
        return None

    results = parsed.get("results") if isinstance(parsed, dict) else None
    if not isinstance(results, list) or not results:
        return None

    first = results[0] if isinstance(results[0], dict) else {}
    raw_content = first.get("raw_content", "") or ""
    images_raw = first.get("images", []) or []
    images: List[str] = []
    for item in images_raw:
        if isinstance(item, str) and item.startswith("http"):
            images.append(item)
        elif isinstance(item, dict):
            maybe = item.get("url")
            if isinstance(maybe, str) and maybe.startswith("http"):
                images.append(maybe)
    images = [u for u in images if is_probable_product_image_url(u) and not is_too_small_image(u)]

    if not images:
        images = sorted(
            {
                u.rstrip('\\"\'')
                for u in URL_RE.findall(raw_content)
                if is_probable_product_image_url(u) and not is_too_small_image(u)
            }
        )

    core, asin = parse_core_from_text(raw_content, images)
    return {
        "core": core,
        "asin": asin,
        "source": "extract",
    }


def clean_text(raw: str) -> str:
    value = re.sub(r"<[^>]+>", " ", raw)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_between(source: str, start_pat: str, end_pat: str, flags: int = re.IGNORECASE | re.DOTALL) -> str:
    m = re.search(start_pat + r"(.*?)" + end_pat, source, flags)
    return clean_text(m.group(1)) if m else ""


def get_first_match(patterns: List[str], source: str) -> str:
    for pat in patterns:
        m = re.search(pat, source, re.IGNORECASE | re.DOTALL)
        if m:
            return clean_text(m.group(1))
    return ""


def parse_specs(html_text: str) -> Dict[str, str]:
    specs: Dict[str, str] = {}
    table_ids = [
        "productDetails_techSpec_section_1",
        "productDetails_detailBullets_sections1",
        "technicalSpecifications_section_1",
    ]
    for table_id in table_ids:
        block = extract_between(
            html_text,
            rf'<table[^>]*id="{re.escape(table_id)}"[^>]*>',
            r"</table>",
        )
        if not block:
            continue
        row_matches = re.findall(
            r"<tr[^>]*>\s*(?:<th[^>]*>(.*?)</th>)?\s*(?:<td[^>]*>(.*?)</td>)?\s*</tr>",
            block,
            re.IGNORECASE | re.DOTALL,
        )
        for key_raw, val_raw in row_matches:
            key = clean_text(key_raw)
            val = clean_text(val_raw)
            if key and val and key not in specs:
                specs[key] = val

    bullets = extract_between(
        html_text,
        r'<div[^>]*id="detailBullets_feature_div"[^>]*>',
        r"</div>",
    )
    for m in re.finditer(r"([A-Za-z][A-Za-z \-/]+):\s*([^\n]+)", bullets):
        key = clean_text(m.group(1))
        val = clean_text(m.group(2))
        if key and val and key not in specs:
            specs[key] = val

    return specs


def parse_variants(html_text: str, section_id: str) -> List[str]:
    section = extract_between(
        html_text,
        rf'<div[^>]*id="{re.escape(section_id)}"[^>]*>',
        r"</div>",
    )
    if not section:
        return []

    values = set()
    for m in re.finditer(r"alt=\"([^\"]+)\"", section, re.IGNORECASE):
        txt = clean_text(m.group(1))
        if txt and txt.lower() not in {"selected", "image"}:
            values.add(txt)
    for m in re.finditer(r'<span[^>]*class="[^"]*a-size-base[^"]*"[^>]*>(.*?)</span>', section, re.IGNORECASE | re.DOTALL):
        txt = clean_text(m.group(1))
        if txt and len(txt) < 40:
            values.add(txt)

    return sorted(values)


def parse_images(html_text: str) -> List[str]:
    urls: set[str] = set()

    for m in re.finditer(r'data-a-dynamic-image="([^"]+)"', html_text, re.IGNORECASE):
        raw = html.unescape(m.group(1))
        try:
            payload = json.loads(raw)
            for key in payload.keys():
                if isinstance(key, str) and key.startswith("http"):
                    urls.add(key)
        except Exception:
            pass

    for m in re.finditer(r'"hiRes"\s*:\s*"([^"]+)"', html_text):
        if m.group(1).startswith("http"):
            urls.add(m.group(1))
    for m in re.finditer(r'"large"\s*:\s*"([^"]+)"', html_text):
        if m.group(1).startswith("http"):
            urls.add(m.group(1))

    for m in URL_RE.finditer(html_text):
        url = m.group(0).replace("\\u0026", "&")
        if "m.media-amazon.com/images" in url:
            urls.add(url.rstrip('\\"\''))

    cleaned = sorted(urls)
    final_images = [
        u
        for u in cleaned
        if is_probable_product_image_url(u)
        and not is_too_small_image(u)
        and not looks_like_icon_asset(u)
        and (has_explicit_size_marker(u) or "/aplus-media-library-service-media/" in u.lower())
    ]
    final_images = sorted(
        list(dict.fromkeys(final_images)),
        key=lambda u: (-image_quality_score(u), u),
    )

    if final_images:
        return final_images

    fallback = sorted(
        {
            u
            for u in cleaned
            if ("m.media-amazon.com/images/i/" in u.lower() or "images-na.ssl-images-amazon.com/images/i/" in u.lower())
            and not is_too_small_image(u)
            and not looks_like_icon_asset(u)
            and (has_explicit_size_marker(u) or "/aplus-media-library-service-media/" in u.lower())
        }
    )
    fallback = sorted(
        list(dict.fromkeys(fallback)),
        key=lambda u: (-image_quality_score(u), u),
    )
    return fallback


def detect_block_reason(html_text: str, status_code: int) -> Optional[str]:
    low = html_text.lower()
    if status_code == 404:
        return "NOT_FOUND"
    if "captcha" in low or "enter the characters you see below" in low:
        return "CAPTCHA_REQUIRED"
    if "automated access to amazon data" in low or "sorry, we just need to make sure you're not a robot" in low:
        return "BLOCKED_BY_BOT"
    if status_code >= 500:
        return "BLOCKED_BY_BOT"
    return None


def extract_core(html_text: str) -> Dict[str, Any]:
    title = get_first_match([
        r'<span[^>]*id="productTitle"[^>]*>(.*?)</span>',
        r"<title[^>]*>(.*?)</title>",
    ], html_text)
    if title.strip().lower() == "amazon.com":
        title = ""

    brand = get_first_match([
        r'<a[^>]*id="bylineInfo"[^>]*>(.*?)</a>',
        r'"brand"\s*:\s*"([^"]+)"',
    ], html_text)

    currency, price = extract_buybox_price(html_text)
    if not price:
        price_text = get_first_match([
            r'<span[^>]*id="priceblock_ourprice"[^>]*>(.*?)</span>',
            r'<span[^>]*id="priceblock_dealprice"[^>]*>(.*?)</span>',
            r'<span[^>]*class="a-offscreen"[^>]*>(.*?)</span>',
        ], html_text)
        pm = PRICE_RE.search(price_text)
        if pm:
            currency = pm.group(1)
            price = pm.group(2).replace(",", "")

    availability = get_first_match([
        r'<div[^>]*id="availability"[^>]*>\s*<span[^>]*>(.*?)</span>',
        r'"availability"\s*:\s*"([^"]+)"',
    ], html_text)

    seller = get_first_match([
        r'<div[^>]*id="merchant-info"[^>]*>(.*?)</div>',
        r'<a[^>]*id="sellerProfileTriggerId"[^>]*>(.*?)</a>',
    ], html_text)
    sold_by, ships_from = parse_shipping_seller(seller)
    seller = sold_by or ships_from or seller

    bullets_block = extract_between(
        html_text,
        r'<div[^>]*id="feature-bullets"[^>]*>',
        r"</div>",
    )
    bullets = []
    for m in re.finditer(r"<span[^>]*class=\"a-list-item\"[^>]*>(.*?)</span>", bullets_block, re.IGNORECASE | re.DOTALL):
        txt = clean_text(m.group(1))
        if txt and txt.lower() != "" and "make sure this fits" not in txt.lower():
            bullets.append(txt)
    bullets = list(dict.fromkeys(bullets))

    description = get_first_match([
        r'<div[^>]*id="productDescription"[^>]*>\s*<p[^>]*>(.*?)</p>',
        r'<meta[^>]*name="description"[^>]*content="([^"]+)"',
    ], html_text)

    rating_text = get_first_match([
        r'<span[^>]*id="acrPopover"[^>]*title="([^"]+)"',
        r'([0-9.]+\s+out of 5 stars)',
    ], html_text)
    rating_value = ""
    rm = re.search(r"([0-9.]+)", rating_text)
    if rm:
        rating_value = rm.group(1)

    review_count_text = get_first_match([
        r'<span[^>]*id="acrCustomerReviewText"[^>]*>(.*?)</span>',
    ], html_text)
    review_count = ""
    rcm = re.search(r"([0-9,]+)", review_count_text)
    if rcm:
        review_count = rcm.group(1).replace(",", "")

    images = parse_images(html_text)
    specs = parse_specs(html_text)
    colors = parse_variants(html_text, "variation_color_name")
    sizes = parse_variants(html_text, "variation_size_name")

    return {
        "title": title,
        "brand": brand,
        "price": price,
        "currency": currency,
        "availability": availability,
        "seller": seller,
        "sold_by": sold_by,
        "ships_from": ships_from,
        "bullets": bullets,
        "description": description,
        "specs": specs,
        "images": images,
        "colors": colors,
        "sizes": sizes,
        "rating": rating_value,
        "review_count": review_count,
    }


def score_coverage(core: Dict[str, Any], asin: str) -> Tuple[float, List[str]]:
    title = (core.get("title") or "").strip().lower()
    checks = {
        "asin": bool(asin),
        "title": bool(title and title != "amazon.com"),
        "price": bool(core.get("price")),
        "availability": bool(core.get("availability")),
        "main_image": bool(core.get("images")),
        "bullets_or_description": bool(core.get("bullets") or core.get("description")),
        "specs": bool(core.get("specs")),
    }
    missing = [k for k, v in checks.items() if not v]
    coverage = (len(checks) - len(missing)) / len(checks)
    return coverage, missing


def merge_core(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(primary)
    title_primary = (primary.get("title") or "").strip().lower()
    title_fallback = (fallback.get("title") or "").strip()
    if (not title_primary or title_primary == "amazon.com") and title_fallback:
        merged["title"] = title_fallback

    scalar_fields = [
        "brand",
        "price",
        "currency",
        "availability",
        "seller",
        "sold_by",
        "ships_from",
        "description",
        "rating",
        "review_count",
    ]
    for field in scalar_fields:
        if not merged.get(field) and fallback.get(field):
            merged[field] = fallback[field]

    merged_specs = dict(fallback.get("specs", {}))
    merged_specs.update(primary.get("specs", {}))
    merged["specs"] = merged_specs

    for list_field in ["bullets", "images", "colors", "sizes"]:
        first = primary.get(list_field, []) or []
        second = fallback.get(list_field, []) or []
        merged[list_field] = list(dict.fromkeys([*first, *second]))

    return merged


def build_result(
    input_type: str,
    input_value: str,
    asin: str,
    canonical_url: str,
    fetch: FetchResult,
    core: Dict[str, Any],
    block_reason: Optional[str],
    fallback_source: str,
    verify_main_image: bool,
    image_check_timeout: int,
) -> Dict[str, Any]:
    coverage, missing = score_coverage(core, asin)
    title_ok = bool((core.get("title") or "").strip() and (core.get("title") or "").strip().lower() != "amazon.com")

    image_list = core.get("images") or []
    product_images, other_images = split_media_images(image_list)
    product_main_image, main_image_verified = select_main_image_with_verification(
        product_images=product_images,
        fallback_images=image_list,
        verify=verify_main_image,
        timeout=image_check_timeout,
    )
    has_media = bool(product_main_image and product_images)

    if block_reason and coverage < 0.3:
        status = "error"
        error_code = block_reason
    elif coverage >= 0.8 and has_media and title_ok:
        status = "success"
        error_code = ""
    else:
        status = "partial_success"
        error_code = block_reason or "PARTIAL_SUCCESS"

    return {
        "schema_version": "1.0.0",
        "status": status,
        "input": {
            "type": input_type,
            "value": input_value,
            "marketplace": "amazon.com",
        },
        "asin": asin,
        "canonical_url": canonical_url,
        "product": {
            "title": core.get("title", ""),
            "brand": core.get("brand", ""),
            "category_path": "",
        },
        "offer": {
            "price": core.get("price", ""),
            "currency": core.get("currency", ""),
            "availability": core.get("availability", ""),
            "seller": core.get("seller", ""),
            "sold_by": core.get("sold_by", ""),
            "ships_from": core.get("ships_from", ""),
        },
        "content": {
            "bullets": core.get("bullets", []),
            "description": core.get("description", ""),
        },
        "specs": core.get("specs", {}),
        "media": {
            "product_main_image": product_main_image,
            "product_images": product_images,
            "other_images": other_images,
            "variant_images": {},
        },
        "variant": {
            "colors": core.get("colors", []),
            "sizes": core.get("sizes", []),
            "selected_variant": {},
        },
        "rating": {
            "star": core.get("rating", ""),
            "review_count": core.get("review_count", ""),
        },
        "diagnostics": {
            "fetch_mode": fetch.mode,
            "final_url": fetch.final_url,
            "http_status": fetch.status_code,
            "confidence": round(coverage, 4),
            "missing_fields": missing,
            "error_code": error_code,
            "fallback_source": fallback_source,
            "main_image_verified": main_image_verified,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Amazon product details and image URLs.")
    parser.add_argument("input", help="Amazon product URL or ASIN")
    parser.add_argument("--marketplace", default="www.amazon.com", help="Marketplace domain")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--image-check-timeout", type=int, default=4, help="Timeout (seconds) for main image URL validation")
    parser.add_argument("--no-headless", action="store_true", help="Disable headless fallback")
    parser.add_argument("--no-verify-main-image", action="store_true", help="Disable main image URL reachability verification")
    parser.add_argument("--no-extract-fallback", action="store_true", help="Disable extract skill fallback")
    parser.add_argument("--extract-script", default="", help="Path to extract skill script")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--output", help="Write JSON output to file")
    parser.add_argument("--error-json", action="store_true", help="Emit errors as JSON")
    args = parser.parse_args()

    try:
        input_type, asin, url = normalize_input(args.input, args.marketplace)
        extract_script_path = resolve_extract_script_path(args.extract_script)
        fetch = fetch_with_requests(url, timeout=args.timeout)
        block_reason = detect_block_reason(fetch.html, fetch.status_code)
        core = extract_core(fetch.html)
        coverage, _ = score_coverage(core, asin)
        fallback_source = ""

        use_headless = (
            not args.no_headless and (block_reason in {"CAPTCHA_REQUIRED", "BLOCKED_BY_BOT"} or coverage < 0.45)
        )
        if use_headless:
            alt = fetch_with_playwright(url, timeout=args.timeout)
            if alt is not None:
                alt_block = detect_block_reason(alt.html, alt.status_code)
                alt_core = extract_core(alt.html)
                alt_cov, _ = score_coverage(alt_core, asin)
                if alt_cov >= coverage:
                    fetch = alt
                    core = alt_core
                    block_reason = alt_block
                    coverage = alt_cov

        use_extract = (
            not args.no_extract_fallback
            and (block_reason in {"CAPTCHA_REQUIRED", "BLOCKED_BY_BOT"} or coverage < 0.6 or not core.get("images"))
        )
        if use_extract:
            extra = fetch_with_extract_skill(url, timeout=args.timeout, script_path=extract_script_path)
            if extra is not None:
                merged = merge_core(core, extra.get("core", {}))
                merged_cov, _ = score_coverage(merged, asin or extra.get("asin", ""))
                if merged_cov >= coverage or (not core.get("images") and merged.get("images")):
                    core = merged
                    coverage = merged_cov
                    fallback_source = extra.get("source", "extract")
                    fetch.mode = f"{fetch.mode}+{fallback_source}"
                    if not asin and extra.get("asin"):
                        asin = extra["asin"]

        if not asin:
            m = ASIN_IN_URL_RE.search(fetch.final_url)
            if m:
                asin = m.group(1).upper()

        canonical = f"https://www.amazon.com/dp/{asin}" if asin else url
        result = build_result(
            input_type=input_type,
            input_value=args.input,
            asin=asin,
            canonical_url=canonical,
            fetch=fetch,
            core=core,
            block_reason=block_reason,
            fallback_source=fallback_source,
            verify_main_image=not args.no_verify_main_image,
            image_check_timeout=max(1, args.image_check_timeout),
        )

        output = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output + "\n")
        else:
            print(output)

    except Exception as exc:
        if args.error_json:
            err = {
                "schema_version": "1.0.0",
                "status": "error",
                "diagnostics": {
                    "error_code": "EXTRACTION_FAILED",
                    "message": str(exc),
                },
            }
            print(json.dumps(err, ensure_ascii=False, indent=2 if args.pretty else None))
            return
        raise


if __name__ == "__main__":
    main()
