import json

from odoo import api, fields, models
from odoo.exceptions import UserError

image_type = [
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/vnd.microsoft.icon",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/tiff",
    "image/webp",
]
document_type = [
    "application/xhtml+xml",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/xml",
    "application/vnd.mozilla.xul+xml",
    "application/zip",
    "application/x-7z-compressed",
    "application/x-abiword",
    "application/x-freearc",
    "application/vnd.amazon.ebook",
    "application/octet-stream",
    "application/x-bzip",
    "application/x-bzip2",
    "application/x-cdf",
    "application/x-csh",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-fontobject",
    "application/epub+zip",
    "application/gzip",
    "application/java-archive",
    "application/json",
    "application/ld+json",
    "application/vnd.apple.installer+xml",
    "application/vnd.oasis.opendocument.presentation",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.text",
    "application/ogg",
    "application/pdf",
    "application/x-httpd-php",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.rar",
    "application/rtf",
    "application/x-sh",
    "application/x-tar",
    "application/vnd.visio",
]
audio_type = [
    "audio/aac",
    "audio/midi",
    "audio/x-midi",
    "audio/mpeg",
    "audio/ogg",
    "audio/opus",
    "audio/wav",
    "audio/webm",
    "audio/3gpp",
    "audio/3gpp2",
]
video_type = [
    "video/x-msvideo",
    "video/mp4",
    "video/mpeg",
    "video/ogg",
    "video/mp2t",
    "video/webm",
    "video/3gpp",
    "video/3gpp2",
]


