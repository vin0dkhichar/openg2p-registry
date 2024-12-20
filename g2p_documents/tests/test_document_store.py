import base64
from unittest.mock import patch

from odoo.addons.component.tests.common import TransactionComponentCase


class TestG2PDocumentStore(TransactionComponentCase):
    # Setup test environment by creating a storage backend.
    def setUp(self):
        super().setUp()
        self.storage_backend = self.env["storage.backend"].create({"name": "Test Backend"})

    # Test the method that opens the file tree for the storage backend.
    def test_open_store_files_tree(self):
        # Call the method to retrieve the store files tree
        result = self.storage_backend.open_store_files_tree()

        # Verify that the returned result matches the expected action window
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "storage.file")
        self.assertEqual(result["view_mode"], "tree,form")
        self.assertEqual(result["context"], {"hide_backend": 1})
        self.assertEqual(result["domain"], [("backend_id", "=", self.storage_backend.id)])

    # Test the method that adds a file without a specific name (uses UUID).
    def test_add_file_without_name(self):
        test_data = b"Test Data"

        # Patch uuid.uuid4 to return a fixed value
        with patch("uuid.uuid4", return_value="test-uuid"):
            file = self.storage_backend.add_file(test_data)

        # Verify that the file was created with the expected name (UUID) and data
        self.assertEqual(file.name, "test-uuid")
        self.assertEqual(file.backend_id, self.storage_backend)
        self.assertEqual(file.data, base64.b64encode(test_data))

    # Test the method that adds a file with a specified name and extension.
    def test_add_file_with_name_and_extension(self):
        test_data = b"Test data"
        test_name = "test_file"
        test_extension = ".txt"

        # Add the file with a name and extension
        file = self.storage_backend.add_file(data=test_data, name=test_name, extension=test_extension)

        # Verify the file name includes the extension and correct data
        self.assertEqual(file.name, "test_file.txt")
        self.assertEqual(file.backend_id, self.storage_backend)
        self.assertEqual(file.data, base64.b64encode(test_data))

    # Test adding a file with a string tag (create and assign the tag).
    def test_add_file_with_string_tag(self):
        test_data = b"Test Data"
        test_tag = "TestTag"

        # Create the tag in the system
        tag = self.env["g2p.document.tag"].create({"name": test_tag})

        # Add the file with the tag name (string)
        file = self.storage_backend.add_file(test_data, tags=test_tag)

        # Verify the file has the correct tag assigned
        self.assertTrue(file.tags_ids)
        self.assertEqual(file.tags_ids[0].name, test_tag)
        self.assertEqual(len(file.tags_ids), 1)
        self.assertIn(tag, file.tags_ids)

    # Test adding a file with multiple tags.
    def test_add_file_with_multiple_tags(self):
        test_data = b"Test data"
        test_tags = ["Tag1", "Tag2"]

        # Add the file with multiple tags
        file = self.storage_backend.add_file(test_data, tags=test_tags)

        # Verify the file has all tags assigned
        self.assertEqual(len(file.tags_ids), 2)
        self.assertEqual(file.tags_ids.mapped("name"), test_tags)

    # Test adding a file with an existing tag.
    def test_add_file_with_existing_tag(self):
        test_data = b"Test data"

        # Create an existing tag in the system
        existing_tag = self.env["g2p.document.tag"].create({"name": "ExistingTag"})

        # Add the file with the existing tag's name
        file = self.storage_backend.add_file(test_data, tags=existing_tag.name)

        # Verify the file is correctly assigned to the existing tag
        self.assertEqual(len(file.tags_ids), 1)
        self.assertEqual(file.tags_ids[0], existing_tag)

    # Test the method that generates a random name using UUID.
    def test_gen_random_name(self):
        # Patch uuid.uuid4 to return a fixed value
        with patch("uuid.uuid4", return_value="test-uuid"):
            name = self.storage_backend._gen_random_name()

        # Verify the generated name matches the expected value
        self.assertEqual(name, "test-uuid")
