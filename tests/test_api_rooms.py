class TestRoomsAPI:
    async def test_list_rooms_requires_auth(self, client):
        resp = await client.get("/api/v1/rooms")
        assert resp.status_code == 401

    async def test_list_rooms_returns_seeded_rooms_sorted_by_building(self, client, auth_headers):
        resp = await client.get("/api/v1/rooms", headers=auth_headers)
        assert resp.status_code == 200

        rooms = resp.json()
        assert len(rooms) == 8

        names = [room["name"] for room in rooms]
        assert names == [
            "Room A101",
            "Room A102",
            "Room A201",
            "Room B101",
            "Room B102",
            "Room B201",
            "Room E101",
            "Room E201",
        ]

        buildings = [room["building"] for room in rooms]
        assert buildings.count("A") == 3
        assert buildings.count("B") == 3
        assert buildings.count("E") == 2
        assert all("auto_control_enabled" in room for room in rooms)

    async def test_admin_can_update_room_automation_mode(self, client, auth_headers):
        resp = await client.put(
            "/api/v1/rooms/1/automation-mode",
            json={"auto_control_enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["auto_control_enabled"] is False

        rooms_resp = await client.get("/api/v1/rooms", headers=auth_headers)
        rooms = rooms_resp.json()
        updated_room = next(room for room in rooms if room["id"] == 1)
        assert updated_room["auto_control_enabled"] is False

    async def test_room_mode_update_deactivates_room_rules(self, client, auth_headers):
        update_mode = await client.put(
            "/api/v1/rooms/1/automation-mode",
            json={"auto_control_enabled": False},
            headers=auth_headers,
        )
        assert update_mode.status_code == 200

        rules_resp = await client.get("/api/v1/rules/room/1", headers=auth_headers)
        assert rules_resp.status_code == 200
        assert all(rule["is_active"] is False for rule in rules_resp.json())
