from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    instagram_account_id = fields.Char("Instagram ID")
    messenger_account_id = fields.Char("Messenger ID")
    messenger_channel_provider_line_ids = fields.One2many(
        "messenger.channel.provider.line",
        "partner_id",
        "Messenger Channel Provider Line",
    )
