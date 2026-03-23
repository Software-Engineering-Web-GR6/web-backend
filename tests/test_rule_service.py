import pytest
from unittest.mock import ANY, AsyncMock, MagicMock
from app.services.rule_service import RuleService


def make_payload(**kwargs):
    defaults = {
        "metric": "temperature",
        "operator": ">",
        "threshold_value": 30,
        "action": "ON",
        "name": "Test rule",
        "alert_level": "MEDIUM",
        "alert_message": "Too hot",
        "room_id": 1,
        "is_active": True,
        "target_device_id": None,
    }
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    m.model_dump.return_value = defaults
    return m


class TestRuleServiceValidation:
    def setup_method(self):
        self.svc = RuleService()

    def test_valid_payload_passes(self):
        self.svc._validate(make_payload())  # should not raise

    def test_invalid_metric_raises(self):
        with pytest.raises(ValueError, match="metric must be one of"):
            self.svc._validate(make_payload(metric="pressure"))

    def test_invalid_operator_raises(self):
        with pytest.raises(ValueError, match="operator is invalid"):
            self.svc._validate(make_payload(operator="!="))

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError, match="action is invalid"):
            self.svc._validate(make_payload(action="TOGGLE"))

    def test_all_valid_metrics(self):
        for metric in ["temperature", "humidity", "co2", "motion_detected"]:
            self.svc._validate(make_payload(metric=metric))

    def test_all_valid_operators(self):
        for op in [">", "<", ">=", "<=", "=="]:
            self.svc._validate(make_payload(operator=op))

    def test_all_valid_actions(self):
        for action in ["ON", "OFF", "OPEN", "CLOSE"]:
            self.svc._validate(make_payload(action=action))


class TestRuleServiceUpdate:
    def setup_method(self):
        self.svc = RuleService()

    async def test_update_rule_not_found_raises(self):
        from unittest.mock import patch
        with patch("app.services.rule_service.rule_repository") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(ValueError, match="Rule not found"):
                payload = MagicMock()
                payload.model_dump.return_value = {}
                await self.svc.update(db=AsyncMock(), rule_id=99, payload=payload)

    async def test_delete_rule_not_found_raises(self):
        from unittest.mock import patch
        with patch("app.services.rule_service.rule_repository") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(ValueError, match="Rule not found"):
                await self.svc.delete(db=AsyncMock(), rule_id=99)

    async def test_update_preserves_unset_fields(self):
        from unittest.mock import patch

        existing_rule = MagicMock()
        existing_rule.metric = "temperature"
        existing_rule.operator = ">"
        existing_rule.action = "ON"
        existing_rule.room_id = 1

        with patch("app.services.rule_service.rule_repository") as mock_repo:
            with patch("app.services.rule_service.room_repository") as mock_room_repo:
                mock_room = MagicMock()
                mock_room.auto_control_enabled = True
                mock_room_repo.get_by_id = AsyncMock(return_value=mock_room)
                mock_room_repo.update = AsyncMock(return_value=mock_room)
                mock_repo.get_by_id = AsyncMock(return_value=existing_rule)
                mock_repo.update = AsyncMock(return_value=existing_rule)
                mock_repo.has_active_rules_by_room = AsyncMock(return_value=True)

                payload = MagicMock()
                payload.model_dump.return_value = {"threshold_value": 35}  # only update threshold

                result = await self.svc.update(db=AsyncMock(), rule_id=1, payload=payload)
                called_updates = mock_repo.update.call_args[0][2]
                assert called_updates == {"threshold_value": 35}
                assert result is existing_rule

    async def test_update_syncs_room_mode_when_last_active_rule_is_disabled(self):
        from unittest.mock import patch

        existing_rule = MagicMock()
        existing_rule.metric = "temperature"
        existing_rule.operator = ">"
        existing_rule.action = "ON"
        existing_rule.room_id = 1

        with patch("app.services.rule_service.rule_repository") as mock_repo:
            with patch("app.services.rule_service.room_repository") as mock_room_repo:
                mock_room = MagicMock()
                mock_room.auto_control_enabled = True
                mock_repo.get_by_id = AsyncMock(return_value=existing_rule)
                mock_repo.update = AsyncMock(return_value=existing_rule)
                mock_repo.has_active_rules_by_room = AsyncMock(return_value=False)
                mock_room_repo.get_by_id = AsyncMock(return_value=mock_room)
                mock_room_repo.update = AsyncMock(return_value=mock_room)

                payload = MagicMock()
                payload.model_dump.return_value = {"is_active": False}

                await self.svc.update(db=AsyncMock(), rule_id=1, payload=payload)
                mock_room_repo.update.assert_called_once_with(ANY, mock_room, {"auto_control_enabled": False})
