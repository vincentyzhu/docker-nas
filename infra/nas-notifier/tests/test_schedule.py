import unittest
from datetime import datetime

from notifier.config import ConfigError
from notifier.schedule import next_scheduled_run, parse_notify_time


class ScheduleTests(unittest.TestCase):
    def test_next_run_today(self) -> None:
        now = datetime(2026, 9, 7, 7, 30)
        self.assertEqual(
            next_scheduled_run(8, 0, now),
            datetime(2026, 9, 7, 8, 0),
        )

    def test_next_run_tomorrow_after_notify_time(self) -> None:
        now = datetime(2026, 9, 7, 8, 0)
        self.assertEqual(
            next_scheduled_run(8, 0, now),
            datetime(2026, 9, 8, 8, 0),
        )

    def test_invalid_time(self) -> None:
        with self.assertRaises(ConfigError):
            parse_notify_time("25:00")


if __name__ == "__main__":
    unittest.main()
