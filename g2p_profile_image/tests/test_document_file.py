from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestG2PDocumentFile(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test data
        cls.backend = cls.env["storage.backend"].create({"name": "Default S3 Document Store"})
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

        # Get or create profile tag
        cls.profile_tag = cls._create_profile_tag()

    @classmethod
    def _create_profile_tag(cls):
        """Get existing profile tag or create new one"""
        # if profile image tag is exist then first rmove it
        cls.env["g2p.document.tag"].search([("name", "=", "Profile Image")]).unlink()
        return cls.env["g2p.document.tag"].create({"name": "Profile Image"})

    def test_01_create_file_without_profile_tag(self):
        """Test creating a file without profile tag"""
        vals = {
            "name": "Test File",
            "registrant_id": self.partner.id,
            "backend_id": self.backend.id,
            "tags_ids": [],
        }
        file = self.env["storage.file"].create(vals)
        self.assertTrue(file)
        self.assertEqual(file.name, "Test File")

    def test_02_create_file_with_profile_tag_no_existing(self):
        """Test creating a file with profile tag when no existing file"""
        vals = {
            "name": "Profile Image",
            "registrant_id": self.partner.id,
            "backend_id": self.backend.id,
            "tags_ids": [(4, self.profile_tag.id)],
        }
        file = self.env["storage.file"].create(vals)
        self.assertTrue(file)
        self.assertEqual(file.name, "Profile Image")

    def test_03_create_file_with_profile_tag_existing(self):
        """Test creating a file with profile tag when existing file exists"""
        # Create first file
        vals = {
            "name": "Profile Image 1",
            "registrant_id": self.partner.id,
            "backend_id": self.backend.id,
            "tags_ids": [(4, self.profile_tag.id)],
        }
        first_file = self.env["storage.file"].create(vals)
        self.assertTrue(first_file)

        # Try to create second file
        vals = {
            "name": "Profile Image 2",
            "registrant_id": self.partner.id,
            "backend_id": self.backend.id,
            "tags_ids": [(4, self.profile_tag.id)],
        }
        with self.assertRaises(UserError):
            self.env["storage.file"].create(vals)

    def test_04_create_multiple_files(self):
        """Test creating multiple files at once"""
        vals_list = [
            {
                "name": "Regular File 1",
                "registrant_id": self.partner.id,
                "backend_id": self.backend.id,
                "tags_ids": [],
            },
            {
                "name": "Regular File 2",
                "registrant_id": self.partner.id,
                "backend_id": self.backend.id,
                "tags_ids": [],
            },
        ]
        files = self.env["storage.file"].create(vals_list)
        self.assertEqual(len(files), 2)

    def test_05_create_multiple_files_with_profile_tag(self):
        """Test creating multiple files with profile tag"""
        vals_list = [
            {
                "name": "Profile Image 1",
                "registrant_id": self.partner.id,
                "backend_id": self.backend.id,
                "tags_ids": [(4, self.profile_tag.id)],
            },
            {
                "name": "Regular File",
                "registrant_id": self.partner.id,
                "backend_id": self.backend.id,
                "tags_ids": [],
            },
        ]
        files = self.env["storage.file"].create(vals_list)
        self.assertEqual(len(files), 2)

        # Try to create another file with profile tag
        vals = {
            "name": "Profile Image 2",
            "registrant_id": self.partner.id,
            "backend_id": self.backend.id,
            "tags_ids": [(4, self.profile_tag.id)],
        }
        with self.assertRaises(UserError):
            self.env["storage.file"].create(vals)
