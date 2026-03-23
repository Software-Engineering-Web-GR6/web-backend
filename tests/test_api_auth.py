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
