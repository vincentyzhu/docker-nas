import unittest
from datetime import datetime

from notifier.config import ConfigError
from notifier.policy import NotificationPolicy


class NotificationPolicyTests(unittest.TestCase):
    def test_missing_policy_keeps_existing_behavior(self) -> None:
        policy = NotificationPolicy()
        self.assertTrue(policy.allows(datetime(2026, 1, 1, 2)))
        policy.validate_scheduled_time("08:00")

    def test_china_holiday_is_silent(self) -> None:
        policy = self.workday_policy()
        self.assertFalse(policy.allows(datetime(2026, 1, 1, 10)))

    def test_adjusted_weekend_workday_is_allowed(self) -> None:
        policy = self.workday_policy()
        self.assertTrue(policy.allows(datetime(2026, 1, 4, 10)))

    def test_time_ranges_include_start_and_exclude_end(self) -> None:
        policy = self.workday_policy()
        self.assertTrue(policy.allows(datetime(2026, 1, 4, 9)))
        self.assertFalse(policy.allows(datetime(2026, 1, 4, 12)))
        self.assertTrue(policy.allows(datetime(2026, 1, 4, 13)))
        self.assertFalse(policy.allows(datetime(2026, 1, 4, 18)))

    def test_scheduled_time_must_be_inside_a_range(self) -> None:
        policy = self.workday_policy()
        policy.validate_scheduled_time("09:00")
        with self.assertRaisesRegex(ConfigError, "不在"):
            policy.validate_scheduled_time("08:00")

    def test_invalid_calendar_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "calendar"):
            NotificationPolicy({"enabled": True, "calendar": "unknown"})

    @staticmethod
    def workday_policy() -> NotificationPolicy:
        return NotificationPolicy(
            {
                "enabled": True,
                "calendar": "china_workdays",
                "time_ranges": [
                    {"start": "09:00", "end": "12:00"},
                    {"start": "13:00", "end": "18:00"},
                ],
            }
        )


if __name__ == "__main__":
    unittest.main()
