import unittest

from scrapers.products import woocommerce_scraper


class WooCommerceScraperTests(unittest.TestCase):
    def test_expand_board_category_ids_includes_children_of_board_parent(self):
        categories = [
            {"id": 380, "name": "Surfboards", "slug": "surfboards", "parent": 0},
            {"id": 916, "name": "Beginner Surfboards", "slug": "beginner-surfboards", "parent": 380},
            {"id": 70, "name": "Fish Surfboards", "slug": "fish-surfboards", "parent": 380},
            {"id": 110, "name": "Leg Ropes", "slug": "leg-ropes", "parent": 381},
            {"id": 381, "name": "Accessories", "slug": "accessories", "parent": 0},
        ]

        self.assertEqual(
            woocommerce_scraper.expand_board_category_ids(categories),
            [70, 380, 916],
        )

    def test_expand_board_category_ids_matches_board_like_leaf_categories(self):
        categories = [
            {"id": 47, "name": "Longboard", "slug": "longboard", "parent": 0},
            {"id": 140, "name": "Softboard", "slug": "softboard", "parent": 0},
            {"id": 143, "name": "Aloha", "slug": "aloha", "parent": 0},
        ]

        self.assertEqual(
            woocommerce_scraper.expand_board_category_ids(categories),
            [47, 140],
        )

    def test_expand_board_category_ids_excludes_accessory_and_non_surfboard_categories(self):
        categories = [
            {"id": 17, "name": "Second Hand Surfboards", "slug": "second-hand-surfboards", "parent": 380},
            {"id": 22, "name": "Surfboard Fins", "slug": "surfboard-fins", "parent": 381},
            {"id": 82, "name": "SUP Stand Up Paddle Boards", "slug": "sup", "parent": 386},
            {"id": 126, "name": "Bodyboards", "slug": "bodyboard", "parent": 382},
            {"id": 37797, "name": "Skateboard", "slug": "skateboard", "parent": 0},
        ]

        self.assertEqual(
            woocommerce_scraper.expand_board_category_ids(categories),
            [17],
        )


if __name__ == "__main__":
    unittest.main()
