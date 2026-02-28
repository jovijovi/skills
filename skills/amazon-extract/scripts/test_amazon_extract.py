#!/usr/bin/env python3
import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest import mock


MODULE_PATH = pathlib.Path(__file__).resolve().parent / "amazon_extract.py"
spec = importlib.util.spec_from_file_location("amazon_extract", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class AmazonExtractUnitTests(unittest.TestCase):
    def test_extract_buybox_price_display_price(self):
        raw = '{"desktop_buybox_group_1":[{"displayPrice":"$99.99","priceAmount":99.99,"currencySymbol":"$"}]}'
        currency, price = mod.extract_buybox_price(raw)
        self.assertEqual(currency, "$")
        self.assertEqual(price, "99.99")

    def test_extract_buybox_price_escaped(self):
        raw = '{\\"desktop_buybox_group_1\\":[{\\"displayPrice\\":\\"$23.74\\"}]}'
        currency, price = mod.extract_buybox_price(raw)
        self.assertEqual(currency, "$")
        self.assertEqual(price, "23.74")

    def test_to_hires_main_image(self):
        src = "https://m.media-amazon.com/images/I/61s8YkJvoPL._AC_SX425_.jpg"
        self.assertEqual(
            mod.to_hires_main_image(src),
            "https://m.media-amazon.com/images/I/61s8YkJvoPL._AC_SL1500_.jpg",
        )
        src2 = "https://m.media-amazon.com/images/I/21XLcrK44YL._AC_.jpg"
        self.assertEqual(
            mod.to_hires_main_image(src2),
            "https://m.media-amazon.com/images/I/21XLcrK44YL._AC_SL1500_.jpg",
        )

    def test_small_image_filtered(self):
        self.assertTrue(mod.is_too_small_image("https://m.media-amazon.com/images/I/516rYrCATYL._AC_US40_.jpg"))
        self.assertTrue(mod.is_too_small_image("https://m.media-amazon.com/images/I/51zbe-9IlJL.SS40_BG85,85,85_BR-120_PKdp-play-icon-overlay__.jpg"))

    def test_icon_asset_filtered(self):
        self.assertTrue(mod.looks_like_icon_asset("https://m.media-amazon.com/images/I/118nlf+F3RL.png"))
        self.assertFalse(mod.looks_like_icon_asset("https://m.media-amazon.com/images/I/61s8YkJvoPL._AC_SX425_.jpg"))

    def test_split_media_images(self):
        images = [
            "https://m.media-amazon.com/images/I/61s8YkJvoPL._AC_SX425_.jpg",
            "https://m.media-amazon.com/images/I/516rYrCATYL._AC_US40_.jpg",
            "https://m.media-amazon.com/images/G/01/books-detail-page-table-of-contents/blackback/ToC.png",
        ]
        product_images, other_images = mod.split_media_images(images)
        self.assertIn("https://m.media-amazon.com/images/I/61s8YkJvoPL._AC_SL1500_.jpg", product_images)
        self.assertEqual(len(other_images), 0)

    def test_parse_shipping_seller(self):
        text = "Ships from Amazon Sold by EufyHome Returns"
        sold_by, ships_from = mod.parse_shipping_seller(text)
        self.assertEqual(sold_by, "EufyHome")
        self.assertEqual(ships_from, "Amazon")

    def test_select_main_image_with_verification(self):
        with mock.patch.object(mod, "is_url_reachable", return_value=True):
            image, verified = mod.select_main_image_with_verification(
                product_images=["https://m.media-amazon.com/images/I/61s8YkJvoPL._AC_SL1500_.jpg"],
                fallback_images=[],
                verify=True,
                timeout=2,
            )
        self.assertTrue(verified)
        self.assertIn("_AC_SL1500_", image)

    def test_resolve_extract_script_path_priority(self):
        with tempfile.TemporaryDirectory() as td:
            custom = pathlib.Path(td) / "extract.sh"
            custom.write_text("#!/bin/bash\necho ok\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {mod.EXTRACT_SCRIPT_ENV: "/tmp/not-used.sh"}):
                resolved = mod.resolve_extract_script_path(str(custom))
        self.assertEqual(resolved, str(custom))


if __name__ == "__main__":
    unittest.main()
