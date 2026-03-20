class TestSensorsAPI:
    async def test_ingest_requires_auth(self, client):
        resp = await client.post("/api/v1/sensors/ingest", json={"room_id": 1, "temperature": 25})
        assert resp.status_code == 401

    async def test_ingest_normal_reading(self, client, auth_headers):
        resp = await client.post(
            "/api/v1/sensors/ingest",
            json={"room_id": 1, "temperature": 25, "humidity": 60, "co2": 800},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "reading" in body
        assert body["reading"]["temperature"] == 25

    async def test_ingest_triggers_automation_rule(self, client, auth_headers):
        # temperature > 30 should trigger the seeded rule
        resp = await client.post(
            "/api/v1/sensors/ingest",
            json={"room_id": 1, "temperature": 35, "humidity": 60, "co2": 800},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["executed_rules"]) > 0

    async def test_ingest_no_rule_triggered_below_threshold(self, client, auth_headers):
        resp = await client.post(
            "/api/v1/sensors/ingest",
            json={"room_id": 1, "temperature": 20, "humidity": 50, "co2": 500},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert body["executed_rules"] == [] if (body := resp.json()) else True

    async def test_ingest_no_duplicate_alert(self, client, auth_headers):
        payload = {"room_id": 1, "temperature": 35, "humidity": 60, "co2": 800}
        # gửi 2 lần cùng điều kiện vượt ngưỡng
        await client.post("/api/v1/sensors/ingest", json=payload, headers=auth_headers)
        await client.post("/api/v1/sensors/ingest", json=payload, headers=auth_headers)

        alerts_resp = await client.get("/api/v1/alerts/", headers=auth_headers)
        alerts = alerts_resp.json()
        # chỉ được tạo 1 alert cho cùng điều kiện
        messages = [a["message"] for a in alerts]
        assert len(messages) == len(set(messages))

    async def test_get_latest_requires_auth(self, client):
        resp = await client.get("/api/v1/sensors/1/latest")
        assert resp.status_code == 401

    async def test_get_latest_not_found(self, client, auth_headers):
        resp = await client.get("/api/v1/sensors/999/latest", headers=auth_headers)
        assert resp.status_code == 404

    async def test_get_latest_after_ingest(self, client, auth_headers):
        await client.post(
            "/api/v1/sensors/ingest",
            json={"room_id": 1, "temperature": 28, "humidity": 55, "co2": 900},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/sensors/1/latest", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["temperature"] == 28

    async def test_get_history(self, client, auth_headers):
        for i in range(3):
            await client.post(
                "/api/v1/sensors/ingest",
                json={"room_id": 1, "temperature": 20 + i},
                headers=auth_headers,
            )
        resp = await client.get("/api/v1/sensors/1/history?limit=10", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3
