import unittest
from datetime import date
from unittest.mock import patch

from notifier.adapters.homebox import HomeboxAdapter


class HomeboxTests(unittest.TestCase):
    def test_date_parsing(self) -> None:
        self.assertEqual(
            HomeboxAdapter._parse_date("2026-09-30T00:00:00Z"),
            date(2026, 9, 30),
        )

    def test_empty_date(self) -> None:
        self.assertIsNone(HomeboxAdapter._parse_date(""))

    def test_expired_warranty_is_excluded(self) -> None:
        adapter = HomeboxAdapter(
            {
                "api_url": "http://homebox.test",
                "api_key": "test-api-key",
                "remind_days": 30,
            },
            timeout=20,
        )
        adapter._summaries = lambda: [
            {"id": "expired", "name": "旧设备"},
            {"id": "upcoming", "name": "新设备"},
        ]

        def fake_get(path, params=None):
            del params
            if path.endswith("expired"):
                return {
                    "name": "旧设备",
                    "warrantyExpires": "2026-09-06",
                }
            return {
                "name": "新设备",
                "warrantyExpires": "2026-09-20",
            }

        adapter._get = fake_get
        with patch("notifier.adapters.homebox.date") as mocked_date:
            mocked_date.today.return_value = date(2026, 9, 7)
            alerts = adapter._warranties()

        self.assertEqual([item["name"] for item in alerts], ["新设备"])


if __name__ == "__main__":
    unittest.main()
