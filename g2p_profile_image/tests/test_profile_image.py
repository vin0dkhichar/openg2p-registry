import base64
import io
import logging
import random
from unittest.mock import MagicMock, patch

from PIL import Image, ImageDraw

from odoo.tests import tagged

from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.addons.g2p_profile_image.models.profile_image import G2PImageStorage

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestProfileImage(TransactionComponentCase):
    """Test cases for Profile Image functionality"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_s3_backend()
        cls._setup_system_parameters()
        cls.profile_tag = cls._create_profile_tag()

    @classmethod
    def _setup_s3_backend(cls):
        """Set up S3 backend configuration"""
        cls.s3_backend = cls.env["storage.backend"].create(
            {
                "name": "Default S3 Document Store",
                "backend_type": "amazon_s3",
                "aws_access_key_id": "test_key",
                "aws_secret_access_key": "test_secret",
                "aws_bucket": "documents",
                "aws_host": "http://127.0.0.1:9000",
                "aws_region": "us-east-1",
                "directory_path": "profile_images/",
                "is_public": True,
            }
        )

    @classmethod
    def _setup_system_parameters(cls):
        """Set up required system parameters"""
        params = cls.env["ir.config_parameter"].sudo()
        params.set_param("g2p_profile_image.auto_create_profile_image", "True")
        params.set_param("g2p_profile_image.storage_backend_id", str(cls.s3_backend.id))

    @classmethod
    def _create_profile_tag(cls):
        """Get existing profile tag or create new one"""
        # if profile image tag is exist then first rmove it
        cls.env["g2p.document.tag"].search([("name", "=", "Profile Image")]).unlink()
        return cls.env["g2p.document.tag"].create({"name": "Profile Image"})

    def setUp(self):
        super().setUp()
        self.mock_s3()

    def test_image_lifecycle(self):
        """Test complete lifecycle of profile image operations"""
        _logger.info("⚡ Starting g2p_profile_image test... Please wait, this may take few minutes. ⏳")

        _logger.info("🔄 Testing partner creation with large image...")
        self._test_create_partner_with_large_image()

        _logger.info("🔄 Testing partner creation with small image...")
        self._test_create_partner_with_small_image()

        _logger.info("🔄 Testing partner image removal...")
        self._test_update_partner_remove_image()

        _logger.info("🔄 Testing profile tag creation...")
        self._test_create_profile_tag()

        _logger.info("🔄 Testing image resize quality...")
        self._test_image_resize_quality()

        _logger.info("✅ g2p_profile_image test completed successfully! ✅")

    def mock_s3(self):
        """Set up S3 mocking for tests"""
        patcher = patch("odoo.addons.storage_backend_s3.components.s3_adapter.boto3")
        mock_boto3 = patcher.start()

        # Configure mock objects
        mock_s3_client = MagicMock()
        mock_s3_resource = MagicMock()
        mock_bucket = MagicMock()
        mock_object = MagicMock()

        mock_boto3.client.return_value = mock_s3_client
        mock_boto3.resource.return_value = mock_s3_resource
        mock_s3_resource.Bucket.return_value = mock_bucket
        mock_bucket.Object.return_value = mock_object

        self.addCleanup(patcher.stop)
        return mock_boto3

    @staticmethod
    def generate_large_image_binary(target_size_mb):
        """Generate test image of specified size with autumn colors"""
        autumn_colors = [
            (255, 69, 0),  # Red-Orange
            (255, 140, 0),  # Dark Orange
            (255, 165, 0),  # Orange
            (255, 215, 0),  # Gold
            (218, 165, 32),  # Golden Rod
            (210, 105, 30),  # Chocolate
            (139, 69, 19),  # Saddle Brown
            (165, 42, 42),  # Brown
        ]

        # Calculate dimensions for target size
        target_bytes = target_size_mb * 1024 * 1024
        aspect_ratio = 16 / 9
        base_size = int((target_bytes / 3) ** 0.5)
        width = int(base_size * aspect_ratio)
        height = base_size

        # Generate and fill image
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        for y in range(height):
            for x in range(width):
                draw.point((x, y), fill=random.choice(autumn_colors))

        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG", compress_level=0)
        return img_buffer.getvalue()

    def _test_create_partner_with_large_image(self):
        """Test creating a partner with a large image"""
        large_image = base64.b64encode(self.generate_large_image_binary(2)).decode("utf-8")

        storage_file = self.env["storage.file"].create(
            {
                "name": "Profile Image",
                "backend_id": self.s3_backend.id,
                "data": large_image,
                "tags_ids": [(4, self.profile_tag.id)],
            }
        )

        partner = (
            self.env["res.partner"]
            .with_context(test_profile_image=True, storage_file_id=storage_file.id)
            .create({"name": "Test Large Image", "image_1920": large_image})
        )

        storage_file.write({"registrant_id": partner.id})
        self.env.flush_all()

    def _test_create_partner_with_small_image(self):
        """Test creating a partner with a small image"""
        small_image = base64.b64encode(self.generate_large_image_binary(0.5)).decode("utf-8")

        partner = self.env["res.partner"].create({"name": "Test Small Image", "image_1920": small_image})

        storage_file = self.env["storage.file"].search(
            [("registrant_id", "=", partner.id), ("tags_ids", "in", [self.profile_tag.id])]
        )
        self.assertFalse(storage_file.exists())

    def _test_update_partner_remove_image(self):
        """Test updating a partner to remove the image"""
        initial_image = base64.b64encode(self.generate_large_image_binary(1)).decode("utf-8")
        partner = self.env["res.partner"].create({"name": "Test Remove Image", "image_1920": initial_image})

        partner.write({"image_1920": False})

        self.assertFalse(partner.image_1920)
        storage_file = self.env["storage.file"].search(
            [("registrant_id", "=", partner.id), ("tags_ids", "in", [self.profile_tag.id])]
        )
        self.assertFalse(storage_file.exists())

    def _test_create_profile_tag(self):
        """Test creating a new profile tag when it doesn't exist"""
        self.profile_tag.unlink()

        image = base64.b64encode(self.generate_large_image_binary(0.5)).decode("utf-8")
        self.env["res.partner"].create({"name": "Test Tag Creation", "image_1920": image})

        new_tag = self.env["g2p.document.tag"].search([("name", "=", "Profile Image")])
        self.assertTrue(new_tag)

    def _test_image_resize_quality(self):
        """Test image resize with different quality settings"""
        test_sizes = [0.001, 1.1, 2.0, 4.0, 32]  # MB

        for size in test_sizes:
            img = self.generate_large_image_binary(size)
            resized = G2PImageStorage._resize_image(self, img)
            decoded = base64.b64decode(resized)

            self.assertLess(len(decoded), 1024 * 1024)
            Image.open(io.BytesIO(decoded))  # Verify image integrity
