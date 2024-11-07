import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    odk_config_id = fields.Many2one("odk.config", string="ODK Config")
    project = fields.Char(related="odk_config_id.project", string="Project ID", readonly=True)
    odk_app_user = fields.Many2one("odk.app.user", string="ODK App User")
    session = fields.Char(string="Session Token", readonly=True)

    @api.onchange("odk_config_id")
    def _onchange_odk_config_id(self):
        """Fetch ODK users dynamically when the ODK config changes."""
        if self.odk_config_id:
            base_url = self.odk_config_id.base_url
            project_id = self.odk_config_id.project
            username = self.odk_config_id.username
            password = self.odk_config_id.password
            self._login(base_url, username, password)
            if self.session:
                app_users = self._fetch_app_users(base_url, project_id)
                return {
                    "domain": {
                        "odk_app_user": [
                            ("odk_user_id", "in", [user["id"] for user in app_users]),
                            ("project_id", "=", project_id),  # Filter based on project_id
                        ]
                    }
                }
        else:
            return {"domain": {"odk_app_user": []}}

    def _login(self, base_url, username, password):
        """Login to the ODK API and retrieve the session token."""
        login_url = f"{base_url}/v1/sessions"
        headers = {"Content-Type": "application/json"}
        data = json.dumps({"email": username, "password": password})
        response = requests.post(login_url, headers=headers, data=data, timeout=10)
        if response.status_code == 200:
            self.session = response.json().get("token")
        else:
            raise ValidationError(_("Login failed. Check your ODK credentials."))

    def _fetch_app_users(self, base_url, project_id):
        """Fetch app users from ODK and update odk.app.user records specific to a project."""
        url = f"{base_url}/v1/projects/{project_id}/app-users"
        headers = {
            "Authorization": f"Bearer {self.session}",
            "Content-Type": "application/json",
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            app_users_data = response.json()

            # Get current ODK users in Odoo for the specific project
            existing_odk_users = self.env["odk.app.user"].search([("project_id", "=", project_id)])

            # Create a set of ODK user IDs from the fetched data
            fetched_odk_user_ids = {user["id"] for user in app_users_data}

            for user in app_users_data:
                odk_user = self.env["odk.app.user"].search(
                    [
                        ("odk_user_id", "=", user["id"]),
                        ("project_id", "=", project_id),
                    ],
                    limit=1,
                )

                if odk_user:
                    odk_user.write(
                        {
                            "name": user["displayName"],
                            "active": True,
                        }
                    )
                else:
                    self.env["odk.app.user"].create(
                        {
                            "name": user["displayName"],
                            "odk_user_id": user["id"],
                            "project_id": project_id,
                            "active": True,
                        }
                    )

            for odk_user in existing_odk_users:
                if odk_user.odk_user_id not in fetched_odk_user_ids:
                    odk_user.write({"active": False})

            return app_users_data

        else:
            raise UserError(_("Failed to fetch app users from ODK"))
