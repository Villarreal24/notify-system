import asyncio
import random

from models import User
from strategies.notification_channel import SendResult


class EmailStrategy:
    channel_name = "E-Mail"

    async def send(self, *, user: User, message: str) -> SendResult:
        if random.random() < 0.15:
            raise RuntimeError("Simulated e-mail provider timeout")

        await asyncio.sleep(random.uniform(0.5, 2.0))

        return SendResult(
            channel_name=self.channel_name,
            recipient=user.email,
            delivered=True,
            detail=f"Simulated e-mail sent to {user.email}: {message}",
        )
