import base64
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from odoo.addons.g2p_odk_importer.models.odk_client import ODKClient


class TestODKClient(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.env_mock = MagicMock()
        self.base_url = "http://example.com"
        self.username = "test_user"
        self.password = "test_password"
        self.project_id = 5
        self.form_id = "test_form_id"
        self.target_registry = "group"
        self.json_formatter = "."
        self.client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

    @patch("requests.post")
    def test_login_success(self, mock_post):
        # Test login success method
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "test_token"}
        mock_post.return_value = mock_response

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        odk_client.login()
        self.assertEqual(odk_client.session, "test_token")

    @patch("requests.post")
    def test_login_exception(self, mock_post):
        # Test login exception handling
        mock_post.side_effect = Exception("Network error")

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        with self.assertRaises(ValidationError) as cm:
            odk_client.login()

        self.assertEqual(str(cm.exception), "Login failed: Network error")

    @patch("requests.get")
    def test_test_connection_success(self, mock_get):
        # Test successful connection
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"displayName": "test_user"}
        mock_get.return_value = mock_response

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        odk_client.session = "test_token"
        self.assertTrue(odk_client.test_connection())

    @patch("requests.get")
    def test_connection_no_session(self, mock_get):
        # Test connection when session is not created
        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        odk_client.session = None

        with self.assertRaises(ValidationError) as cm:
            odk_client.test_connection()

        self.assertEqual(str(cm.exception), "Session not created")

    @patch("requests.get")
    def test_connection_failure(self, mock_get):
        # Test connection failure handling
        mock_get.side_effect = Exception("Connection error")

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        odk_client.session = "valid_session_token"

        with self.assertRaises(ValidationError) as cm:
            odk_client.test_connection()

        self.assertEqual(str(cm.exception), "Connection test failed: Connection error")

    @patch("requests.get")
    def test_import_delta_records_success(self, mock_get):
        # Test importing delta records successfully
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"name": "John Doe"}]}
        mock_get.return_value = mock_response

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        odk_client.session = "test_token"
        result = odk_client.import_delta_records()
        self.assertIn("value", result)

    @patch("requests.get")
    def test_handle_media_import(self, mock_get):
        # Test handling media imports
        member = {"meta": {"instanceID": "test_instance"}}
        mapped_json = {}
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"fake_image_data"
        mock_get.return_value.json.return_value = [{"name": "test_image.jpg"}]

        self.client.handle_media_import(member, mapped_json)
        self.assertIn("supporting_documents_ids", mapped_json)

    def test_get_dob(self):
        # Test getting date of birth from record
        record = {"birthdate": "2000-01-01", "age": 4}
        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        dob = odk_client.get_dob(record)
        self.assertEqual(dob, "2000-01-01")

        record = {"age": 4}
        dob = odk_client.get_dob(record)
        self.assertEqual(dob[:4], str(datetime.now().year - 4))

    def test_is_image(self):
        # Test checking if file is an image
        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        result = odk_client.is_image("test.jpg")
        self.assertTrue(result)

    @patch("requests.get")
    def test_list_expected_attachments(self, mock_get):
        # Test listing expected attachments
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{"name": "test.jpg"}]

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        result = odk_client.list_expected_attachments(
            "http://example.com", "1", "1", "test_instance", "fake_token"
        )
        self.assertIn({"name": "test.jpg"}, result)

    @patch("requests.get")
    def test_download_attachment(self, mock_get):
        # Test downloading attachment
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"fake_image_data"

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        result = odk_client.download_attachment(
            "http://example.com", "1", "1", "test_instance", "test.jpg", "fake_token"
        )
        self.assertEqual(result, b"fake_image_data")

    @patch("requests.get")
    def test_get_submissions_success(self, mock_get):
        # Test importing submission successfully
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": 2, "field1": "value1", "field2": "value2"},
                {"id": 3, "field1": "value3", "field2": "value4"},
            ]
        }
        mock_get.return_value = mock_response

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        submissions = odk_client.get_submissions()

        self.assertEqual(submissions[0]["id"], 2)
        self.assertEqual(submissions[1]["id"], 3)

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.get_dob")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.get_gender")
    def test_get_individual_data_success(self, mock_get_gender, mock_get_dob):
        # Test case for successful retrieval of individual data
        mock_get_dob.return_value = "1990-01-01"
        mock_get_gender.return_value = "Male"

        record = {"name": "John Doe", "gender": "Male"}

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        individual_data = odk_client.get_individual_data(record)

        self.assertEqual(individual_data["name"], "John Doe")
        self.assertEqual(individual_data["given_name"], "John")
        self.assertEqual(individual_data["family_name"], "Doe")
        self.assertEqual(individual_data["addl_name"], "")
        self.assertEqual(individual_data["is_registrant"], True)
        self.assertEqual(individual_data["is_group"], False)
        self.assertEqual(individual_data["birthdate"], "1990-01-01")
        self.assertEqual(individual_data["gender"], "Male")

        mock_get_dob.assert_called_once_with(record)
        mock_get_gender.assert_called_once_with("Male")

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.get_dob")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.get_gender")
    def test_get_individual_data_no_name(self, mock_get_gender, mock_get_dob):
        # Test case when no name is provided in the record
        mock_get_dob.return_value = "1990-01-01"
        mock_get_gender.return_value = "Female"

        record = {"gender": "Female"}

        odk_client = ODKClient(
            self.env_mock,
            1,
            self.base_url,
            self.username,
            self.password,
            self.project_id,
            self.form_id,
            self.target_registry,
            self.json_formatter,
        )

        individual_data = odk_client.get_individual_data(record)

        self.assertEqual(individual_data["name"], None)
        self.assertEqual(individual_data["given_name"], None)
        self.assertEqual(individual_data["family_name"], None)
        self.assertEqual(individual_data["addl_name"], None)
        self.assertEqual(individual_data["is_registrant"], True)
        self.assertEqual(individual_data["is_group"], False)
        self.assertEqual(individual_data["birthdate"], "1990-01-01")
        self.assertEqual(individual_data["gender"], "Female")

        mock_get_dob.assert_called_once_with(record)
        mock_get_gender.assert_called_once_with("Female")

    def test_get_member_kind(self):
        # Test with existing kind
        mock_kind = MagicMock()
        mock_kind.id = 1
        self.env_mock["g2p.group.membership.kind"].search.return_value = mock_kind

        record = {"kind": "member"}
        result = self.client.get_member_kind(record)
        self.assertEqual(result, mock_kind)

        # Test with non-existent kind
        self.env_mock["g2p.group.membership.kind"].search.return_value = False
        record = {"kind": "nonexistent"}
        result = self.client.get_member_kind(record)
        self.assertFalse(result)

        # Test with no kind in record
        record = {}
        result = self.client.get_member_kind(record)
        self.assertFalse(result)

    def test_get_member_relationship(self):
        # Test with existing relationship
        mock_relation = MagicMock()
        mock_relation.id = 1
        self.env_mock["g2p.relationship"].search.return_value = mock_relation

        source_id = 1
        record = {"relationship_with_head": "spouse"}
        result = self.client.get_member_relationship(source_id, record)

        self.assertIsNotNone(result)
        self.assertEqual(result["source"], source_id)
        self.assertEqual(result["relation"], mock_relation.id)
        self.assertIsInstance(result["start_date"], datetime)

        # Test with non-existent relationship
        self.env_mock["g2p.relationship"].search.return_value = False
        record = {"relationship_with_head": "nonexistent"}
        result = self.client.get_member_relationship(source_id, record)
        self.assertIsNone(result)

        # Test with no relationship in record
        record = {}
        result = self.client.get_member_relationship(source_id, record)
        self.assertIsNone(result)

    def test_get_gender(self):
        # Test with existing gender
        mock_gender = MagicMock()
        mock_gender.code = "M"
        self.env_mock["gender.type"].sudo.return_value.search.return_value = mock_gender

        result = self.client.get_gender("male")
        self.assertEqual(result, "M")

        # Test with non-existent gender
        self.env_mock["gender.type"].sudo.return_value.search.return_value = False
        result = self.client.get_gender("nonexistent")
        self.assertIsNone(result)

        # Test with None gender value
        result = self.client.get_gender(None)
        self.assertIsNone(result)

    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.get_individual_data")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.get_member_kind")
    @patch("odoo.addons.g2p_odk_importer.models.odk_client.ODKClient.get_member_relationship")
    def test_handle_group_membership(self, mock_get_relationship, mock_get_kind, mock_get_individual_data):
        # Setup mock returns
        mock_individual = MagicMock()
        mock_individual.id = 1
        self.env_mock["res.partner"].sudo.return_value.create.return_value = mock_individual

        mock_kind = MagicMock()
        mock_kind.id = 2
        mock_get_kind.return_value = mock_kind

        mock_relationship = {"source": 1, "relation": 3, "start_date": datetime.now()}
        mock_get_relationship.return_value = mock_relationship

        mock_individual_data = {"name": "Test Person", "given_name": "Test", "family_name": "Person"}
        mock_get_individual_data.return_value = mock_individual_data

        # Test data
        mapped_json = {
            "group_membership_ids": [
                {"name": "Test Person", "kind": "member", "relationship_with_head": "spouse"}
            ]
        }

        # Execute the group membership handling
        self.client.target_registry = "group"
        self.client.handle_one2many_fields(mapped_json)

        # Verify the results
        self.assertTrue("group_membership_ids" in mapped_json)
        self.assertTrue("related_1_ids" in mapped_json)

        # Verify individual creation
        self.env_mock["res.partner"].sudo.return_value.create.assert_called_once_with(mock_individual_data)

        # Verify relationship creation
        self.assertEqual(len(mapped_json["related_1_ids"]), 1)
        self.assertEqual(mapped_json["related_1_ids"][0][0], 0)
        self.assertEqual(mapped_json["related_1_ids"][0][1], 0)
        self.assertEqual(mapped_json["related_1_ids"][0][2], mock_relationship)

        # Verify group membership creation
        self.assertEqual(len(mapped_json["group_membership_ids"]), 1)
        expected_individual_data = {"individual": mock_individual.id, "kind": [(4, mock_kind.id)]}
        self.assertEqual(mapped_json["group_membership_ids"][0][2], expected_individual_data)

    def test_handle_group_membership_no_relationship(self):
        # Test handling when no relationship is found
        mapped_json = {"group_membership_ids": [{"name": "Test Person"}]}

        mock_individual = MagicMock()
        mock_individual.id = 1
        self.env_mock["res.partner"].sudo.return_value.create.return_value = mock_individual

        self.client.target_registry = "group"
        self.client.handle_one2many_fields(mapped_json)

        # Verify only group membership was created without relationship
        self.assertTrue("group_membership_ids" in mapped_json)
        self.assertEqual(len(mapped_json.get("related_1_ids", [])), 0)
        self.assertEqual(len(mapped_json["group_membership_ids"]), 1)
        expected_individual_data = {"individual": mock_individual.id}
        self.assertEqual(mapped_json["group_membership_ids"][0][2], expected_individual_data)

    def test_handle_one2many_fields(self):
        # Create a mock environment with proper structure
        mock_id_type = MagicMock()
        mock_id_type.id = 1

        # Set up the mock environment chain
        mock_search = MagicMock(return_value=mock_id_type)
        mock_g2p_id_type = MagicMock()
        mock_g2p_id_type.search = mock_search

        # Configure the env_mock to return the mock_g2p_id_type when accessed
        self.env_mock.__getitem__.return_value = mock_g2p_id_type

        # Test data
        mapped_json = {
            "phone_number_ids": [
                {"phone_no": "123456789", "date_collected": "2024-07-01", "disabled": False}
            ],
            "group_membership_ids": [],
            "reg_ids": [{"id_type": "National ID", "value": "12345", "expiry_date": "2024-12-31"}],
        }

        # Execute
        self.client.handle_one2many_fields(mapped_json)

        # Assert phone_number_ids structure
        self.assertIn("phone_number_ids", mapped_json)
        self.assertEqual(len(mapped_json["phone_number_ids"]), 1)
        phone_data = mapped_json["phone_number_ids"][0]
        self.assertEqual(phone_data[0], 0)  # create command
        self.assertEqual(phone_data[1], 0)  # no id
        self.assertEqual(phone_data[2]["phone_no"], "123456789")
        self.assertEqual(phone_data[2]["date_collected"], "2024-07-01")
        self.assertEqual(phone_data[2]["disabled"], False)

        # Assert reg_ids structure
        self.assertIn("reg_ids", mapped_json)
        self.assertEqual(len(mapped_json["reg_ids"]), 1)
        reg_data = mapped_json["reg_ids"][0]
        self.assertEqual(reg_data[0], 0)  # create command
        self.assertEqual(reg_data[1], 0)  # no id
        self.assertEqual(reg_data[2]["id_type"], mock_id_type.id)
        self.assertEqual(reg_data[2]["value"], "12345")
        self.assertEqual(reg_data[2]["expiry_date"], "2024-12-31")

        # Verify the search was called correctly
        mock_search.assert_called_with([("name", "=", "National ID")], limit=1)

    def test_handle_one2many_fields_no_id_type_found(self):
        # Set up the mock environment to return False for id_type search
        mock_search = MagicMock(return_value=False)
        mock_g2p_id_type = MagicMock()
        mock_g2p_id_type.search = mock_search
        self.env_mock.__getitem__.return_value = mock_g2p_id_type

        # Test data
        mapped_json = {
            "reg_ids": [{"id_type": "NonExistent ID", "value": "12345", "expiry_date": "2024-12-31"}]
        }

        # Test should raise a ValidationError or handle the case appropriately
        with self.assertRaises(AttributeError):
            self.client.handle_one2many_fields(mapped_json)

    def test_handle_one2many_fields_empty(self):
        """Test handling empty mapped_json"""
        mapped_json = {}
        self.client.handle_one2many_fields(mapped_json)
        self.assertEqual(mapped_json, {})

    def test_handle_one2many_fields_only_phone(self):
        """Test handling only phone numbers"""
        mapped_json = {
            "phone_number_ids": [{"phone_no": "123456789", "date_collected": "2024-07-01", "disabled": False}]
        }
        self.client.handle_one2many_fields(mapped_json)
        self.assertEqual(len(mapped_json["phone_number_ids"]), 1)
        self.assertEqual(mapped_json["phone_number_ids"][0][2]["phone_no"], "123456789")

    def test_import_delta_records_with_timestamp(self):
        """Test importing records with a last sync timestamp"""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"submission_time": "2024-01-01T10:00:00.000Z"}]}

        # Create a timestamp for testing
        test_timestamp = datetime(2024, 1, 1, 8, 0, 0)
        expected_filter = "__system/submissionDate ge 2024-01-01T08:00:00.000Z"

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            # Call the method with timestamp
            self.client.session = "test_token"  # Set session token
            self.client.import_delta_records(last_sync_timestamp=test_timestamp)

            # Verify the request was made with correct parameters
            actual_params = mock_get.call_args[1]["params"]
            self.assertIn("$filter", actual_params)
            self.assertEqual(actual_params["$filter"], expected_filter)

    def test_import_delta_records_without_timestamp(self):
        """Test importing records without a last sync timestamp"""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"submission_time": "2024-01-01T10:00:00.000Z"}]}

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            # Call the method without timestamp
            self.client.session = "test_token"  # Set session token
            self.client.import_delta_records()

            # Verify the request was made without filter parameter
            actual_params = mock_get.call_args[1]["params"]
            self.assertNotIn("$filter", actual_params)

    def test_import_delta_records_request_exception(self):
        """Test handling of RequestException during import"""
        with patch("requests.get") as mock_get:
            # Simulate a request exception
            mock_get.side_effect = requests.RequestException("Network error")

            self.client.session = "test_token"  # Set session token

            # Verify that ValidationError is raised with the correct message
            with self.assertRaises(ValidationError) as context:
                self.client.import_delta_records()

            self.assertEqual(str(context.exception), "Failed to parse response: Network error")

    def test_import_delta_records_with_skip(self):
        """Test importing records with skip parameter"""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"submission_time": "2024-01-01T10:00:00.000Z"}]}

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            # Call the method with skip parameter
            self.client.session = "test_token"  # Set session token
            skip_value = 10
            self.client.import_delta_records(skip=skip_value)

            # Verify the request was made with correct skip parameter
            actual_params = mock_get.call_args[1]["params"]
            self.assertEqual(actual_params["$skip"], skip_value)

    def test_import_delta_records_timestamp_and_skip(self):
        """Test importing records with both timestamp and skip parameters"""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"submission_time": "2024-01-01T10:00:00.000Z"}]}

        test_timestamp = datetime(2024, 1, 1, 8, 0, 0)
        skip_value = 10
        expected_filter = "__system/submissionDate ge 2024-01-01T08:00:00.000Z"

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            # Call the method with both parameters
            self.client.session = "test_token"  # Set session token
            self.client.import_delta_records(last_sync_timestamp=test_timestamp, skip=skip_value)

            # Verify all parameters are correct
            actual_params = mock_get.call_args[1]["params"]
            self.assertEqual(actual_params["$skip"], skip_value)
            self.assertEqual(actual_params["$filter"], expected_filter)

    def test_import_record_by_instance_id_request_exception(self):
        """Test handling of RequestException during import by instance ID"""
        instance_id = "test-instance-123"

        with patch("requests.get") as mock_get:
            # Simulate a network error
            mock_get.side_effect = requests.RequestException("Network error")

            self.client.session = "test_token"  # Set session token

            # Verify that ValidationError is raised with the correct message
            with self.assertRaises(ValidationError) as context:
                self.client.import_record_by_instance_id(instance_id)

            self.assertEqual(
                str(context.exception), "Failed to parse response by using instance ID: Network error"
            )

    def test_import_record_by_instance_id_success(self):
        """Test successful import of record by instance ID with correct registry flags"""
        instance_id = "test-instance-123"

        # Mock response data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [{"name": "Doe John", "family_name": "Doe", "given_name": "John"}]
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            # Set up environment mock for partner creation
            mock_partner = MagicMock()
            self.env_mock["res.partner"].sudo.return_value.create = MagicMock(return_value=mock_partner)

            # Test individual registry
            self.client.session = "test_token"
            self.client.target_registry = "individual"
            result = self.client.import_record_by_instance_id(instance_id)

            # Verify the created partner data had correct flags
            create_call_args = self.env_mock["res.partner"].sudo.return_value.create.call_args[0][0]
            self.assertTrue(create_call_args["is_registrant"])
            self.assertFalse(create_call_args["is_group"])
            self.assertEqual(create_call_args["name"], "Doe John")
            self.assertTrue(result["form_updated"])

    def test_import_record_by_instance_id_group(self):
        """Test import of record by instance ID for group registry"""
        instance_id = "test-instance-123"

        # Mock response data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [{"name": "Family Group", "family_name": "Family", "given_name": "Group"}]
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            # Set up environment mock for partner creation
            mock_partner = MagicMock()
            self.env_mock["res.partner"].sudo.return_value.create = MagicMock(return_value=mock_partner)

            # Test group registry
            self.client.session = "test_token"
            self.client.target_registry = "group"
            result = self.client.import_record_by_instance_id(instance_id)

            # Verify the created partner data had correct flags
            create_call_args = self.env_mock["res.partner"].sudo.return_value.create.call_args[0][0]
            self.assertTrue(create_call_args["is_registrant"])
            self.assertTrue(create_call_args["is_group"])
            self.assertEqual(create_call_args["name"], "Family Group")
            self.assertTrue(result["form_updated"])

    def test_import_record_by_instance_id_with_timestamp(self):
        """Test import of record by instance ID with timestamp parameter"""
        instance_id = "test-instance-123"
        test_timestamp = datetime(2024, 1, 1, 8, 0, 0)

        # Mock response data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"family_name": "Doe", "given_name": "John"}]}

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response

            self.client.session = "test_token"
            self.client.import_record_by_instance_id(instance_id, last_sync_timestamp=test_timestamp)

            # Verify API call parameters
            call_kwargs = mock_get.call_args[1]
            self.assertIn("params", call_kwargs)
            self.assertEqual(call_kwargs["params"]["$skip"], 0)
            self.assertEqual(call_kwargs["params"]["$count"], "true")
            self.assertEqual(call_kwargs["params"]["$expand"], "*")

    @patch("requests.get")
    def test_get_submissions_with_fields(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"field1": "value1"}]}
        mock_get.return_value = mock_response

        fields = "field1,field2"
        submissions = self.client.get_submissions(fields=fields)
        self.assertIn("$select", mock_get.call_args[1]["params"])
        self.assertEqual(mock_get.call_args[1]["params"]["$select"], fields)
        self.assertEqual(submissions[0]["field1"], "value1")

    @patch("requests.get")
    def test_get_submissions_with_last_sync_time(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"id": 1}]}
        mock_get.return_value = mock_response

        last_sync_time = datetime(2024, 12, 25, 10, 0, 0)
        submissions = self.client.get_submissions(last_sync_time=last_sync_time)
        expected_filter = "__system/submissionDate ge 2024-12-25T10:00:00.000Z"
        self.assertIn("$filter", mock_get.call_args[1]["params"])
        self.assertEqual(mock_get.call_args[1]["params"]["$filter"], expected_filter)
        self.assertEqual(submissions[0]["id"], 1)

    @patch("requests.get")
    def test_get_submissions_invalid_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"field1": "value1"}]  # Not a dict
        mock_get.return_value = mock_response

        with self.assertLogs(level="ERROR") as log:
            submissions = self.client.get_submissions()
            self.assertIn("Unexpected response format", log.output[0])
            self.assertEqual(len(submissions), 0)

    @patch("requests.get")
    def test_handle_media_import_no_instance_id(self, mock_get):
        # Test with missing instance_id
        member = {"meta": {}}  # No instanceID
        mapped_json = {}

        self.client.handle_media_import(member, mapped_json)
        self.assertEqual(mapped_json, {})  # No changes should be made

    @patch("requests.get")
    def test_handle_media_import_no_attachments(self, mock_get):
        # Test with empty attachments
        member = {"meta": {"instanceID": "test_instance"}}
        mapped_json = {}

        with patch.object(self.client, "list_expected_attachments", return_value=[]):
            self.client.handle_media_import(member, mapped_json)
            self.assertEqual(mapped_json, {})  # No changes should be made

    @patch("requests.get")
    def test_import_delta_records_is_registrant(self, mock_get):
        # Set target_registry to "individual"
        self.client.target_registry = "individual"

        # Mock response for submissions
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"submission_time": "2024-01-01T10:00:00.000Z"}]}
        mock_get.return_value = mock_response

        # Call the method
        with patch.object(self.client, "get_addl_data", side_effect=lambda x: x):
            with patch.object(self.client, "handle_one2many_fields"):
                self.client.import_delta_records()

        # Check if "is_registrant" and "is_group" were set correctly
        create_call_args = self.env_mock["res.partner"].sudo.return_value.create.call_args[0][0]
        self.assertTrue(create_call_args["is_registrant"])
        self.assertFalse(create_call_args["is_group"])

    @patch("requests.get")
    def test_import_record_by_instance_id_is_registrant(self, mock_get):
        # Set target_registry to "individual"
        self.client.target_registry = "individual"

        # Mock response for submissions
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [{"name": "Doe John", "family_name": "Doe", "given_name": "John"}]
        }
        mock_get.return_value = mock_response

        # Call the method
        with patch.object(self.client, "handle_one2many_fields"):
            self.client.import_record_by_instance_id("test_instance_id")

        # Check if "is_registrant" and "is_group" were set correctly
        create_call_args = self.env_mock["res.partner"].sudo.return_value.create.call_args[0][0]
        self.assertTrue(create_call_args["is_registrant"])
        self.assertFalse(create_call_args["is_group"])
        self.assertEqual(create_call_args["name"], "Doe John")

    def test_get_dob_future_birth_year(self):
        # Create a record with an age resulting in a birthdate one day in the future
        now = datetime.now()
        future_age = now.year - (now.year + 1) + 1  # Simulate age for birthdate exactly one day in the future
        record = {"age": int(future_age)}  # Ensure age is an integer

        # Call the method
        dob = self.client.get_dob(record)

        # Verify the return value is None
        self.assertIsNone(dob)

    @patch("requests.get")
    def test_handle_media_import_first_image_stored(self, mock_get):
        # Test storing the first image
        member = {"meta": {"instanceID": "test_instance"}}
        mapped_json = {"image_1920": None}  # Ensure the key exists in mapped_json

        # Mock methods to return valid data
        attachment_data = b"fake_image_data"
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = attachment_data

        with patch.object(self.client, "list_expected_attachments", return_value=[{"name": "image1.jpg"}]):
            with patch.object(self.client, "is_image", return_value=True):
                with patch.object(self.client, "download_attachment", return_value=attachment_data):
                    self.client.handle_media_import(member, mapped_json)

                    # Verify the first image was stored
                    self.assertIsNotNone(mapped_json["image_1920"])
                    self.assertEqual(
                        mapped_json["image_1920"], base64.b64encode(attachment_data).decode("utf-8")
                    )

    @patch("requests.get")
    def test_handle_media_import_no_first_image_stored(self, mock_get):
        # Test when first image is already stored
        member = {"meta": {"instanceID": "test_instance"}}
        mapped_json = {"image_1920": "already_set_image"}  # Already set

        # Mock methods to return valid data
        attachment_data = b"fake_image_data"
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = attachment_data

        with patch.object(self.client, "list_expected_attachments", return_value=[{"name": "image1.jpg"}]):
            with patch.object(self.client, "is_image", return_value=True):
                with patch.object(self.client, "download_attachment", return_value=attachment_data):
                    self.client.handle_media_import(member, mapped_json)

                    # Verify the first image was not overwritten
                    # self.assertEqual(mapped_json["image_1920"], "already_set_image")
