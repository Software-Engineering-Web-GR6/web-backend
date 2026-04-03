class TestAuthAPI:
    async def test_login_success(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@example.com", "password": "admin123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "noone@example.com", "password": "admin123"},
        )
        assert resp.status_code == 401

    async def test_protected_endpoint_without_token_returns_401(self, client):
        resp = await client.get("/api/v1/alerts/")
        assert resp.status_code == 401

    async def test_protected_endpoint_with_invalid_token_returns_401(self, client):
        resp = await client.get(
            "/api/v1/alerts/",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    async def test_admin_can_create_user_account(self, client, auth_headers):
        resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Nguyen Van User",
                "email": "user1@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "user1@example.com"
        assert body["role"] == "user"
        assert "id" in body

    async def test_create_user_with_duplicate_email_returns_400(self, client, auth_headers):
        first = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "User One",
                "email": "dup@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "User Two",
                "email": "dup@example.com",
                "password": "user67890",
            },
            headers=auth_headers,
        )
        assert second.status_code == 400
        assert second.json()["detail"] == "Email already exists"

    async def test_non_admin_cannot_create_user_account(self, client, auth_headers):
        create_user_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Regular User",
                "email": "regular@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_user_resp.status_code == 201

        login_user_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "regular@example.com", "password": "user12345"},
        )
        assert login_user_resp.status_code == 200
        user_token = login_user_resp.json()["access_token"]

        forbidden_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Another User",
                "email": "another@example.com",
                "password": "user12345",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert forbidden_resp.status_code == 403

    async def test_admin_can_list_users(self, client, auth_headers):
        create_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "List Target",
                "email": "list-target@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201

        resp = await client.get("/api/v1/auth/users", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert any(item["email"] == "list-target@example.com" for item in body)

    async def test_admin_can_import_users_with_partial_failures(self, client, auth_headers):
        seed_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Existing User",
                "email": "existing@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert seed_resp.status_code == 201

        import_resp = await client.post(
            "/api/v1/auth/users/import",
            json={
                "items": [
                    {
                        "full_name": "Batch User 1",
                        "email": "batch-user-1@example.com",
                        "password": "user12345",
                    },
                    {
                        "full_name": "Existing User",
                        "email": "existing@example.com",
                        "password": "user12345",
                    },
                    {
                        "full_name": "Batch User 2",
                        "email": "batch-user-2@example.com",
                        "password": "user12345",
                    },
                ]
            },
            headers=auth_headers,
        )

        assert import_resp.status_code == 200
        body = import_resp.json()
        assert body["created_count"] == 2
        assert body["failed_count"] == 1
        assert len(body["results"]) == 3
        assert body["results"][0]["row_number"] == 1
        assert body["results"][0]["success"] is True
        assert body["results"][1]["row_number"] == 2
        assert body["results"][1]["success"] is False
        assert body["results"][1]["message"] == "Email already exists"

    async def test_non_admin_cannot_import_users(self, client, auth_headers):
        create_user_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Regular User Import",
                "email": "regular-import@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_user_resp.status_code == 201

        login_user_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "regular-import@example.com", "password": "user12345"},
        )
        assert login_user_resp.status_code == 200
        user_token = login_user_resp.json()["access_token"]

        resp = await client.post(
            "/api/v1/auth/users/import",
            json={
                "items": [
                    {
                        "full_name": "Should Fail",
                        "email": "should-fail@example.com",
                        "password": "user12345",
                    }
                ]
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    async def test_admin_can_import_schedule_with_partial_failures(self, client, auth_headers):
        create_user_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Schedule Import User",
                "email": "schedule-import@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_user_resp.status_code == 201

        resp = await client.post(
            "/api/v1/auth/schedule/import",
            json={
                "items": [
                    {
                        "email": "schedule-import@example.com",
                        "room_name": "Room A101",
                        "day_of_week": 6,
                        "shift_number": 6,
                    },
                    {
                        "email": "missing-user@example.com",
                        "room_name": "Room A101",
                        "day_of_week": 2,
                        "shift_number": 2,
                    },
                    {
                        "email": "schedule-import@example.com",
                        "room_name": "Room Unknown",
                        "day_of_week": 2,
                        "shift_number": 2,
                    },
                    {
                        "email": "schedule-import@example.com",
                        "room_name": "Room A101",
                        "day_of_week": 9,
                        "shift_number": 2,
                    },
                ]
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["created_count"] == 1
        assert body["failed_count"] == 3
        assert len(body["results"]) == 4
        assert body["results"][0]["success"] is True
        assert body["results"][1]["success"] is False
        assert body["results"][1]["message"] == "User not found"
        assert body["results"][2]["success"] is False
        assert body["results"][2]["message"] == "Room not found"
        assert body["results"][3]["success"] is False
        assert body["results"][3]["message"] == "day_of_week must be between 0 and 6"

    async def test_non_admin_cannot_import_schedule(self, client, auth_headers):
        create_user_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Regular User Schedule Import",
                "email": "regular-schedule-import@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_user_resp.status_code == 201

        login_user_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "regular-schedule-import@example.com", "password": "user12345"},
        )
        assert login_user_resp.status_code == 200
        user_token = login_user_resp.json()["access_token"]

        resp = await client.post(
            "/api/v1/auth/schedule/import",
            json={
                "items": [
                    {
                        "email": "regular-schedule-import@example.com",
                        "room_name": "Room A101",
                        "day_of_week": 1,
                        "shift_number": 1,
                    }
                ]
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    async def test_get_me_returns_current_user(self, client, auth_headers):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "admin@example.com"
        assert body["role"] == "admin"

    async def test_current_user_can_change_password(self, client, auth_headers):
        resp = await client.put(
            "/api/v1/auth/me/password",
            json={
                "current_password": "admin123",
                "new_password": "admin12345",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password updated successfully"

        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@example.com", "password": "admin12345"},
        )
        assert login_resp.status_code == 200

    async def test_admin_can_assign_and_list_schedule(self, client, auth_headers):
        create_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Schedule User",
                "email": "schedule-user@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        assign_resp = await client.post(
            f"/api/v1/auth/users/{user_id}/schedule",
            json={"room_id": 1, "shifts": [2], "days_of_week": [0]},
            headers=auth_headers,
        )
        assert assign_resp.status_code == 200
        assigned = assign_resp.json()
        assert len(assigned) == 1
        assert assigned[0]["room_id"] == 1
        assert assigned[0]["shift_number"] == 2

        list_resp = await client.get(
            f"/api/v1/auth/users/{user_id}/schedule",
            headers=auth_headers,
        )
        assert list_resp.status_code == 200
        listed = list_resp.json()
        assert len(listed) == 1
        assert listed[0]["day_of_week"] == 0

    async def test_admin_can_remove_schedule_entry(self, client, auth_headers):
        create_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Schedule Remove User",
                "email": "schedule-remove@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        assign_resp = await client.post(
            f"/api/v1/auth/users/{user_id}/schedule",
            json={"room_id": 1, "shifts": [3], "days_of_week": [1]},
            headers=auth_headers,
        )
        assert assign_resp.status_code == 200

        remove_resp = await client.delete(
            f"/api/v1/auth/users/{user_id}/schedule",
            params={"room_id": 1, "shift_number": 3, "day_of_week": 1},
            headers=auth_headers,
        )
        assert remove_resp.status_code == 200
        assert remove_resp.json()["message"] == "Schedule entry removed successfully"

        list_resp = await client.get(
            f"/api/v1/auth/users/{user_id}/schedule",
            headers=auth_headers,
        )
        assert list_resp.status_code == 200
        assert list_resp.json() == []

    async def test_change_password_rejects_wrong_current_password(self, client, auth_headers):
        resp = await client.put(
            "/api/v1/auth/me/password",
            json={
                "current_password": "wrong-password",
                "new_password": "admin12345",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Current password is incorrect"

    async def test_non_admin_cannot_list_users(self, client, auth_headers):
        create_user_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Regular User List",
                "email": "regular-list@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_user_resp.status_code == 201

        login_user_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "regular-list@example.com", "password": "user12345"},
        )
        assert login_user_resp.status_code == 200
        user_token = login_user_resp.json()["access_token"]

        resp = await client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    async def test_admin_can_delete_user(self, client, auth_headers):
        create_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Delete Target",
                "email": "delete-target@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/api/v1/auth/users/{user_id}", headers=auth_headers)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["message"] == "User deleted successfully"

        list_resp = await client.get("/api/v1/auth/users", headers=auth_headers)
        assert list_resp.status_code == 200
        assert all(item["id"] != user_id for item in list_resp.json())

    async def test_admin_can_delete_user_with_schedule(self, client, auth_headers):
        create_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Delete With Schedule",
                "email": "delete-with-schedule@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        assign_resp = await client.post(
            f"/api/v1/auth/users/{user_id}/schedule",
            json={"room_id": 1, "shifts": [2], "days_of_week": [0]},
            headers=auth_headers,
        )
        assert assign_resp.status_code == 200

        delete_resp = await client.delete(f"/api/v1/auth/users/{user_id}", headers=auth_headers)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["message"] == "User deleted successfully"

    async def test_delete_non_existing_user_returns_404(self, client, auth_headers):
        resp = await client.delete("/api/v1/auth/users/999999", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    async def test_non_admin_cannot_delete_user(self, client, auth_headers):
        create_user_resp = await client.post(
            "/api/v1/auth/users",
            json={
                "full_name": "Regular User Delete",
                "email": "regular-delete@example.com",
                "password": "user12345",
            },
            headers=auth_headers,
        )
        assert create_user_resp.status_code == 201
        target_id = create_user_resp.json()["id"]

        login_user_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "regular-delete@example.com", "password": "user12345"},
        )
        assert login_user_resp.status_code == 200
        user_token = login_user_resp.json()["access_token"]

        resp = await client.delete(
            f"/api/v1/auth/users/{target_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    async def test_forgot_password_returns_generic_message_for_unknown_email(self, client):
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "unknown@example.com"},
        )
        assert resp.status_code == 200
        assert "If the account exists" in resp.json()["message"]

    async def test_forgot_password_and_reset_password_success(self, client, monkeypatch):
        from app.services.auth_service import auth_service
        from app.services.mail_service import mail_service

        sent_payload = {}

        async def fake_send_password_reset_code(to_email: str, code: str, expires_minutes: int):
            sent_payload["email"] = to_email
            sent_payload["code"] = code
            sent_payload["expires_minutes"] = expires_minutes

        monkeypatch.setattr(auth_service, "_generate_reset_code", lambda: "123456")
        monkeypatch.setattr(mail_service, "send_password_reset_code", fake_send_password_reset_code)

        forgot_resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "admin@example.com"},
        )
        assert forgot_resp.status_code == 200
        assert sent_payload["email"] == "admin@example.com"
        assert sent_payload["code"] == "123456"

        verify_resp = await client.post(
            "/api/v1/auth/verify-reset-code",
            json={"email": "admin@example.com", "code": "123456"},
        )
        assert verify_resp.status_code == 200

        reset_resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"email": "admin@example.com", "code": "123456", "new_password": "admin12345"},
        )
        assert reset_resp.status_code == 200
        assert reset_resp.json()["message"] == "Password updated successfully"

        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@example.com", "password": "admin12345"},
        )
        assert login_resp.status_code == 200

    async def test_verify_reset_code_rejects_invalid_code(self, client, monkeypatch):
        from app.services.auth_service import auth_service
        from app.services.mail_service import mail_service

        async def fake_send_password_reset_code(to_email: str, code: str, expires_minutes: int):
            return None

        monkeypatch.setattr(auth_service, "_generate_reset_code", lambda: "123456")
        monkeypatch.setattr(mail_service, "send_password_reset_code", fake_send_password_reset_code)

        forgot_resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "admin@example.com"},
        )
        assert forgot_resp.status_code == 200

        verify_resp = await client.post(
            "/api/v1/auth/verify-reset-code",
            json={"email": "admin@example.com", "code": "000000"},
        )
        assert verify_resp.status_code == 400
        assert verify_resp.json()["detail"] == "Invalid or expired verification code"

    async def test_reset_password_rejects_used_code(self, client, monkeypatch):
        from app.services.auth_service import auth_service
        from app.services.mail_service import mail_service

        async def fake_send_password_reset_code(to_email: str, code: str, expires_minutes: int):
            return None

        monkeypatch.setattr(auth_service, "_generate_reset_code", lambda: "654321")
        monkeypatch.setattr(mail_service, "send_password_reset_code", fake_send_password_reset_code)

        forgot_resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "admin@example.com"},
        )
        assert forgot_resp.status_code == 200

        first_reset = await client.post(
            "/api/v1/auth/reset-password",
            json={"email": "admin@example.com", "code": "654321", "new_password": "admin12345"},
        )
        assert first_reset.status_code == 200

        second_reset = await client.post(
            "/api/v1/auth/reset-password",
            json={"email": "admin@example.com", "code": "654321", "new_password": "admin67890"},
        )
        assert second_reset.status_code == 400
        assert second_reset.json()["detail"] == "Invalid or expired verification code"
