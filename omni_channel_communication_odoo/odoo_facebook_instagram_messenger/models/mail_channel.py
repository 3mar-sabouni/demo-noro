from odoo import _, api, fields, models, modules, tools, Command
import json
from collections import defaultdict
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.mail.models.discuss.discuss_channel import Channel
from odoo.tools import html2plaintext
from markupsafe import Markup
import re
from odoo.exceptions import UserError
from odoo.addons.mail.models.discuss.discuss_channel_member import ChannelMember
from odoo.addons.mail.tools.discuss import Store

class MailChannel(models.Model):
    _inherit = "discuss.channel"

    channel_type = fields.Selection(
        selection_add=[('FbChannels', 'Facebook Conversation'),
                       ('InstaChannels', 'Instagram Conversation')],
        ondelete={'FbChannels': 'cascade', 'InstaChannels': 'cascade'})
    im_provider_id = fields.Many2one('messenger.provider', string="Insta/Messenger Provider")

    instagram_channel = fields.Boolean(string="Instagram Channel")
    facebook_channel = fields.Boolean(string="Facebook Channel")

    def _to_store(self, store: Store):
        super()._to_store(store)
        for channel in self.filtered(lambda channel: channel.channel_type in ["FbChannels", "InstaChannels"]):
            store.add(channel, {
                "channel_type": channel.channel_type,
                "length": len(channel),
            })


@api.model_create_multi
def create(self, vals_list):
    if self.env.context.get("mail_create_bypass_create_check") is self._bypass_create_check:
        self = self.sudo()
    for vals in vals_list:
        if "channel_id" not in vals:
            raise UserError(
                _(
                    "It appears you're trying to create a channel member, but it seems like you forgot to specify the related channel. "
                    "To move forward, please make sure to provide the necessary channel information."
                )
            )
        channel = self.env["discuss.channel"].browse(vals["channel_id"])
    return super(ChannelMember, self).create(vals_list)

ChannelMember.create = create


class IrAsset(models.Model):
    _inherit = 'ir.asset'

    # def _fill_asset_paths(self, bundle, asset_paths, seen, addons, installed, **assets_params):
    #     super()._fill_asset_paths( bundle, asset_paths, seen, addons, installed, **assets_params)
    #     is_whatsapp_installed = self.env['ir.module.module'].sudo().search(
    #         [('state', '=', 'installed'), ('name', 'in', ['whatsapp_extended', 'tus_meta_wa_discuss'])])
    #     if is_whatsapp_installed and bundle == 'web.assets_backend':
    #         path = self._get_paths('odoo_facebook_instagram_messenger/static/src/xml/AgentsList.xml', installed)
    #         asset_paths.remove(path, bundle)