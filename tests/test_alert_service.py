import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.alert_service import AlertService


class TestAlertService:
    def setup_method(self):
        self.svc = AlertService()

    async def test_create_alert_broadcasts_websocket(self):
        alert_mock = MagicMock()
        alert_mock.id = 1
        alert_mock.room_id = 1
        alert_mock.level = "HIGH"
        alert_mock.message = "CO2 cao"
        alert_mock.status = "OPEN"

        with patch("app.services.alert_service.alert_repository") as mock_repo, \
             patch("app.services.alert_service.ws_manager") as mock_ws:
            mock_repo.create_alert = AsyncMock(return_value=alert_mock)
            mock_ws.broadcast_json = AsyncMock()

            result = await self.svc.create(db=AsyncMock(), room_id=1, level="HIGH", message="CO2 cao")

            mock_repo.create_alert.assert_called_once()
            call_args = mock_repo.create_alert.call_args[0]
            assert call_args[1] == 1       # room_id
            assert call_args[2] == "HIGH"  # level
            assert call_args[3] == "CO2 cao"  # message
            mock_ws.broadcast_json.assert_called_once()
            broadcast_payload = mock_ws.broadcast_json.call_args[0][0]
            assert broadcast_payload["event"] == "new_alert"
            assert broadcast_payload["alert"]["id"] == 1
            assert result == alert_mock

    async def test_resolve_alert_broadcasts_websocket(self):
        alert_mock = MagicMock()
        alert_mock.id = 5
        alert_mock.status = "RESOLVED"

        with patch("app.services.alert_service.alert_repository") as mock_repo, \
             patch("app.services.alert_service.ws_manager") as mock_ws:
            mock_repo.get_by_id = AsyncMock(return_value=alert_mock)
            mock_repo.resolve = AsyncMock(return_value=alert_mock)
            mock_ws.broadcast_json = AsyncMock()

            result = await self.svc.resolve(db=AsyncMock(), alert_id=5)

            mock_ws.broadcast_json.assert_called_once()
            broadcast_payload = mock_ws.broadcast_json.call_args[0][0]
            assert broadcast_payload["event"] == "resolved_alert"
            assert broadcast_payload["alert"]["status"] == "RESOLVED"
            assert result == alert_mock

    async def test_resolve_nonexistent_alert_raises(self):
        with patch("app.services.alert_service.alert_repository") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=None)
            with pytest.raises(ValueError, match="Alert not found"):
                await self.svc.resolve(db=AsyncMock(), alert_id=999)

    async def test_get_open_alert_delegates_to_repo(self):
        existing = MagicMock()
        with patch("app.services.alert_service.alert_repository") as mock_repo:
            mock_repo.get_open_by_room_and_message = AsyncMock(return_value=existing)
            result = await self.svc.get_open_alert(
                db=AsyncMock(), room_id=1, level="HIGH", message="CO2 cao"
            )
            mock_repo.get_open_by_room_and_message.assert_called_once()
            assert result == existing
