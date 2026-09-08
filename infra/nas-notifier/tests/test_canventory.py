import unittest

from notifier.adapters.canventory import CanventoryAdapter


class CanventoryTests(unittest.TestCase):
    def test_quantity_with_unit(self) -> None:
        self.assertEqual(
            CanventoryAdapter._quantity({"quantity": 2.5, "quantity_unit": "千克"}),
            "2.5千克",
        )


if __name__ == "__main__":
    unittest.main()
