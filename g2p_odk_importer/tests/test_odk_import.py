from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestOdkImport(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.odk_config = self.env["odk.config"].create(
            {
                "name": "Test ODK Config",
                "base_url": "http://example.com",
                "username": "test_user",
                "password": "test_password",
                "project": 1,
                "form_id": "test_form_id",
            }
        )

        self.odk_import = self.env["odk.import"].create(
            {
                "odk_config": self.odk_config.id,
                "json_formatter": "{ name: .name, age: .age }",
                "target_registry": "individual",
                "last_sync_time": datetime.now() - timedelta(days=1),
                "job_status": "draft",
                "interval_hours": 1,
            }
        )
        self.env["ir.config_parameter"].set_param("g2p_odk_importer.enable_odk", True)

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.login")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.import_record_by_instance_id")
    def test_fetch_record_by_instance_id(self, mock_import_record, mock_login):
        # Test fetch record by instance ID method
        mock_login.return_value = None
        mock_import_record.return_value = {"form_updated": True}

        self.odk_import.instance_id = "test_instance_id"
        result = self.odk_import.fetch_record_by_instance_id()
        self.assertEqual(result["params"]["type"], "success")

        self.odk_import.instance_id = False
        with self.assertRaises(UserError):
            self.odk_import.fetch_record_by_instance_id()

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.login")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.test_connection")
    def test_test_connection(self, mock_test_connection, mock_login):
        # Test connection method
        mock_login.return_value = None
        mock_test_connection.return_value = True

        result = self.odk_import.test_connection()
        self.assertEqual(result["params"]["message"], "Tested successfully.")

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.login")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.import_record_by_instance_id")
    def test_process_instance_id(self, mock_import_record, mock_login):
        # Test processing instance ID method
        mock_login.return_value = None
        mock_import_record.return_value = {"form_updated": True}

        instance_id = self.env["odk.instance.id"].create(
            {
                "instance_id": "test_instance_id",
                "odk_import_id": self.odk_import.id,
                "status": "pending",
            }
        )
        self.odk_import._process_instance_id([instance_id])
        self.assertEqual(instance_id.status, "processing")

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.get_submissions")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.login")
    def test_import_records_with_async(self, mock_login, mock_get_submissions):
        # Test importing records with async enabled
        mock_login.return_value = None
        mock_get_submissions.return_value = [{"__id": "test_instance_id"}]

        self.env["ir.config_parameter"].sudo().set_param("g2p_odk_importer.enable_odk_async", True)
        self.odk_import.import_records()

        pending_instance = self.env["odk.instance.id"].search([("instance_id", "=", "test_instance_id")])
        self.assertTrue(pending_instance)
        self.assertEqual(pending_instance.status, "pending")

    def test_odk_import_action_trigger(self):
        # Test ODK import action trigger method
        self.odk_import.odk_import_action_trigger()
        self.assertEqual(self.odk_import.job_status, "running")
        self.assertTrue(self.odk_import.cron_id)

        self.odk_import.odk_import_action_trigger()
        self.assertEqual(self.odk_import.job_status, "completed")
        self.assertFalse(self.odk_import.cron_id)

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.login")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.import_delta_records")
    def test_import_delta_records(self, mock_import_delta, mock_login):
        mock_login.return_value = None

        # Case 1: Successful import
        mock_import_delta.return_value = {"form_updated": True, "partner_count": 5}
        result = self.odk_import.import_records()
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("5 records were imported successfully.", result["params"]["message"])

        # Case 2: Import failed
        mock_import_delta.return_value = {"form_failed": True}
        result = self.odk_import.import_records()
        self.assertEqual(result["params"]["type"], "danger")
        self.assertIn("ODK form import failed", result["params"]["message"])

        # Case 3: No new records
        mock_import_delta.return_value = {}
        result = self.odk_import.import_records()
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("No new form records were submitted.", result["params"]["message"])

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.login")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.import_record_by_instance_id")
    def test_odk_setting_disabled(self, mock_import_record, mock_login):
        # Test when ODK setting is disabled
        self.env["ir.config_parameter"].set_param("g2p_odk_importer.enable_odk", False)
        with self.assertRaises(UserError):
            self.odk_import.fetch_record_by_instance_id()

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.login")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.import_record_by_instance_id")
    def test_import_failed(self, mock_import_record, mock_login):
        # Test when import fails
        mock_login.return_value = None
        mock_import_record.return_value = {"form_failed": True}

        self.odk_import.instance_id = "test_instance_id"
        result = self.odk_import.fetch_record_by_instance_id()
        self.assertEqual(result["params"]["type"], "danger")
        self.assertIn("ODK form import failed", result["params"]["message"])

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.login")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.import_record_by_instance_id")
    def test_no_record_found(self, mock_import_record, mock_login):
        # Test when no record is found for the given instance ID
        mock_login.return_value = None
        mock_import_record.return_value = {}

        self.odk_import.instance_id = "test_instance_id"
        result = self.odk_import.fetch_record_by_instance_id()
        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("No record found using this instance ID.", result["params"]["message"])

    def test_compute_config_param_value(self):
        # Set the parameter and test
        self.env["ir.config_parameter"].sudo().set_param("g2p_odk_importer.enable_odk", "True")
        self.odk_import._compute_config_param_value()
        self.assertEqual(self.odk_import.enable_import_instance, "True")

    def test_constraint_json_fields_invalid(self):
        # Test case: Invalid JSON formatter raises ValidationError
        with self.assertRaises(ValidationError):
            self.odk_import.json_formatter = "{ invalid_json: .value "  # Missing closing brace

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.import_record_by_instance_id")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.login")
    @patch("odoo.addons.g2p_odk_importer.models.odk_import._logger.error")
    def test_process_instance_id_exception(self, mock_logger_error, mock_login, mock_import_record):
        # Setup mock behaviors
        mock_login.return_value = None
        mock_import_record.side_effect = Exception("Test Exception")

        # Create a test instance_id
        instance_id = self.env["odk.instance.id"].create(
            {
                "instance_id": "test_instance_id",
                "odk_import_id": self.odk_import.id,
                "status": "pending",
            }
        )

        # Process the instance_id and handle the exception
        self.odk_import._process_instance_id([instance_id])

        # Re-fetch the instance_id to check its updated status
        updated_instance_id = self.env["odk.instance.id"].browse(instance_id.id)

        # Check that the status was updated to "failed"
        self.assertEqual(updated_instance_id.status, "failed")

        # Verify logger was called with the exception details
        self.assertTrue(mock_logger_error.called)
        self.assertIn("Failed to import instance ID test_instance_id", mock_logger_error.call_args[0][0])
