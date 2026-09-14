from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Notification:
    title: str
    text: str


class NotificationSender(Protocol):
    def send(self, notification: Notification) -> None:
        """Send one notification through the configured channel."""
