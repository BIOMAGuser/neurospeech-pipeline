"""User management and role-based access control tests."""
import time

import requests
from helpers import auth_headers, ADMIN_USER


class TestUserCRUD:
    """Admin-only user CRUD endpoints."""

    def test_list_users_admin(self, base_url, admin_token):
        resp = requests.get(f"{base_url}/users", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        users = resp.json()
        assert isinstance(users, list)
        assert len(users) >= 2
        usernames = [u["username"] for u in users]
        assert ADMIN_USER in usernames
        assert "arzt" in usernames
        # Verify fields
        admin = next(u for u in users if u["username"] == ADMIN_USER)
        assert admin["is_admin"] is True
        assert "id" in admin
        assert "is_active" in admin
        assert "created_at" in admin

    def test_list_users_forbidden_for_non_admin(self, base_url, standard_token):
        resp = requests.get(f"{base_url}/users", headers=auth_headers(standard_token))
        assert resp.status_code == 403

    def test_list_users_requires_auth(self, base_url):
        resp = requests.get(f"{base_url}/users")
        assert resp.status_code == 401

    def test_create_user(self, base_url, admin_token):
        unique = f"testuser_{int(time.time())}"
        resp = requests.post(
            f"{base_url}/users",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"username": unique, "password": "pass1234", "is_admin": False},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == unique
        assert data["is_admin"] is False
        assert data["is_active"] is True

        # Clean up
        requests.delete(
            f"{base_url}/users/{data['id']}",
            headers=auth_headers(admin_token),
        )

    def test_create_user_forbidden_for_non_admin(self, base_url, standard_token):
        resp = requests.post(
            f"{base_url}/users",
            headers={**auth_headers(standard_token), "Content-Type": "application/json"},
            json={"username": "hacker", "password": "nope1234"},
        )
        assert resp.status_code == 403

    def test_create_duplicate_username(self, base_url, admin_token):
        resp = requests.post(
            f"{base_url}/users",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"username": "arzt", "password": "doesntmatter1"},
        )
        assert resp.status_code == 409

    def test_update_user_password(self, base_url, admin_token):
        # Create a user
        unique = f"updpw_{int(time.time())}"
        create_resp = requests.post(
            f"{base_url}/users",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"username": unique, "password": "old_pass1234"},
        )
        user_id = create_resp.json()["id"]

        # Update password
        resp = requests.put(
            f"{base_url}/users/{user_id}",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"password": "new_pass1234"},
        )
        assert resp.status_code == 200

        # Login with new password
        login = requests.post(
            f"{base_url}/token",
            data={"username": unique, "password": "new_pass1234"},
        )
        assert login.status_code == 200

        # Old password should fail
        login_old = requests.post(
            f"{base_url}/token",
            data={"username": unique, "password": "old_pass1234"},
        )
        assert login_old.status_code == 401

        # Clean up
        requests.delete(
            f"{base_url}/users/{user_id}",
            headers=auth_headers(admin_token),
        )

    def test_update_user_role(self, base_url, admin_token):
        unique = f"role_{int(time.time())}"
        create_resp = requests.post(
            f"{base_url}/users",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"username": unique, "password": "pass1234", "is_admin": False},
        )
        user_id = create_resp.json()["id"]

        # Promote to admin
        resp = requests.put(
            f"{base_url}/users/{user_id}",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"is_admin": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is True

        # Demote back
        resp = requests.put(
            f"{base_url}/users/{user_id}",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"is_admin": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is False

        # Clean up
        requests.delete(
            f"{base_url}/users/{user_id}",
            headers=auth_headers(admin_token),
        )

    def test_deactivate_user(self, base_url, admin_token):
        unique = f"deact_{int(time.time())}"
        create_resp = requests.post(
            f"{base_url}/users",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"username": unique, "password": "pass1234"},
        )
        user_id = create_resp.json()["id"]

        # Deactivate
        resp = requests.put(
            f"{base_url}/users/{user_id}",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        # Deactivated user cannot login
        login = requests.post(
            f"{base_url}/token",
            data={"username": unique, "password": "pass1234"},
        )
        assert login.status_code == 401

        # Clean up
        requests.delete(
            f"{base_url}/users/{user_id}",
            headers=auth_headers(admin_token),
        )

    def test_delete_user(self, base_url, admin_token):
        unique = f"del_{int(time.time())}"
        create_resp = requests.post(
            f"{base_url}/users",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"username": unique, "password": "pass1234"},
        )
        user_id = create_resp.json()["id"]

        resp = requests.delete(
            f"{base_url}/users/{user_id}",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify deleted
        login = requests.post(
            f"{base_url}/token",
            data={"username": unique, "password": "pass1234"},
        )
        assert login.status_code == 401

    def test_delete_self_forbidden(self, base_url, admin_token):
        # Get admin user id
        users = requests.get(
            f"{base_url}/users", headers=auth_headers(admin_token)
        ).json()
        admin_id = next(u["id"] for u in users if u["username"] == ADMIN_USER)

        resp = requests.delete(
            f"{base_url}/users/{admin_id}",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 422

    def test_demote_self_forbidden(self, base_url, admin_token):
        """Admin cannot remove their own admin rights."""
        users = requests.get(
            f"{base_url}/users", headers=auth_headers(admin_token)
        ).json()
        admin_id = next(u["id"] for u in users if u["username"] == ADMIN_USER)

        resp = requests.put(
            f"{base_url}/users/{admin_id}",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"is_admin": False},
        )
        assert resp.status_code == 422

    def test_deactivate_self_forbidden(self, base_url, admin_token):
        """Admin cannot deactivate their own account."""
        users = requests.get(
            f"{base_url}/users", headers=auth_headers(admin_token)
        ).json()
        admin_id = next(u["id"] for u in users if u["username"] == ADMIN_USER)

        resp = requests.put(
            f"{base_url}/users/{admin_id}",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"is_active": False},
        )
        assert resp.status_code == 422

    def test_change_own_password_allowed(self, base_url, admin_token):
        """Admin CAN change their own password (that's fine)."""
        users = requests.get(
            f"{base_url}/users", headers=auth_headers(admin_token)
        ).json()
        admin_id = next(u["id"] for u in users if u["username"] == ADMIN_USER)

        # Change password then change it back
        resp = requests.put(
            f"{base_url}/users/{admin_id}",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"password": "testpassword"},
        )
        assert resp.status_code == 200

    def test_delete_nonexistent_user(self, base_url, admin_token):
        resp = requests.delete(
            f"{base_url}/users/99999",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 404

    def test_update_nonexistent_user(self, base_url, admin_token):
        resp = requests.put(
            f"{base_url}/users/99999",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"is_admin": True},
        )
        assert resp.status_code == 404


class TestUserMeAdmin:
    """Verify /user/me includes is_admin field."""

    def test_admin_user_me_has_is_admin(self, base_url, admin_token):
        resp = requests.get(f"{base_url}/user/me", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_admin"] is True

    def test_standard_user_me_has_is_admin(self, base_url, standard_token):
        resp = requests.get(f"{base_url}/user/me", headers=auth_headers(standard_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_admin"] is False


class TestAdminTokenClaims:
    """Verify JWT token includes is_admin claim."""

    def test_admin_token_has_admin_claim(self, base_url):
        import json
        import base64

        resp = requests.post(
            f"{base_url}/token",
            data={"username": ADMIN_USER, "password": "testpassword"},
        )
        token = resp.json()["access_token"]
        # Decode JWT payload (no verification needed for testing claims)
        payload = token.split(".")[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        assert claims["is_admin"] is True

    def test_standard_token_has_no_admin_claim(self, base_url):
        import json
        import base64

        resp = requests.post(
            f"{base_url}/token",
            data={"username": "arzt", "password": "arzt1234"},
        )
        token = resp.json()["access_token"]
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        assert claims.get("is_admin") is False
