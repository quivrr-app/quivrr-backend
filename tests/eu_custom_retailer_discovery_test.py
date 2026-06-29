import unittest

from scrapers.retailers.europe.common.discovery_utils import (
    product_rows_from_structured_thumbnail_cards,
)


SURF_PIRATES_LISTING_HTML = """
<div class="p-c thumbnail" id="result-wrapper_buy_form_76019">
  <a class="img-w block" href="https://www.surfpirates.de/NORDEN-First-Ride-Malibu-72-white_1?gclid=test">
    <img src="https://www.surfpirates.de/media/image/product/76019/sm/norden-first-ride-malibu.jpg" alt="NORDEN First Ride Malibu" />
  </a>
  <div class="caption">
    <a class="title block h4 m0" href="https://www.surfpirates.de/NORDEN-First-Ride-Malibu-72-white_1?gclid=test">
      NORDEN First Ride Malibu
    </a>
    <div class="price_wrapper">
      <meta itemprop="price" content="593.00" />
    </div>
  </div>
  <div class="delivery-status">
    <div class="signal_image status-2 small">Avaliable in store &amp; online</div>
  </div>
</div>
<div class="p-c thumbnail" id="result-wrapper_buy_form_132353">
  <a class="img-w block" href="https://www.surfpirates.de/Surfboard-TORQ-TET-76-MOD-Fun-Pinline_1">
    <img src="https://www.surfpirates.de/media/image/product/132353/sm/surfboard-torq-tet-76-mod-fun-pinline.jpg" alt="Surfboard TORQ TET 7.6 MOD Fun Pinline" />
  </a>
  <div class="caption">
    <a class="title block h4 m0" href="https://www.surfpirates.de/Surfboard-TORQ-TET-76-MOD-Fun-Pinline_1">
      Surfboard TORQ TET 7.6 MOD Fun Pinline
    </a>
    <div class="price_wrapper">
      <meta itemprop="price" content="509.00" />
    </div>
  </div>
  <div class="delivery-status">
    <div class="signal_image status-2 small">Currently out of stock</div>
  </div>
</div>
"""


class EuCustomRetailerDiscoveryTests(unittest.TestCase):
    def test_structured_thumbnail_cards_extract_detail_urls(self):
        rows = product_rows_from_structured_thumbnail_cards(
            SURF_PIRATES_LISTING_HTML,
            "https://www.surfpirates.de/en/surfbords",
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            rows[0]["productUrl"],
            "https://www.surfpirates.de/NORDEN-First-Ride-Malibu-72-white_1",
        )
        self.assertEqual(rows[0]["priceAmount"], "593.00")
        self.assertTrue(rows[0]["isAvailable"])
        self.assertEqual(rows[1]["stockStatus"], "out_of_stock")
        self.assertEqual(
            rows[1]["productUrl"],
            "https://www.surfpirates.de/Surfboard-TORQ-TET-76-MOD-Fun-Pinline_1",
        )


if __name__ == "__main__":
    unittest.main()
