from dataclasses import dataclass
from typing import Protocol

from models import User


@dataclass(frozen=True)
class SendResult:
    channel_name: str
    recipient: str
    delivered: bool
    detail: str


class NotificationChannel(Protocol):
    channel_name: str

    async def send(self, *, user: User, message: str) -> SendResult:
        """Simulate delivery through a notification channel."""
