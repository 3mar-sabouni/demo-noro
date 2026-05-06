from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    messenger_provider_id = fields.Many2one(
        "messenger.provider",
        "Messenger Provider",
        domain="[('company_id', 'in', company_ids)]",
    )
    messenger_provider_ids = fields.Many2many(
        "messenger.provider",
        "provider_rel123",
        "provider_id",
        "pid",
        domain="[('company_id', 'in', company_ids)]",
        string="Messenger Providers",
    )
