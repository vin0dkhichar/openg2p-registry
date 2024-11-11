from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestVCIIssuerRegistryMembership(TransactionCase):
    def setUp(self):
        super().setUp()
