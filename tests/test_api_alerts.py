class TestAlertsAPI:
    async def test_list_alerts_requires_auth(self, client):
        resp = await client.get("/api/v1/alerts/")
        assert resp.status_code == 401

    async def test_list_alerts_empty(self, client, auth_headers):
        resp = await client.get("/api/v1/alerts/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_alert_created_after_threshold_exceeded(self, client, auth_headers):
        await client.post(
            "/api/v1/sensors/ingest",
            json={"room_id": 1, "temperature": 35},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/alerts/", headers=auth_headers)
        alerts = resp.json()
        assert len(alerts) >= 1
        assert alerts[0]["status"] == "OPEN"

    async def test_resolve_alert(self, client, auth_headers):
        await client.post(
            "/api/v1/sensors/ingest",
            json={"room_id": 1, "temperature": 35},
            headers=auth_headers,
        )
        alerts = (await client.get("/api/v1/alerts/", headers=auth_headers)).json()
        alert_id = alerts[0]["id"]

        resp = await client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "RESOLVED"

    async def test_resolve_nonexistent_alert(self, client, auth_headers):
        resp = await client.post("/api/v1/alerts/99999/resolve", headers=auth_headers)
        assert resp.status_code == 404

    async def test_new_alert_created_after_resolve(self, client, auth_headers):
        payload = {"room_id": 1, "temperature": 35}
        await client.post("/api/v1/sensors/ingest", json=payload, headers=auth_headers)

        alerts = (await client.get("/api/v1/alerts/", headers=auth_headers)).json()
        alert_id = alerts[0]["id"]
        await client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=auth_headers)

        # sau khi resolve, gửi lại reading vượt ngưỡng → tạo alert mới
        await client.post("/api/v1/sensors/ingest", json=payload, headers=auth_headers)
        alerts2 = (await client.get("/api/v1/alerts/", headers=auth_headers)).json()
        open_alerts = [a for a in alerts2 if a["status"] == "OPEN"]
        assert len(open_alerts) == 1


class TestDashboardAPI:
    async def test_dashboard_requires_auth(self, client):
        resp = await client.get("/api/v1/dashboard/1")
        assert resp.status_code == 401

    async def test_dashboard_returns_expected_keys(self, client, auth_headers):
        resp = await client.get("/api/v1/dashboard/1", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        for key in ["room_id", "latest", "history", "averages", "devices", "unresolved_alerts"]:
            assert key in body

    async def test_dashboard_includes_devices(self, client, auth_headers):
        resp = await client.get("/api/v1/dashboard/1", headers=auth_headers)
        body = resp.json()
        assert len(body["devices"]) == 3  # fan, ac, window từ seed


class TestDevicesAPI:
    async def test_control_device_requires_auth(self, client):
        resp = await client.post("/api/v1/devices/1/control", json={"action": "ON"})
        assert resp.status_code == 401

    async def test_list_devices_in_room(self, client, auth_headers):
        resp = await client.get("/api/v1/devices/1", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    async def test_control_device(self, client, auth_headers):
        devices = (await client.get("/api/v1/devices/1", headers=auth_headers)).json()
        fan = next(d for d in devices if d["device_type"] == "fan")

        resp = await client.post(
            f"/api/v1/devices/{fan['id']}/control",
            json={"action": "ON"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "ON"

    async def test_control_invalid_action(self, client, auth_headers):
        devices = (await client.get("/api/v1/devices/1", headers=auth_headers)).json()
        fan_id = devices[0]["id"]
        resp = await client.post(
            f"/api/v1/devices/{fan_id}/control",
            json={"action": "INVALID"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
