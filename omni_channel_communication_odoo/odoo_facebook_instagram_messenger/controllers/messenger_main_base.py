import base64
import json

import requests

from odoo import http
from odoo.http import request


class WebHook3(http.Controller):
    _webhook_url = "/graph_api/webhook"
    _meta_fb_url = "/graph_api/webhook"

    @http.route(_webhook_url, type="http", methods=["GET"], auth="public", csrf=False)
    def facebook_webhook(self, **kw):
        if kw.get("hub.verify_token"):
            return kw.get("hub.challenge")

    def _get_messenger_received_attachment(self, message_obj, provider):
        attachment_value = {}
        media_url = message_obj.get("attachments")[0].get("payload").get("url")
        if message_obj.get("attachments")[0].get("type") == 'image':
            attachment_value.update({'name': 'messenger_image',
                                     'type': 'binary',
                                     'mimetype': 'image/jpeg'})
        elif message_obj.get("attachments")[0].get("type") == 'video':
            attachment_value.update({"name": "messenger_video",
                                     "type": "binary",
                                     "mimetype": "video/mp4"})
        elif message_obj.get("attachments")[0].get("type") == 'file':
            attachment_value.update({"name": "messenger_file",
                                     "type": "binary",
                                     "mimetype": "application/pdf"})
        elif message_obj.get("attachments")[0].get("type") == 'audio':
            attachment_value.update({"name": "messenger_audio",
                                     "type": "binary",
                                     "mimetype": "audio/mpeg"})
        if media_url:
            decoded = self.get_media_data(media_url, provider)
            attachment_value.update({'datas': decoded})
            attachment = request.env['ir.attachment'].sudo().create(attachment_value)

            return attachment

    def get_media_data(self, url, provider):
        payload = {}
        headers = {"Authorization": "Bearer " + provider.graph_api_token}
        response = requests.request("GET", url, headers=headers, data=payload)
        decoded = base64.b64encode(response.content)
        return decoded

    @http.route(
        _meta_fb_url, type="json", methods=["GET", "POST"], auth="public", csrf=False
    )
    def messenger_meta_webhook(self, **kw):
        wa_dict = {}

        data = json.loads(request.httprequest.data.decode("utf-8"))
        wa_dict.update({"messages": data.get("messages")})
        if data.get("object") == "instagram":
            provider = request.env["messenger.provider"].sudo().search([("graph_api_authenticated", "=", True), (
                'instagram_business_account_id', '=', data.get('entry')[0].get('id')),
                                                                        ('meta_platform', '=', 'instagram')],
                                                                       limit=1)
            if not provider:
                provider = request.env["messenger.provider"].sudo().search(
                    [("graph_api_authenticated", "=", True),
                     ('instagram_business_account_id', '=', data.get('entry')[0].get('id'))], limit=1)
        else:
            provider = request.env["messenger.provider"].sudo().search(
                [("graph_api_authenticated", "=", True), '|', ("account_id", '=', data.get('entry')[0].get('id')),
                 ('instagram_business_account_id', '=', data.get('entry')[0].get('id'))], limit=1)
        wa_dict.update({"provider": provider})
        if provider.graph_api_authenticated:
            user_partner = provider.user_id.partner_id
            if data.get("entry") and data.get("entry")[0].get("messaging") and data.get("entry")[0].get("messaging")[
                0].get("message"):
                message = data.get("entry")[0].get("messaging")[0].get("message")
                page_id = data.get("entry")[0].get("messaging")[0].get("sender").get("id")
                messages_id = data.get("entry")[0].get("messaging")[0].get("message").get("mid")
            elif data.get("entry") and data.get("entry")[0].get("standby") and data.get("entry")[0].get("standby")[
                0].get("message"):
                message = data.get("entry")[0].get("standby")[0].get("message")
                page_id = data.get("entry")[0].get("standby")[0].get("sender").get("id")
                messages_id = data.get("entry")[0].get('standby')[0].get('message').get('mid')
            else:
                message = False
                page_id = False
                messages_id = False
            if message and page_id and messages_id:
                wa_dict.update({"chat": True})
                partners = False
                if data.get("object") in ["page", "instagram"]:
                    platform = 'instagram' if data.get("object") == 'instagram' else 'messenger'
                    partners = request.env["res.partner"].sudo().search(
                        ['|', ("messenger_account_id", "=", page_id), ("instagram_account_id", "=", page_id)])
                    wa_dict.update({"partners": partners})
                    if not partners:
                        user_conversation_url = "%s%s/conversations?platform=%s&user_id=%s&access_token=%s" % (
                            provider.graph_api_url, provider.account_id, platform, page_id, provider.graph_api_token)
                        user_conversations_requests = requests.get(user_conversation_url)
                        user_conversations_datas = user_conversations_requests.json()
                        if user_conversations_datas.get("data"):
                            messages_url = "%s%s?fields=messages&access_token=%s" % (
                                provider.graph_api_url, user_conversations_datas.get("data")[0].get("id"),
                                provider.graph_api_token,)
                            messages_requests = requests.get(messages_url)
                            messages_datas = messages_requests.json()
                            if messages_datas.get("messages").get("data"):
                                users_messages_url = "%s%s?fields=to,from,message&access_token=%s" % (
                                    provider.graph_api_url, messages_datas.get("messages").get("data")[0].get("id"),
                                    provider.graph_api_token)
                                user_messages_requests = requests.get(users_messages_url)
                                user_messages_datas = user_messages_requests.json()
                                if user_messages_datas.get("to") and user_messages_datas.get("to").get("data")[0].get(
                                        'id') == provider.account_id:
                                    user_name = user_messages_datas.get("from").get("name")
                                    user_account_id = user_messages_datas.get("from").get("id")
                                    user_email = user_messages_datas.get("from").get("email")

                                elif user_messages_datas.get("from") and user_messages_datas.get("from").get(
                                        'id') == provider.account_id:
                                    user_name = user_messages_datas.get("to").get("data")[0].get('name')
                                    user_account_id = user_messages_datas.get("to").get("data")[0].get('id')
                                    user_email = user_messages_datas.get("to").get("data")[0].get('email')
                                elif platform == 'instagram':
                                    user_name = user_messages_datas.get("from").get("username")
                                    user_account_id = user_messages_datas.get("from").get("id")
                                    user_email = user_messages_datas.get("from").get("email")
                                else:
                                    user_name = ""
                                    user_email = ""
                                    user_account_id = ""
                                partners = request.env["res.partner"].sudo().create({
                                    "name": user_name,
                                    "email": user_email,
                                })
                                if data.get("object") == 'page':
                                    partners.sudo().write({
                                        "messenger_account_id": user_account_id
                                    })
                                elif data.get("object") == 'instagram':
                                    partners.sudo().write({
                                        "instagram_account_id": user_account_id
                                    })

                for partner in partners:
                    channel = provider._get_instagram_messenger_channel(partner, provider.user_id, data.get("object"))
                    message_values = {
                        "author_id": partner.id,
                        "email_from": partner.email or "",
                        "model": "discuss.channel",
                        "message_id": messages_id,
                        "message_type": "facebook_msgs",
                        "subtype_id": request.env["ir.model.data"].sudo()._xmlid_to_res_id("mail.mt_comment"),
                        "partner_ids": [(4, partner.id)],
                        "res_id": channel.id,
                        "reply_to": partner.email,
                    }
                    if data.get("object") == 'page':
                        message_values.update({
                            "message_type": "facebook_msgs",
                            "isFbMsgs": True
                        })
                    if data.get("object") == 'instagram':
                        message_values.update({
                            "message_type": "insta_msgs",
                            "isInstaMsgs": True
                        })
                    vals = {
                        "provider_id": provider.id,
                        "author_id": partner.id,
                        "message_id": messages_id,
                        "type": "received",
                        "partner_id": user_partner.id,
                        "account_id": page_id,
                        "attachment_ids": False,
                        "company_id": provider.company_id.id,
                    }
                    if message.get("text"):
                        vals.update({
                            "message": message.get("text"),
                        })
                        message_values.update({
                            "body": message.get("text")
                        })

                    elif message.get("attachments")[0].get("type") in ["image", "video", "file", "audio"]:
                        attachment = self._get_messenger_received_attachment(message, provider)
                        message_values.update({
                            'attachment_ids': [(4, attachment.id)],
                        })
                        vals.update({
                            'attachment_ids': [(4, attachment.id)],
                        })
                    if message.get('reply_to') and message.get('reply_to').get('mid'):
                        parent_id = request.env['mail.message'].sudo().search(
                            [('message_id', '=', message.get('reply_to').get('mid'))])
                        if parent_id:
                            message_values.update({'parent_id': parent_id.id})
                    message = request.env["mail.message"].sudo().with_context({"message": "received"}).create(
                        message_values)
                    channel._broadcast(channel.channel_member_ids.mapped('partner_id').ids)
                    channel._notify_thread(message, message_values)
                    vals.update({'mail_message_id': message.id})
                    if data.get("object") == 'page':
                        request.env["messenger.history"].sudo().with_user(provider.user_id.id).with_context(
                            {'message': 'received'}).create(vals)
                    elif data.get("object") == 'instagram':
                        request.env["instagram.history"].sudo().with_user(provider.user_id.id).with_context(
                            {'message': 'received'}).create(vals)
        return wa_dict
