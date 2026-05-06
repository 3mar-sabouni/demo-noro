import logging
import re
from binascii import Error as binascii_error

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError
from odoo.tools.misc import clean_context

_logger = logging.getLogger(__name__)
_image_dataurl = re.compile(
    r'(data:image/[a-z]+?);base64,([a-z0-9+/\n]{3,}=*)\n*([\'"])(?: data-filename="([^"]*)")?',
    re.I,
)
_href_pattern = re.compile(r'<a\s+[^>]*href="([^"]+)"[^>]*>[^<]+</a>')
_pattern = r'<br\s*/?>'


class Message(models.Model):
    _inherit = "mail.message"

    message_type = fields.Selection(
        selection_add=[
            ("insta_msgs", "Instagram Msgs"),
            ("facebook_msgs", "Facebook Msgs"),
        ],
        ondelete={
            "insta_msgs": lambda recs: recs.write({"insta_msgs": "odoo"}),
            "facebook_msgs": lambda recs: recs.write({"facebook_msgs": "odoo"}),
        },
    )
    isFbMsgs = fields.Boolean("FB msgs")
    isInstaMsgs = fields.Boolean("Insta msgs")

    @api.model_create_multi
    def create(self, values_list):
        # Multi Companies and Multi Providers Code Here
        # provider_id = self.env.user.provider_ids.filtered(lambda x: x.company_id == self.env.company)
        provider_id = False
        # if self._context.get('provider_id'):
        #     provider_id = self._context.get('provider_id')
        tracking_values_list = []
        for values in values_list:
            if "email_from" not in values and values.get('message_type') in ['insta_msgs', 'facebook_msgs']:  # needed to compute reply_to

                author_id, email_from = self.env["mail.thread"]._message_compute_author(
                    values.get("author_id"), email_from=None, raise_exception=False
                )
                values["email_from"] = email_from
            if not values.get("message_id"):
                values["message_id"] = self._get_message_id(values)
            if "reply_to" not in values:
                values["reply_to"] = self._get_reply_to(values)
            if (
                "record_name" not in values
                and "default_record_name" not in self.env.context
            ):
                values["record_name"] = self._get_record_name(values)

            if "attachment_ids" not in values:
                values["attachment_ids"] = []
            # extract base64 images
            if "body" in values:
                Attachments = self.env["ir.attachment"].with_context(
                    clean_context(self._context)
                )
                data_to_url = {}

                def base64_to_boundary(match):
                    key = match.group(2)
                    if not data_to_url.get(key):
                        name = (
                            match.group(4)
                            if match.group(4)
                            else "image%s" % len(data_to_url)
                        )
                        try:
                            attachment = Attachments.create(
                                {
                                    "name": name,
                                    "datas": match.group(2),
                                    "res_model": values.get("model"),
                                    "res_id": values.get("res_id"),
                                }
                            )
                        except binascii_error:
                            _logger.warning(
                                "Impossible to create an attachment out of badly formated base64 embedded image. Image has been removed."
                            )
                            return match.group(
                                3
                            )  # group(3) is the url ending single/double quote matched by the regexp
                        else:
                            attachment.generate_access_token()
                            values["attachment_ids"].append((4, attachment.id))
                            data_to_url[key] = [
                                "/web/image/%s?access_token=%s"
                                % (attachment.id, attachment.access_token),
                                name,
                            ]
                    return '%s%s alt="%s"' % (
                        data_to_url[key][0],
                        match.group(3),
                        data_to_url[key][1],
                    )

                values["body"] = _image_dataurl.sub(base64_to_boundary, values["body"] or '')

            # delegate creation of tracking after the create as sudo to avoid access rights issues
            tracking_values_list.append(values.pop("tracking_value_ids", False))

        messages = super(Message, self).create(values_list)

        check_attachment_access = []
        if all(
            isinstance(command, int) or command[0] in (4, 6)
            for values in values_list
            for command in values.get("attachment_ids")
        ):
            for values in values_list:
                for command in values.get("attachment_ids"):
                    if isinstance(command, int):
                        check_attachment_access += [command]
                    elif command[0] == 6:
                        check_attachment_access += command[2]
                    else:  # command[0] == 4:
                        check_attachment_access += [command[1]]
        else:
            check_attachment_access = messages.mapped(
                "attachment_ids"
            ).ids  # fallback on read if any unknow command
        if check_attachment_access:
            self.env["ir.attachment"].browse(check_attachment_access).check(mode="read")

        for message, values, tracking_values_cmd in zip(
            messages, values_list, tracking_values_list
        ):
            if tracking_values_cmd:
                vals_lst = [
                    dict(cmd[2], mail_message_id=message.id)
                    for cmd in tracking_values_cmd
                    if len(cmd) == 3 and cmd[0] == 0
                ]
                other_cmd = [
                    cmd for cmd in tracking_values_cmd if len(cmd) != 3 or cmd[0] != 0
                ]
                if vals_lst:
                    self.env["mail.tracking.value"].sudo().create(vals_lst)
                if other_cmd:
                    message.sudo().write({"tracking_value_ids": tracking_values_cmd})

            if message.is_thread_message(values):
                message._invalidate_documents(values.get("model"), values.get("res_id"))

        if self.env.context:
            for values in values_list:
                if values.get('model') == 'discuss.channel':
                    # channel wise message separation code
                    discuss_channel = self.env['discuss.channel'].browse(values.get('res_id', False))

                    if discuss_channel and discuss_channel._fields.get('facebook_channel'):
                        if discuss_channel.facebook_channel:
                            values["message_type"] = 'facebook_msgs'
                    if discuss_channel and discuss_channel._fields.get('instagram_channel'):
                        if discuss_channel.instagram_channel:
                            values["message_type"] = 'insta_msgs'

                    if discuss_channel and discuss_channel._fields.get('whatsapp_channel'):
                        if discuss_channel.whatsapp_channel:
                            values["message_type"] = 'wa_msgs'
                    # else:
                    #     values["message_type"] = values["message_type"]

                if values.get("message_type") in ["facebook_msgs", "insta_msgs"]:
                    vals = {}
                    user = self.env.user
                    if "user_id" in self.env.context and self.env.context.get(
                        "user_id"
                    ):
                        user = self.env.context.get("user_id")
                    if user.id != self.env.ref("base.public_user").id:
                        if values.get("model") == "discuss.channel":
                            channel_company_line_id = self.env[
                                "messenger.channel.provider.line"
                            ].search([("channel_id", "=", message.res_id)])
                            # phone change to mobile
                            if channel_company_line_id:
                                # social_media_id = channel_company_line_id.partner_id.mobile.social_media_id('+').replace(' ', '')
                                if channel_company_line_id.messenger_provider_id:
                                    provider_id = (
                                        channel_company_line_id.messenger_provider_id
                                    )
                                if re.search(_pattern, values.get('body', '')):
                                    insta_fb_message = re.sub(_pattern, '\n', values.get('body', ''))
                                else:
                                    insta_fb_message = _href_pattern.sub(r'\1', values.get('body', ''))

                                # Multi Companies and Multi Providers Code Here
                                if provider_id:
                                    vals = {
                                        "provider_id": provider_id.id,
                                        "author_id": user.partner_id.id,
                                        "message": insta_fb_message,
                                        "type": "sent",
                                        "partner_id": channel_company_line_id.partner_id.id,
                                        "attachment_ids": values.get("attachment_ids"),
                                        "model": self._context.get(
                                            "active_model", "discuss.channel"
                                        ),
                                        'mail_message_id': message.id,
                                    }
                                    if values.get("message_type") == "facebook_msgs":
                                        vals.update(
                                            {
                                                "account_id": channel_company_line_id.partner_id.messenger_account_id,
                                            }
                                        )
                                    elif values.get("message_type") == "insta_msgs":
                                        vals.update(
                                            {
                                                "account_id": channel_company_line_id.partner_id.instagram_account_id,
                                            }
                                        )
                                    # if 'user_id' in self.env.context and self.env.context.get('user_id'):
                                    #     vals.update({'provider_id': self.env.context.get('user_id').provider_id.id})
                                else:
                                    raise AccessError(_("Please add provider in User!"))

                        else:
                            partner = False
                            data = (
                                self.env[values.get("model")]
                                .sudo()
                                .search_read([("id", "=", int(values.get("res_id")))])
                            )
                            if values.get("model") == "res.partner":
                                partner = self.env["res.partner"].browse(data[0]["id"])
                            elif "partner_id" in data[0]:
                                if data[0]["partner_id"]:
                                    partner = self.env["res.partner"].browse(
                                        data[0]["partner_id"][0]
                                    )
                                else:
                                    raise AccessError(
                                        _(
                                            "Partner must be Required for instagram/messenger message!"
                                        )
                                    )
                            else:
                                raise AccessError(
                                    _(
                                        "Partner must be Required for instagram/messenger message!"
                                    )
                                )

                            if partner:
                                user_partner = user.partner_id
                                provider_id = self.env.context.get('provider_id') if self.env.context.get(
                                    'provider_id') else user.provider_id
                                # Multi Companies and Multi Providers Code Here
                                message_values = {
                                    "body": values.get("body", ""),
                                    "author_id": user_partner.id,
                                    "email_from": user_partner.email or "",
                                    "model": values.get("model"),
                                    "message_type": "comment",
                                    "subtype_id": self.env["ir.model.data"]
                                    .sudo()
                                    ._xmlid_to_res_id("mail.mt_comment"),
                                    # 'channel_ids': [(4, channel.id)],
                                    "partner_ids": [(4, user_partner.id)],
                                    "res_id": values.get("res_id"),
                                    "reply_to": user_partner.email,
                                }

                                if values.get("attachment_ids"):
                                    message_values.update(
                                        {"attachment_ids": values.get("attachment_ids")}
                                    )
                                message_comment = (
                                    self.env["mail.message"]
                                    .sudo()
                                    .create(message_values)
                                )
                                if provider_id:
                                    vals = {
                                        "provider_id": provider_id.id,
                                        "author_id": user.partner_id.id,
                                        "message": values.get("body", ""),
                                        "type": "sent",
                                        "partner_id": partner.id,
                                        "attachment_ids": values.get("attachment_ids"),
                                        "model": self._context.get(
                                            "active_model", "discuss.channel"
                                        ),
                                        'mail_message_id': message.id,
                                    }
                                    if values.get("message_type") == "facebook_msgs":
                                        vals.update(
                                            {
                                                "account_id": partner.messenger_account_id,
                                            }
                                        )
                                    elif values.get("message_type") == "insta_msgs":
                                        vals.update(
                                            {
                                                "account_id": partner.instagram_account_id,
                                            }
                                        )
                                else:
                                    raise AccessError(_("Please add provider in User!"))
                                    # mes.channel_ids = [(4,channel.id)]

                        if "company_id" in self.env.context:
                            vals.update(
                                {"company_id": self.env.context.get("company_id")}
                            )

                        if message.message_id:
                            vals.update({"message_id": values.get("message_id")})

                        if self.env.context.get("whatsapp_application"):
                            if values.get("message_type") == "facebook_msgs":
                                self.env["messenger.history"].sudo().with_context(
                                    {"whatsapp_application": True}
                                ).create(vals)
                            if values.get("message_type") == "insta_msgs":
                                self.env["instagram.history"].sudo().with_context(
                                    {"whatsapp_application": True}
                                ).create(vals)

                        if (
                            message.parent_id
                            and not self.env.context.get("whatsapp_application")
                            and self.env.context.get("message") != "received"
                        ):
                            if values.get("message_type") == "facebook_msgs":
                                self.env["messenger.history"].sudo().with_context(
                                    {
                                        "wa_messsage_id": message,
                                        "message_parent_id": message.parent_id,
                                    }
                                ).create(vals)
                            if values.get("message_type") == "insta_msgs":
                                self.env["instagram.history"].sudo().with_context(
                                    {
                                        "wa_messsage_id": message,
                                        "message_parent_id": message.parent_id,
                                    }
                                ).create(vals)

                        if (
                            not message.parent_id
                            and not self.env.context.get("whatsapp_application")
                            and self.env.context.get("message") != "received"
                            and not self.env.context.get("template_send")
                        ):
                            if values.get("message_type") == "facebook_msgs":
                                self.env["messenger.history"].sudo().with_context(
                                    {"message_id": message}
                                ).create(vals)
                            if values.get("message_type") == "insta_msgs":
                                self.env["instagram.history"].sudo().with_context(
                                    {"message_id": message}
                                ).create(vals)

                        if self.env.context.get("template_send"):
                            dicto = {
                                "wa_messsage_id": message,
                                "template_send": True,
                                "wa_template": self.env.context.get("wa_template"),
                                "attachment_ids": self.env.context.get(
                                    "attachment_ids"
                                ),
                                "active_model_id": self.env.context.get(
                                    "active_model_id"
                                ),
                            }

                            if (
                                "active_model_id_chat_bot" in self.env.context
                                and "active_model_chat_bot" in self.env.context
                            ):
                                dicto.update(
                                    {
                                        "active_model_id_chat_bot": self.env.context.get(
                                            "active_model_id_chat_bot"
                                        ),
                                        "active_model_chat_bot": self.env.context.get(
                                            "active_model_chat_bot"
                                        ),
                                    }
                                )
                            if values.get("message_type") == "facebook_msgs":
                                self.env[
                                    "messenger.history"
                                ].sudo().with_context().create(vals)
                            if values.get("message_type") == "insta_msgs":
                                self.env[
                                    "instagram.history"
                                ].sudo().with_context().create(vals)
        return messages
