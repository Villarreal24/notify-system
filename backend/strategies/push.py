import asyncio
import random

from models import User
from strategies.notification_channel import SendResult


class PushStrategy:
    channel_name = "Push Notification"

    async def send(self, *, user: User, message: str) -> SendResult:
        if random.random() < 0.15:
            raise RuntimeError("Simulated push provider timeout")

        await asyncio.sleep(random.uniform(1.0, 4.0))

        return SendResult(
            channel_name=self.channel_name,
            recipient=str(user.id),
            delivered=True,
            detail=f"Simulated push notification sent to user {user.id}: {message}",
        )
