from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase


class TestResPartner(TransactionCase):
    def setUp(self):
        super().setUp()
        self.odk_config = self.env["odk.config"].create(
            {
                "base_url": "http://test.odk.com",
                "project": "test_project",
                "username": "testuser",
                "password": "testpassword",
                "name": "Test ODK Config",
                "create_date": fields.Datetime.now(),
                "create_uid": 1,
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
        mock_post.return_value.json.return_value = {"token": "test_session_token"}

        self.partner._login("http://test.odk.com", self.odk_config.username, self.odk_config.password)

        self.assertEqual(self.partner.session, "test_session_token")

    @patch("requests.post")
    def test_login_failure(self, mock_post):
        mock_post.side_effect = Exception("Login failed")

        with self.assertRaises(ValidationError) as e:
            self.partner._login("http://test.odk.com", self.odk_config.username, "wrong_password")

        self.assertEqual(str(e.exception), "Login failed: Login failed")

    @patch("requests.get")
    def test_fetch_app_users_failure(self, mock_get):
        mock_get.return_value.status_code = 500

        self.partner.session = "test_session_token"

        with self.assertRaises(UserError):
            self.partner._fetch_app_users("http://test.odk.com", self.odk_config.project)

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
                    ("id", "in", [1]),
                    domain.get("odk_app_user", []),
                    "ODK user filter is incorrect.",
                )

    def test_onchange_odk_config_id_no_config(self):
        partner = self.env["res.partner"].new({"odk_config_id": False})

        result = partner._onchange_odk_config_id()

        self.assertEqual(result, {"domain": {"odk_app_user": []}})
