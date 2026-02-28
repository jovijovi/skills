#!/usr/bin/env python3
import argparse
import json
import pathlib
import subprocess
import sys


SCRIPT = pathlib.Path(__file__).resolve().parent / "amazon_extract.py"
DEFAULT_URLS = [
    "https://www.amazon.com/eufy-Expandable-Compatibility-Military-Grade-Encryption/dp/B0BL8TSB2P/ref=zg_bs_g_17871150011_d_sccl_6/137-0841522-6644458",
    "https://www.amazon.com/dp/B0FQV8GMJ4/ref=sspa_dk_detail_0?psc=1",
    "https://www.amazon.com/dp/B0B42BWP7N/ref=sspa_dk_detail_3?psc=1",
]


def run_extract(url: str) -> dict:
    cmd = [
        sys.executable,
        str(SCRIPT),
        url,
        "--error-json",
        "--image-check-timeout",
        "3",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"extract command failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def assert_contract(payload: dict) -> None:
    for key in ["schema_version", "status", "asin", "product", "offer", "media", "diagnostics"]:
        assert key in payload, f"missing top-level key: {key}"

    media = payload.get("media", {})
    expected_order = ["product_main_image", "product_images", "other_images", "variant_images"]
    assert list(media.keys()) == expected_order, f"media key order mismatch: {list(media.keys())}"

    assert "main_image" not in media, "legacy key main_image should not exist"
    assert "gallery_images" not in media, "legacy key gallery_images should not exist"

    offer = payload.get("offer", {})
    assert "sold_by" in offer and "ships_from" in offer, "offer should contain sold_by and ships_from"

    diagnostics = payload.get("diagnostics", {})
    assert "main_image_verified" in diagnostics, "diagnostics.main_image_verified missing"


def main() -> None:
    parser = argparse.ArgumentParser(description="Contract smoke test for amazon_extract.py")
    parser.add_argument("urls", nargs="*", help="Amazon product URLs")
    args = parser.parse_args()

    urls = args.urls if args.urls else DEFAULT_URLS
    for idx, url in enumerate(urls, start=1):
        payload = run_extract(url)
        assert_contract(payload)
        print(f"[OK] contract #{idx}: status={payload.get('status')} asin={payload.get('asin')}")


if __name__ == "__main__":
    main()
