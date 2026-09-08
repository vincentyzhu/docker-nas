import json
import unittest
from types import SimpleNamespace

from notifier.adapters.frigate import FrigateAdapter


class FakeDingTalk:
    def __init__(self) -> None:
        self.notifications = []

    def send(self, notification) -> None:
        self.notifications.append(notification)


class FrigateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dingtalk = FakeDingTalk()
        self.adapter = FrigateAdapter(
            {
                "mqtt": {"host": "mqtt.test", "port": 1883},
                "cooldown_seconds": 0,
                "watch_labels": ["person"],
            },
            self.dingtalk,
        )

    @staticmethod
    def message(event_id: str, event_type: str = "new"):
        payload = {
            "type": event_type,
            "after": {
                "id": event_id,
                "camera": "front_door",
                "label": "person",
                "start_time": 1788748800,
            },
        }
        return SimpleNamespace(payload=json.dumps(payload).encode("utf-8"))

    def test_zero_cooldown_sends_each_new_event(self) -> None:
        self.adapter._on_message(None, None, self.message("event-1"))
        self.adapter._on_message(None, None, self.message("event-2"))
        self.assertEqual(len(self.dingtalk.notifications), 2)

    def test_non_new_event_is_ignored(self) -> None:
        self.adapter._on_message(
            None,
            None,
            self.message("event-1", event_type="update"),
        )
        self.assertEqual(self.dingtalk.notifications, [])


if __name__ == "__main__":
    unittest.main()
