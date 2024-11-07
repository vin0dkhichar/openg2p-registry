from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase


class TestResPartner(TransactionCase):
    def setUp(self):
        super().setUp()
        self.odk_config = self.env["odk.config"].create(
            {
                "base_url": "http://mocked.url",
                "create_date": fields.Datetime.now(),
                "create_uid": 1,
                "password": "password",
                "project": "test_project",
                "username": "user",
                "name": "Test ODK Config",
                "write_date": fields.Datetime.now(),
                "write_uid": 1,
            }
        )

        self.partner = self.env["res.partner"].create(
            {"name": "Test Partner", "odk_config_id": self.odk_config.id}
        )

    @patch("requests.post")
    def test_login_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"token": "mocked_token"}

        self.partner._login("http://mocked.url", "user", "password")

        self.assertEqual(self.partner.session, "mocked_token")

    @patch("requests.post")
    def test_login_failure(self, mock_post):
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {}

        with self.assertRaises(ValidationError):
            self.partner._login("http://mocked.url", "user", "wrong_password")

    @patch("requests.get")
    def test_fetch_app_users_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {"id": 1, "displayName": "User One"},
            {"id": 2, "displayName": "User Two"},
        ]

        self.env["odk.app.user"].create(
            {"name": "Existing User", "odk_user_id": 1, "project_id": "test_project", "active": False}
        )

        users = self.partner._fetch_app_users("http://mocked.url", "test_project")

        self.assertEqual(len(users), 2)
        self.assertEqual(self.env["odk.app.user"].search([("odk_user_id", "=", 1)]).active, True)
        self.assertEqual(self.env["odk.app.user"].search([("odk_user_id", "=", 2)]).active, True)

    @patch("requests.get")
    def test_fetch_app_users_no_project(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        users = self.partner._fetch_app_users("http://mocked.url", "")

        self.assertEqual(len(users), 0)

    def test_onchange_odk_config_id(self):
        with patch(
            "odoo.addons.g2p_odk_user_mapping.models.res_partner.ResPartner._login"
        ) as mock_login, patch(
            "odoo.addons.g2p_odk_user_mapping.models.res_partner.ResPartner._fetch_app_users"
        ) as mock_fetch:
            mock_login.side_effect = lambda *args, **kwargs: setattr(
                self.partner, "session", "mocked_session_token"
            )
            mock_fetch.return_value = [{"id": 1, "displayName": "User One"}]

            self.partner.odk_config_id = self.odk_config

            result = self.partner._onchange_odk_config_id()

            self.assertIsNotNone(result, "_onchange_odk_config_id should not return None")

            if result:
                self.assertIsInstance(result, dict, "_onchange_odk_config_id should return a dictionary")
                self.assertIn("domain", result, "_onchange_odk_config_id result should contain 'domain' key")
                domain = result.get("domain", {})
                self.assertIn("odk_app_user", domain, "'odk_app_user' not found in domain.")
                self.assertIn(
                    ("odk_user_id", "in", [1]),
                    domain.get("odk_app_user", []),
                    "ODK user filter is incorrect.",
                )

    @patch("requests.get")
    def test_onchange_odk_config_id_no_config(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        self.partner.odk_config_id = False

        domain = self.partner._onchange_odk_config_id()
        self.assertEqual(domain, {"domain": {"odk_app_user": []}})

    def test_fetch_app_users_deactivates_missing_users(self):
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [{"id": 2, "displayName": "New User Name"}]

            existing_odk_user = self.env["odk.app.user"].create(
                {"name": "Old User Name", "odk_user_id": 1, "project_id": "test_project", "active": True}
            )

            self.partner._fetch_app_users("http://mocked.url", "test_project")

            self.assertFalse(existing_odk_user.active)

    def test_fetch_app_users_raises_error_on_failure(self):
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 500
            mock_get.return_value.json.return_value = {}

            with self.assertRaises(UserError):
                self.partner._fetch_app_users("http://mocked.url", "test_project")
