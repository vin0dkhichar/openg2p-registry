import base64
import io
import logging
import random

from PIL import Image, ImageDraw

from odoo.tests import tagged

from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.addons.g2p_profile_image.models.profile_image import G2PImageStorage

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestProfileImage(TransactionComponentCase):
    """Test cases for Profile Image functionality"""

    def setUp(self):
        """Set up test environment before each test method"""
        super().setUp()
        self._create_test_data()

    def _create_test_data(self):
        """Create common test data used across test cases"""
        # Create test partner
        self.partner = self.env["res.partner"].create({"name": "Test Partner"})

        # Set up profile tag
        self.profile_tag = self._get_or_create_profile_tag()

        # Set up storage backend
        self.backend = self._get_or_create_storage_backend()

    def _get_or_create_profile_tag(self):
        """Get existing profile tag or create new one"""
        profile_tag = self.env["g2p.document.tag"].search([("name", "=", "Profile Image")], limit=1)
        if not profile_tag:
            profile_tag = self.env["g2p.document.tag"].create({"name": "Profile Image"})
        return profile_tag

    def _get_or_create_storage_backend(self):
        """Get existing storage backend or create new one"""
        backend = self.env["storage.backend"].search([("name", "=", "Default S3 Document Store")], limit=1)
        if not backend:
            backend = self.env["storage.backend"].create(
                {"name": "Default S3 Document Store", "backend_type": "s3"}
            )
        return backend

    def test_image_lifecycle(self):
        """Test complete lifecycle of profile image: upload, resize, delete, quality check, replacement"""

        _logger.info("⚡ Starting g2p_profile_image test... Please wait, this may take few minutes. ⏳")
        # Test Case 1: Small Image Upload (< 1MB)
        self._test_small_image_upload()

        # Test Case 2: Image Deletion
        self._test_image_deletion()

        # Test Case 3: Image Quality
        self._test_image_resize_quality()

        _logger.info("✅ g2p_profile_image test completed successfully!✅")

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

        # Calculate dimensions
        target_bytes = target_size_mb * 1024 * 1024
        aspect_ratio = 16 / 9
        base_size = int((target_bytes / 3) ** 0.5)
        width = int(base_size * aspect_ratio)
        height = base_size

        # Generate image
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # # Fill with colors
        for y in range(height):
            for x in range(width):
                draw.point((x, y), fill=random.choice(autumn_colors))

        # Save and adjust size
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG", compress_level=0)
        return img_buffer.getvalue()

    def _test_small_image_upload(self):
        """Test uploading image smaller than 1MB"""
        small_img = self.generate_large_image_binary(0.5)
        small_img_b64 = base64.b64encode(small_img).decode("utf-8")

        self.partner.write({"image_1920": small_img_b64})

        # Verify storage
        self.assertEqual(
            base64.b64decode(self.partner.image_1920), small_img, "Small image should be stored as-is"
        )

        # Verify no S3 storage
        self.assertFalse(
            self.env["storage.file"].search([("registrant_id", "=", self.partner.id)]),
            "No S3 storage for small images",
        )

    def _test_image_deletion(self):
        """Test image deletion functionality"""
        self.partner.write({"image_1920": False})

        # Verify database deletion
        self.assertFalse(self.partner.image_1920, "Image should be removed from database")

        # Verify S3 deletion
        self.assertFalse(
            self.env["storage.file"].search([("registrant_id", "=", self.partner.id)]),
            "S3 file should be deleted",
        )

    def _test_image_resize_quality(self):
        """Test image resize with different quality settings"""
        test_sizes = [0.001, 1.1, 2.0, 4.0, 32]  # MB
        for size in test_sizes:
            img = self.generate_large_image_binary(size)
            resized = G2PImageStorage._resize_image(self, img)
            decoded = base64.b64decode(resized)

            # Verify size
            self.assertLess(len(decoded), 1024 * 1024, f"Image of {size}MB should be resized to < 1MB")

            # Verify image integrity
            Image.open(io.BytesIO(decoded))
