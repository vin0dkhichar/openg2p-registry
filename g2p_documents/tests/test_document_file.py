import base64
import io
from unittest.mock import patch

from PIL import Image

from odoo.exceptions import UserError

from odoo.addons.component.tests.common import TransactionComponentCase


class TestG2PDocumentFile(TransactionComponentCase):
    def setUp(self):
        super().setUp()
        self.storage_backend = self.env["storage.backend"].create({"name": "Test Backend"})

        self.test_data = b"Test Data"
        self.test_file = self.env["storage.file"].create(
            {
                "name": "test.txt",
                "backend_id": self.storage_backend.id,
                "data": base64.b64encode(self.test_data),
            }
        )

    def test_filter_for_tags_multiple(self):
        tag1 = self.env["g2p.document.tag"].create({"name": "Tag1"})
        tag2 = self.env["g2p.document.tag"].create({"name": "Tag2"})

        file1 = self.env["storage.file"].create(
            {
                "name": "test1.txt",
                "backend_id": self.storage_backend.id,
                "data": base64.b64encode(b"test data 1"),
                "tags_ids": [(6, 0, [tag1.id])],
            }
        )

        file2 = self.env["storage.file"].create(
            {
                "name": "test2.txt",
                "backend_id": self.storage_backend.id,
                "data": base64.b64encode(b"test data 2"),
                "tags_ids": [(6, 0, [tag2.id])],
            }
        )

        files = self.env["storage.file"].search([])

        filtered = files.filter_for_tags(["Tag1"])
        self.assertEqual(filtered[0].id, file1.id)

        filtered = files.filter_for_tags_any(["Tag2"])
        self.assertEqual(filtered[0].id, file2.id)

        filtered = files.filter_for_tags_any(["Tag1", "Tag2"])
        self.assertEqual(len(filtered), 2)

        filtered = files.filter_for_tags_any(["NonExistentTag"])
        self.assertEqual(len(filtered), 0)

    def test_filter_for_tags_any(self):
        tag1 = self.env["g2p.document.tag"].create({"name": "Tag1"})
        self.test_file.write({"tags_ids": [(6, 0, [tag1.id])]})

        files = self.env["storage.file"].search([])
        filtered = files.filter_for_tags_any(["Tag1", "NonExistentTag"])
        self.assertEqual(len(filtered), 1)

    def test_compute_file_type(self):
        img_data = Image.new("RGB", (60, 30), color="red")
        img_byte_arr = io.BytesIO()
        img_data.save(img_byte_arr, format="PNG")

        image_file = self.env["storage.file"].create(
            {
                "name": "test.png",
                "backend_id": self.storage_backend.id,
                "data": base64.b64encode(img_byte_arr.getvalue()),
                "mimetype": "image/png",
            }
        )

        image_file._compute_file_type()
        self.assertEqual(image_file.file_type, "PNG")

    def test_compute_extract_filename(self):
        self.test_file._compute_extract_filename()
        self.assertEqual(self.test_file.filename, "test")
        self.assertEqual(self.test_file.extension, ".txt")

    def test_get_mime_type(self):
        img_data = Image.new("RGB", (60, 30), color="red")
        img_byte_arr = io.BytesIO()
        img_data.save(img_byte_arr, format="PNG")

        mime_type = self.test_file._get_mime_type(img_byte_arr.getvalue())
        self.assertEqual(mime_type, "image/png")

        mime_type = self.test_file._get_mime_type(b"invalid data")
        self.assertIsNone(mime_type)

    def test_compute_data_key_error(self):
        file = self.env["storage.file"].create(
            {
                "name": "test.txt",
                "backend_id": self.storage_backend.id,
                "data": base64.b64encode(self.test_data),
            }
        )

        with patch.object(file.backend_id.__class__, "get", side_effect=Exception("NoSuchKey")):
            with self.assertRaises(UserError) as cm:
                file._compute_data()

            self.assertEqual(str(cm.exception), "The file with the given name is not present on the s3.")
