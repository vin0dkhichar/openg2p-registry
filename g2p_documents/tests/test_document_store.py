import base64
from unittest.mock import patch

from odoo.addons.component.tests.common import TransactionComponentCase


class TestG2PDocumentStore(TransactionComponentCase):
    def setUp(self):
        super().setUp()
        self.storage_backend = self.env["storage.backend"].create({"name": "Test Backend"})

    def test_open_store_files_tree(self):
        result = self.storage_backend.open_store_files_tree()

        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "storage.file")
        self.assertEqual(result["view_mode"], "tree,form")
        self.assertEqual(result["context"], {"hide_backend": 1})
        self.assertEqual(result["domain"], [("backend_id", "=", self.storage_backend.id)])

    def test_add_file_without_name(self):
        test_data = b"Test Data"

        with patch("uuid.uuid4", return_value="test-uuid"):
            file = self.storage_backend.add_file(test_data)

        self.assertEqual(file.name, "test-uuid")
        self.assertEqual(file.backend_id, self.storage_backend)
        self.assertEqual(file.data, base64.b64encode(test_data))

    def test_add_file_with_name_and_extension(self):
        test_data = b"Test data"
        test_name = "test_file"
        test_extension = ".txt"

        file = self.storage_backend.add_file(data=test_data, name=test_name, extension=test_extension)

        self.assertEqual(file.name, "test_file.txt")
        self.assertEqual(file.backend_id, self.storage_backend)
        self.assertEqual(file.data, base64.b64encode(test_data))

    def test_add_file_with_string_tag(self):
        test_data = b"Test Data"
        test_tag = "TestTag"

        tag = self.env["g2p.document.tag"].create({"name": test_tag})

        file = self.storage_backend.add_file(test_data, tags=test_tag)

        self.assertTrue(file.tags_ids)
        self.assertEqual(file.tags_ids[0].name, test_tag)
        self.assertEqual(len(file.tags_ids), 1)
        self.assertIn(tag, file.tags_ids)

    def test_add_file_with_multiple_tags(self):
        test_data = b"Test data"
        test_tags = ["Tag1", "Tag2"]
        file = self.storage_backend.add_file(test_data, tags=test_tags)
        self.assertEqual(len(file.tags_ids), 2)
        self.assertEqual(file.tags_ids.mapped("name"), test_tags)

    def test_add_file_with_existing_tag(self):
        test_data = b"Test data"

        existing_tag = self.env["g2p.document.tag"].create({"name": "ExistingTag"})
        file = self.storage_backend.add_file(test_data, tags=existing_tag.name)
        self.assertEqual(len(file.tags_ids), 1)
        self.assertEqual(file.tags_ids[0], existing_tag)

    def test_gen_random_name(self):
        with patch("uuid.uuid4", return_value="test-uuid"):
            name = self.storage_backend._gen_random_name()

        self.assertEqual(name, "test-uuid")
