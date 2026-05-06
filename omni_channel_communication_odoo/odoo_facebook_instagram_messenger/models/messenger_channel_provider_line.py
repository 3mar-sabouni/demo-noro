from odoo import fields, models


class MessengerChannelProviderLine(models.Model):
    _description = "Messenger Channel Provider Line"
    _name = "messenger.channel.provider.line"

    channel_id = fields.Many2one("discuss.channel", "Channel")
    messenger_provider_id = fields.Many2one("messenger.provider", "Provider")
    partner_id = fields.Many2one("res.partner", "Partner")
