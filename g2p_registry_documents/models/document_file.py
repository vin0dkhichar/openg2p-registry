from odoo import api, fields, models


class G2PDocumentRegistry(models.Model):
    _inherit = "storage.file"

    registrant_id = fields.Many2one("res.partner")

    is_encrypted = fields.Boolean(string="Encrypted", default=False)

    @api.model
    def create(self, vals):
        is_encrypt_fields = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("g2p_registry_encryption.encrypt_registry", default=False)
        )
        if is_encrypt_fields:
            vals["is_encrypted"] = True
        return super().create(vals)

    def get_record(self):
        for record in self:
            return {
                "mimetype": record.mimetype,
                "name": record.name,
                "url": record.url if record.url else "#",
            }
