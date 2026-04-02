import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.automation_engine import AutomationEngine


def make_rule(**kwargs):
    r = MagicMock()
    r.id = kwargs.get("id", 1)
    r.metric = kwargs.get("metric", "temperature")
    r.operator = kwargs.get("operator", ">")
    r.threshold_value = kwargs.get("threshold_value", 30)
    r.alert_level = kwargs.get("alert_level", "MEDIUM")
    r.alert_message = kwargs.get("alert_message", "Too hot")
    r.target_device_id = kwargs.get("target_device_id", None)
    r.action = kwargs.get("action", "ON")
    r.name = kwargs.get("name", "Test rule")
    return r


def make_reading(**kwargs):
    r = MagicMock()
    r.room_id = kwargs.get("room_id", 1)
    r.temperature = kwargs.get("temperature", 35)
    r.humidity = kwargs.get("humidity", 60)
    r.co2 = kwargs.get("co2", 800)
    r.motion_detected = kwargs.get("motion_detected", None)
    return r


class TestAutomationEngine:
    def setup_method(self):
        self.engine = AutomationEngine()

    async def test_rule_triggered_creates_alert(self):
        rule = make_rule(metric="temperature", operator=">", threshold_value=30)
        reading = make_reading(temperature=35)

        alert_mock = MagicMock()
        alert_mock.id = 42

        alert_service = MagicMock()
        alert_service.get_open_alert = AsyncMock(return_value=None)
        alert_service.create = AsyncMock(return_value=alert_mock)

        device_service = MagicMock()

        result = await self.engine.evaluate_rules(
            reading=reading,
            rules=[rule],
            alert_service=alert_service,
            device_service=device_service,
            db=AsyncMock(),
        )

        alert_service.create.assert_called_once()
        assert result[0]["alert_id"] == 42

    async def test_rule_not_triggered_no_alert(self):
        rule = make_rule(metric="temperature", operator=">", threshold_value=30)
        reading = make_reading(temperature=25)  # below threshold

        alert_service = MagicMock()
        alert_service.get_open_alert = AsyncMock(return_value=None)
        alert_service.create = AsyncMock()
        device_service = MagicMock()

        result = await self.engine.evaluate_rules(
            reading=reading, rules=[rule],
            alert_service=alert_service, device_service=device_service, db=AsyncMock(),
        )

        alert_service.create.assert_not_called()
        assert result == []

    async def test_no_duplicate_alert_when_open_exists(self):
        rule = make_rule()
        reading = make_reading(temperature=35)

        existing_alert = MagicMock()
        existing_alert.id = 10

        alert_service = MagicMock()
        alert_service.get_open_alert = AsyncMock(return_value=existing_alert)
        alert_service.create = AsyncMock()
        device_service = MagicMock()

        result = await self.engine.evaluate_rules(
            reading=reading, rules=[rule],
            alert_service=alert_service, device_service=device_service, db=AsyncMock(),
        )

        alert_service.create.assert_not_called()  # không tạo mới
        assert result[0]["alert_id"] == 10  # dùng alert cũ

    async def test_device_controlled_when_target_set(self):
        rule = make_rule(target_device_id=5, action="ON")
        reading = make_reading(temperature=35)

        alert_mock = MagicMock()
        alert_mock.id = 1

        alert_service = MagicMock()
        alert_service.get_open_alert = AsyncMock(return_value=None)
        alert_service.create = AsyncMock(return_value=alert_mock)

        device_mock = MagicMock()
        device_mock.id = 5
        device_service = MagicMock()
        device_service.control = AsyncMock(return_value=device_mock)

        result = await self.engine.evaluate_rules(
            reading=reading, rules=[rule],
            alert_service=alert_service, device_service=device_service, db=AsyncMock(),
        )

        device_service.control.assert_called_once()
        assert result[0]["device_id"] == 5

    async def test_device_not_found_does_not_crash(self):
        rule = make_rule(target_device_id=99)
        reading = make_reading(temperature=35)

        alert_mock = MagicMock()
        alert_mock.id = 1

        alert_service = MagicMock()
        alert_service.get_open_alert = AsyncMock(return_value=None)
        alert_service.create = AsyncMock(return_value=alert_mock)

        device_service = MagicMock()
        device_service.control = AsyncMock(side_effect=ValueError("Device not found"))

        result = await self.engine.evaluate_rules(
            reading=reading, rules=[rule],
            alert_service=alert_service, device_service=device_service, db=AsyncMock(),
        )

        # alert vẫn được tạo, không crash
        assert len(result) == 1
        assert "device_id" not in result[0]

    async def test_multiple_rules_evaluated(self):
        rules = [
            make_rule(id=1, metric="temperature", operator=">", threshold_value=30),
            make_rule(id=2, metric="co2", operator=">", threshold_value=1000),
        ]
        reading = make_reading(temperature=35, co2=1200)

        def make_alert(id):
            a = MagicMock()
            a.id = id
            return a

        alert_service = MagicMock()
        alert_service.get_open_alert = AsyncMock(return_value=None)
        alert_service.create = AsyncMock(side_effect=[make_alert(1), make_alert(2)])
        device_service = MagicMock()

        result = await self.engine.evaluate_rules(
            reading=reading, rules=rules,
            alert_service=alert_service, device_service=device_service, db=AsyncMock(),
        )

        assert len(result) == 2

    async def test_none_sensor_value_skips_rule(self):
        rule = make_rule(metric="humidity", operator=">", threshold_value=80)
        reading = make_reading(humidity=None)  # sensor không có dữ liệu

        alert_service = MagicMock()
        alert_service.get_open_alert = AsyncMock(return_value=None)
        alert_service.create = AsyncMock()
        device_service = MagicMock()

        result = await self.engine.evaluate_rules(
            reading=reading, rules=[rule],
            alert_service=alert_service, device_service=device_service, db=AsyncMock(),
        )

        alert_service.create.assert_not_called()
        assert result == []
