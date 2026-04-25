from strategies.email import EmailStrategy
from strategies.notification_channel import NotificationChannel
from strategies.push import PushStrategy
from strategies.sms import SmsStrategy


class UnknownChannelError(ValueError):
    pass


class ChannelFactory:
    def __init__(self) -> None:
        strategies: list[NotificationChannel] = [
            SmsStrategy(),
            EmailStrategy(),
            PushStrategy(),
        ]
        self._strategies = {
            strategy.channel_name.casefold(): strategy for strategy in strategies
        }

    def get(self, channel_name: str) -> NotificationChannel:
        strategy = self._strategies.get(channel_name.casefold())
        if strategy is None:
            raise UnknownChannelError(f"No strategy registered for {channel_name}")
        return strategy
