import json
import secrets
import string
import time

import requests

from odoo import _, fields, models, api, tools
from odoo.exceptions import UserError


class MessengerProvider(models.Model):
    _name = "messenger.provider"
    _description = "Add Provider to configure the instagram and messenger"

    name = fields.Char("Name", required=True)
    provider = fields.Selection(
        string="Provider",
        required=True,
        selection=[("none", "No Provider Set"), ("graph_api", "Graph API")],
        default="none",
    )
    state = fields.Selection(
        string="State",
        selection=[("disabled", "Disabled"), ("enabled", "Enabled")],
        default="enabled",
        required=True,
        copy=False,
    )
    meta_platform = fields.Selection([('instagram', 'Instagram'),
                                      ('facebook', 'Facebook')], string="Meta Platform", default='facebook')
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
        required=True,
    )

    graph_api_url = fields.Char(string="API URL")
    graph_api_token = fields.Char(string="Token")
    username = fields.Char("Username", readonly=True)
    account_id = fields.Char("Account ID", readonly=True)
    instagram_business_account_id = fields.Char("Instagram Business Account ID", readonly=True)
    graph_api_authentication = fields.Selection(
        [("bearer_token", "Bearer Token")],
        default="bearer_token",
        string="Authentication",
    )
    graph_api_authenticated = fields.Boolean("Authenticated")
    user_id = fields.Many2one(string="User", comodel_name="res.users", default=lambda self: self.env.user)

    is_token_generated = fields.Boolean("Is Token Generated")
    call_back_url = fields.Html(string="Call Back URL & Verify Token")
    user_ids = fields.Many2many('res.users', string='Operators')

    @api.onchange('meta_platform')
    def _onchange_graph_api_url(self):
        if self.meta_platform == 'instagram':
            self.graph_api_url = "https://graph.instagram.com/v20.0/"
        elif self.meta_platform == 'facebook':
            self.graph_api_url = "https://graph.facebook.com/v20.0/"

    def GenerateMessengerVerifyToken(self):
        seconds = time.time()
        unix_time_to_string = str(seconds).split(".")[
            0
        ]  # time.time() generates a float example 1596941668.6601112
        alphaNumeric = string.ascii_uppercase + unix_time_to_string
        alphaNumericlower = string.ascii_lowercase + unix_time_to_string
        firstSet = "".join(secrets.choice(alphaNumeric) for i in range(4))
        secondSet = "".join(secrets.choice(alphaNumeric) for i in range(4))
        thirdSet = "".join(secrets.choice(alphaNumericlower) for i in range(4))
        forthSet = "".join(secrets.choice(alphaNumeric) for i in range(4))
        fifthset = "".join(secrets.choice(alphaNumericlower) for i in range(4))
        token = firstSet + secondSet + thirdSet + forthSet + fifthset
        return token

    def messenger_reload_with_get_status(self):
        if self.graph_api_url and self.graph_api_token:
            url = "%s/me?access_token=%s" % (self.graph_api_url, self.graph_api_token)
            page = requests.get(url)
            page_content = page.json()
            if not page_content.get("error"):
                if self.meta_platform == 'instagram':
                    url = "%s%s?fields=name,username,user_id,followers_count&access_token=%s" % (
                        self.graph_api_url,
                        page_content["id"],
                        self.graph_api_token,
                    )
                else:
                    url = "%s%s?fields=name,username,instagram_business_account,followers_count&access_token=%s" % (
                        self.graph_api_url,
                        page_content["id"],
                        self.graph_api_token,
                    )
                val = requests.get(url)
                content = val.json()
                self.username = content.get("username") if content.get("username") else content.get('name') or ''
                self.account_id = content.get("id") if content.get("id") else ''
                if content.get('instagram_business_account') and content.get('instagram_business_account').get('id'):
                    self.instagram_business_account_id = content.get('instagram_business_account').get('id')
                elif content.get('user_id') and self.meta_platform == 'instagram':
                    self.instagram_business_account_id = content.get('user_id')

            payload = {
                "full": True,
            }
            headers = {}
            try:
                response = requests.request("GET", url, headers=headers, data=payload)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if response.status_code == 200:
                dict = json.loads(response.text)
                if dict["id"] == self.account_id:
                    self.graph_api_authenticated = True

                    IrConfigParam = self.env["ir.config_parameter"].sudo()
                    base_url = IrConfigParam.get_param("web.base.url", False)
                    data = {"webhookUrl": base_url + "/graph_api/webhook"}
                    verify_token = self.GenerateMessengerVerifyToken()
                    self.call_back_url = (
                        '<p>Now, You can set below details to your facebook configurations.</p><p>Call Back URL: <u><a href="%s">%s</a></u></p><p>Verify Token: <u style="color:#017e84">%s</u></p>'
                        % (data.get("webhookUrl"), data.get("webhookUrl"), verify_token)
                    )
                    self.is_token_generated = True
            else:
                self.graph_api_authenticated = False
                self.call_back_url = "<p>Oops, something went wrong, Kindly Double Check the above Credentials. </p>"


    def messenger_send_message(self, recipient, message, quotedMsgId=False):
        t = type(self)
        if self.provider != "none":
            fn = getattr(t, f"{self.provider}_messenger_send_message", None)
            res = fn(self, recipient, message, quotedMsgId)
            return res
        else:
            raise UserError(_("No Provider Set, Please Enable Provider"))

    def graph_api_messenger_send_message(self, recipient, message, quotedMsgId):
        if self.graph_api_authenticated:
            payload = json.dumps(
                {
                    "recipient": {"id": recipient.messenger_account_id},
                    "message": {"text": message},
                    "access_token": self.graph_api_token,
                }
            )
            url = (
                self.graph_api_url
                + self.account_id
                + "/messages?access_token="
                + self.graph_api_token
            )
            headers = {"Content-Type": "application/json"}
            try:
                answer = requests.post(url, data=payload, headers=headers)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if answer.status_code != 200:
                if json.loads(answer.text) and "error" in json.loads(answer.text):
                    if "error_user_msg" in json.loads(answer.text).get(
                        "error"
                    ) and "error_user_title" in json.loads(answer.text).get("error"):
                        dict = (
                            "Title  :  "
                            + json.loads(answer.text)
                            .get("error")
                            .get("error_user_title")
                            + "\nMessage  :  "
                            + json.loads(answer.text).get("error").get("error_user_msg")
                        )
                        raise UserError(_(dict))
                    if "message" in json.loads(answer.text).get("error"):
                        dict = json.loads(answer.text).get("error").get("message")
                        raise UserError(_(dict))
            return answer
        else:
            raise UserError("please authenticated your messenger.")

    def messenger_send_media(self, media_url, recipient, sent_type):
        t = type(self)
        fn = getattr(t, f"{self.provider}_messenger_send_media", None)
        res = fn(self, media_url, recipient, sent_type)
        return res

    def graph_api_messenger_send_media(self, media_url, recipient, sent_type):
        if self.graph_api_authenticated:
            url = self.graph_api_url + self.account_id + "/messages"
            data = {
                "recipient": {"id": recipient.messenger_account_id},
                "message": {
                    "attachment": {
                        "type": sent_type,
                        "payload": {
                            "url": media_url,
                            "is_reusable": True,
                        }

                    }
                }
            }
            payload = json.dumps(data)
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.graph_api_token,
            }
            try:
                answer = requests.post(url, headers=headers, data=payload)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if answer.status_code != 200:
                if json.loads(answer.text) and "error" in json.loads(answer.text):
                    if "error_user_msg" in json.loads(answer.text).get(
                        "error"
                    ) and "error_user_title" in json.loads(answer.text).get("error"):
                        dict = (
                            "Title  :  "
                            + json.loads(answer.text)
                            .get("error")
                            .get("error_user_title")
                            + "\nMessage  :  "
                            + json.loads(answer.text).get("error").get("error_user_msg")
                        )
                        raise UserError(_(dict))
                    if "message" in json.loads(answer.text).get("error"):
                        dict = json.loads(answer.text).get("error").get("message")
                        raise UserError(_(dict))
            return answer
        else:
            raise UserError("please authenticated your messenger.")

    def instagram_send_message(self, recipient, message, quotedMsgId=False):
        t = type(self)
        if self.provider != "none":
            fn = getattr(t, f"{self.provider}_instagram_send_message", None)
            res = fn(self, recipient, message, quotedMsgId)
            return res
        else:
            raise UserError(_("No Provider Set, Please Enable Provider"))

    def graph_api_instagram_send_message(self, recipient, message, quotedMsgId):
        if self.graph_api_authenticated:
            payload = json.dumps(
                {
                    "recipient": {"id": recipient.instagram_account_id},
                    "message": {"text": message},
                    "access_token": self.graph_api_token,
                }
            )
            url = (
                self.graph_api_url
                + self.account_id
                + "/messages?access_token="
                + self.graph_api_token
            )
            headers = {"Content-Type": "application/json"}
            try:
                answer = requests.post(url, data=payload, headers=headers)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if answer.status_code != 200:
                if json.loads(answer.text) and "error" in json.loads(answer.text):
                    if "error_user_msg" in json.loads(answer.text).get(
                        "error"
                    ) and "error_user_title" in json.loads(answer.text).get("error"):
                        dict = (
                            "Title  :  "
                            + json.loads(answer.text)
                            .get("error")
                            .get("error_user_title")
                            + "\nMessage  :  "
                            + json.loads(answer.text).get("error").get("error_user_msg")
                        )
                        raise UserError(_(dict))
                    if "message" in json.loads(answer.text).get("error"):
                        dict = json.loads(answer.text).get("error").get("message")
                        raise UserError(_(dict))
            return answer
        else:
            raise UserError("please authenticated your instagram.")

    def instagram_send_media(self, media_url, recipient, sent_type):
        t = type(self)
        fn = getattr(t, f"{self.provider}_instagram_send_media", None)
        res = fn(self, media_url, recipient, sent_type)
        return res

    def graph_api_instagram_send_media(self, media_url, recipient, sent_type):
        if self.graph_api_authenticated:
            url = self.graph_api_url + self.account_id + "/messages"
            data = {
                "recipient": {"id": recipient.instagram_account_id},
                "message": {
                    "attachment": {"type": sent_type, "payload": {"url": media_url}}
                },
            }
            payload = json.dumps(data)
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.graph_api_token,
            }
            try:
                answer = requests.post(url, headers=headers, data=payload)
            except requests.exceptions.ConnectionError:
                raise UserError("please check your internet connection.")
            if answer.status_code != 200:
                if json.loads(answer.text) and "error" in json.loads(answer.text):
                    if "error_user_msg" in json.loads(answer.text).get(
                        "error"
                    ) and "error_user_title" in json.loads(answer.text).get("error"):
                        dict = (
                            "Title  :  "
                            + json.loads(answer.text)
                            .get("error")
                            .get("error_user_title")
                            + "\nMessage  :  "
                            + json.loads(answer.text).get("error").get("error_user_msg")
                        )
                        raise UserError(_(dict))
                    if "message" in json.loads(answer.text).get("error"):
                        dict = json.loads(answer.text).get("error").get("message")
                        raise UserError(_(dict))
            return answer
        else:
            raise UserError("please authenticated your instagram.")

    def _get_instagram_messenger_channel(self, partner, user, platform=False):
        channel = self.env['discuss.channel'].sudo()
        if not partner or not user:
            return channel
        provider_channel_id = partner.messenger_channel_provider_line_ids.filtered(lambda s: s.messenger_provider_id.id == self.id)
        if provider_channel_id:
            channel |= provider_channel_id.channel_id
        else:
            channel_vals = {
                "im_provider_id": self.id,
                "channel_partner_ids": [(4, partner.id)],
            }
            if platform == 'page':
                channel_vals.update({
                    "channel_type": "FbChannels",
                    "name": partner.messenger_account_id or '',
                    "facebook_channel": True,
                })
            elif platform == 'instagram':
                channel_vals.update({
                    "channel_type": "InstaChannels",
                    "name": partner.instagram_account_id or '',
                    "instagram_channel": True,
                })
            channel |= self.env["discuss.channel"].sudo().create(channel_vals)
            mail_channel_partner = self.env["discuss.channel.member"].sudo().search([
                        ("channel_id", "=", channel.id),
                        ("partner_id", "=", partner.id),
                    ])
            mail_channel_partner.sudo().write({"is_pinned": True})
            channel.sudo().write({"channel_member_ids": [(5, 0, 0)] + [(0, 0, {"partner_id": line_vals}) for line_vals in [partner.id, user.partner_id.id]]})
            partner.sudo().write({
                    "messenger_channel_provider_line_ids": [(0, 0, {
                                "channel_id": channel.id,
                                "messenger_provider_id": self.id,
                            })]
                })
        if channel:
            self._add_insta_messenger_multi_agents(channel)
        return channel

    def _add_insta_messenger_multi_agents(self, channel):
        for rec in self:
            if rec.user_ids:
                for user in rec.user_ids:
                    channel_partner = channel.channel_partner_ids.filtered(lambda x: x.id == user.partner_id.id)
                    if not channel_partner:
                        channel.sudo().write(
                            {'channel_partner_ids': [(4, user.partner_id.id)]})
                    mail_channel_partner = self.env[
                        'discuss.channel.member'].sudo().search(
                        [('channel_id', '=', channel.id),
                         ('partner_id', '=', user.partner_id.id)])
                    if not mail_channel_partner.is_pinned:
                        mail_channel_partner.write({'is_pinned': True})
