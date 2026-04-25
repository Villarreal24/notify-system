from types import SimpleNamespace
from uuid import UUID

import pytest

from strategies.factory import ChannelFactory, UnknownChannelError
from strategies import email as email_module
from strategies import push as push_module
from strategies import sms as sms_module


@pytest.mark.asyncio
async def test_channel_factory_resolves_seeded_channels(monkeypatch) -> None:
    user = SimpleNamespace(
        id=UUID("a1b2c3d4-0000-0000-0000-000000000001"),
        email="alice@example.com",
        phone_number="+1234567890",
    )
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(sms_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(email_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(push_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(sms_module.random, "random", lambda: 0.99)
    monkeypatch.setattr(email_module.random, "random", lambda: 0.99)
    monkeypatch.setattr(push_module.random, "random", lambda: 0.99)
    monkeypatch.setattr(sms_module.random, "uniform", lambda minimum, maximum: minimum)
    monkeypatch.setattr(email_module.random, "uniform", lambda minimum, maximum: minimum)
    monkeypatch.setattr(push_module.random, "uniform", lambda minimum, maximum: minimum)
    factory = ChannelFactory()

    sms = await factory.get("SMS").send(user=user, message="Game starts")
    email = await factory.get("E-Mail").send(user=user, message="Market alert")
    push = await factory.get("Push Notification").send(user=user, message="New movie")

    assert sms.delivered is True
    assert sms.recipient == "+1234567890"
    assert email.recipient == "alice@example.com"
    assert push.recipient == str(user.id)
    assert sleep_calls == [1.0, 0.5, 1.0]


@pytest.mark.asyncio
async def test_channel_strategy_can_simulate_provider_failure(monkeypatch) -> None:
    user = SimpleNamespace(
        id=UUID("a1b2c3d4-0000-0000-0000-000000000001"),
        email="alice@example.com",
        phone_number="+1234567890",
    )
    factory = ChannelFactory()
    monkeypatch.setattr(sms_module.random, "random", lambda: 0.01)

    with pytest.raises(RuntimeError, match="Simulated SMS provider timeout"):
        await factory.get("SMS").send(user=user, message="Game starts")


def test_channel_factory_rejects_unknown_channel() -> None:
    factory = ChannelFactory()

    with pytest.raises(UnknownChannelError):
        factory.get("Fax")
