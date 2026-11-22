import unittest
from unittest.mock import patch

from notifier.adapters.canventory import CanventoryAdapter


class CanventoryTests(unittest.TestCase):
    def test_quantity_with_unit(self) -> None:
        self.assertEqual(
            CanventoryAdapter._quantity({"quantity": 2.5, "quantity_unit": "千克"}),
            "2.5千克",
        )

    @patch.dict("os.environ", {"CANVENTORY_PASSWORD": "test-password"})
    @patch("notifier.adapters.canventory.requests.get")
    @patch("notifier.adapters.canventory.requests.post")
    def test_collect_is_limited_to_expected_single_home(self, post, get) -> None:
        adapter = CanventoryAdapter(
            {"api_url": "https://canventory.example.com", "username": "a", "home_id": 4},
            20,
        )
        post.return_value.json.return_value = {"access_token": "test-token"}
        get.return_value.json.side_effect = [
            [{"id": 4, "name": "家庭 A"}, {"id": 5, "name": "家庭 B"}],
            [{"id": 4, "name": "家庭 A"}],
            {"expired_items": [{"item_name": "牛奶"}]},
        ]
        with self.assertRaisesRegex(RuntimeError, "仅属于配置的家庭"):
            adapter.collect(False)
        self.assertEqual(get.call_count, 1)

        result = adapter.collect(False)
        self.assertIn("家庭 A", result.title)
        self.assertIn("牛奶", result.plain_text)
        self.assertEqual(get.call_args.args[0], "https://canventory.example.com/api/items/alerts")


if __name__ == "__main__":
    unittest.main()
