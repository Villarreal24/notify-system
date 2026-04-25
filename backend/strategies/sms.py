import asyncio
import random

from models import User
from strategies.notification_channel import SendResult


class SmsStrategy:
    channel_name = "SMS"

    async def send(self, *, user: User, message: str) -> SendResult:
        if random.random() < 0.15:
            raise RuntimeError("Simulated SMS provider timeout")

        await asyncio.sleep(random.uniform(1.0, 3.0))

        return SendResult(
            channel_name=self.channel_name,
            recipient=user.phone_number,
            delivered=True,
            detail=f"Simulated SMS sent to {user.phone_number}: {message}",
        )