class MessengerHistory(models.Model):
    _name = "messenger.history"
    _description = "Messenger Message History"

    provider_id = fields.Many2one("messenger.provider", "Provider", readonly=True)
    author_id = fields.Many2one("res.partner", "Author", readonly=True)
    partner_id = fields.Many2one("res.partner", "Recipient", readonly=True)
    account_id = fields.Char("Messenger ID")
    message = fields.Char("Message", readonly=True)
    type = fields.Selection(
        [
            ("in queue", "In queue"),
            ("sent", "Sent"),
            ("delivered", "delivered"),
            ("received", "Received"),
            ("read", "Read"),
            ("fail", "Fail"),
        ],
        string="Type",
        default="in queue",
        readonly=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", string="Attachments", readonly=True
    )
    message_id = fields.Char("Message ID", readonly=True)
    fail_reason = fields.Char("Fail Reason", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )
    date = fields.Datetime("Date", default=fields.Datetime.now, readonly=True)
    model = fields.Char("Related Document Model", index=True, readonly=True)
    active = fields.Boolean("Active", default=True)
    mail_message_id = fields.Many2one('mail.message')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            res = super(MessengerHistory, self).create(vals)

            if res.provider_id and res.partner_id and res.partner_id.messenger_account_id and res.type != 'received':
                if res.message:
                    answer = False
                    if "message_parent_id" in self.env.context:
                        parent_msg = (
                            self.env["mail.message"]
                            .sudo()
                            .search(
                                [
                                    (
                                        "id",
                                        "=",
                                        self.env.context.get(
                                            "message_parent_id"
                                        ).id,
                                    )
                                ]
                            )
                        )
                        answer = res.provider_id.messenger_send_message(
                            res.partner_id,
                            res.message,
                            parent_msg.message_id,
                        )
                    else:
                        answer = res.provider_id.messenger_send_message(
                            res.partner_id, res.message
                        )
                    if answer.status_code == 200:
                        dict = json.loads(answer.text)
                        if (
                            res.provider_id.provider == "graph_api"
                        ):  # if condition for Graph API
                            if dict.get('message_id'):
                                res.message_id = dict.get('message_id')
                                res.mail_message_id.message_id = res.message_id
                        else:
                            if "sent" in dict and dict.get("sent"):
                                res.message_id = dict["id"]
                                if self.env.context.get("wa_messsage_id"):
                                    self.env.context.get(
                                        "wa_messsage_id"
                                    ).wa_message_id = dict["id"]
                            else:
                                if not self.env.context.get("cron"):
                                    if "message" in dict:
                                        raise UserError(dict.get("message"))
                                    if "error" in dict:
                                        raise UserError(
                                            dict.get("error").get("message")
                                        )
                                else:
                                    res.write({"type": "fail"})
                                    if "message" in dict:
                                        res.write(
                                            {"fail_reason": dict.get("message")}
                                        )
                if res.attachment_ids:
                    for attachment_id in res.attachment_ids:
                        if res.provider_id.provider == "chat_api":
                            answer = res.provider_id.send_file(
                                res.partner_id, attachment_id
                            )
                            if answer.status_code == 200:
                                dict = json.loads(answer.text)
                                if "sent" in dict and dict.get("sent"):
                                    res.message_id = dict["id"]
                                    if self.env.context.get("wa_messsage_id"):
                                        self.env.context.get(
                                            "wa_messsage_id"
                                        ).wa_message_id = dict["id"]
                                else:
                                    if not self.env.context.get("cron"):
                                        if "message" in dict:
                                            raise UserError(
                                                dict.get("message")
                                            )
                                        if "error" in dict:
                                            raise UserError(
                                                    dict.get("error").get(
                                                        "message"
                                                    )
                                            )
                                    else:
                                        res.write({"type": "fail"})
                                        if "message" in dict:
                                            res.write(
                                                {
                                                    "fail_reason": dict.get(
                                                        "message"
                                                    )
                                                }
                                            )

                        if res.provider_id.provider == "graph_api":
                            sent_type = False
                            IrConfigParam = self.env[
                                "ir.config_parameter"
                            ].sudo()
                            base_url = IrConfigParam.get_param(
                                "web.base.url", False
                            )
                            if attachment_id.mimetype in image_type:
                                sent_type = "image"
                                media_url = (
                                    base_url
                                    + "/web/image/"
                                    + str(res.attachment_ids.ids[0])
                                    + "/datas"
                                )
                            elif attachment_id.mimetype in document_type:
                                sent_type = "document"
                                media_url = {
                                    "link": base_url
                                    + "/web/content/"
                                    + str(res.attachment_ids.ids[0]),
                                    "filename": self.env["ir.attachment"]
                                    .sudo()
                                    .browse(res.attachment_ids.ids[0])
                                    .name,
                                }
                            elif attachment_id.mimetype in audio_type:
                                sent_type = "audio"
                                media_url = (
                                    base_url
                                    + "/web/content/"
                                    + str(res.attachment_ids[0].id)
                                )
                            elif attachment_id.mimetype in video_type:
                                sent_type = "video"
                                media_url = (
                                    base_url
                                    + "/web/content/"
                                    + str(res.attachment_ids.ids[0])
                                )
                            else:
                                sent_type = "image"
                                media_url = (
                                    base_url
                                    + "/web/image/"
                                    + str(res.attachment_ids[0].id)
                                    + "/datas"
                                )

                            answer = res.provider_id.messenger_send_media(
                                media_url,
                                res.partner_id,
                                sent_type,
                            )
                            if answer.status_code == 200:
                                imagedict = json.loads(answer.text)
                                if imagedict.get('message_id'):
                                    res.message_id = imagedict.get('message_id')
                                    res.mail_message_id.message_id = res.message_id
                                else:
                                    if not self.env.context.get("cron"):
                                        if "messages" in imagedict:
                                            raise UserError(
                                                imagedict.get("message")
                                            )
                                        if "error" in imagedict:
                                            raise UserError(
                                                    imagedict.get("error").get(
                                                        "message"
                                                    )
                                            )
                                    else:
                                        res.write({"type": "fail"})
                                        if "messages" in imagedict:
                                            res.write(
                                                {
                                                    "fail_reason": imagedict.get(
                                                        "message"
                                                    )
                                                }
                                            )
            return res
