import base64

from odoo import _, api, fields, models, tools


class MessangerComposer(models.TransientModel):
    _name = "instagram.compose.message"
    _description = "Instagram composition wizard"

    @api.model
    def default_get(self, fields):
        result = super(MessangerComposer, self).default_get(fields)
        active_model = False
        active_id = False
        template_domain = [("state", "=", "added")]
        # Multi Companies and Multi Providers Code Here
        if self.env.user:
            provider_id = self.env.user.messenger_provider_ids.filtered(
                lambda x: x.company_id == self.env.company
            )
            if provider_id:
                result["messenger_provider_id"] = provider_id[0].id
                template_domain += [("messenger_provider_id", "=", provider_id[0].id)]

        if "model" in result:
            active_model = result.get("model")
            active_id = result.get("res_id")
        else:
            active_model = self.env.context.get("active_model")
            active_id = self.env.context.get("active_id")
        if active_model:
            record = self.env[active_model].browse(active_id)
            if "template_id" in result:
                template = self.env["messenger.template"].browse(
                    result.get("template_id")
                )
                result["body"] = template._render_field(
                    "body_html", [record.id], compute_lang=True
                )[record.id]
            if active_model == "res.partner":
                result["partner_id"] = record.id
            else:
                if record._fields.get("partner_id"):
                    result["partner_id"] = (
                        record.partner_id and record.partner_id.id or False
                    )
                else:
                    result["partner_id"] = False
            if "report" in self.env.context:
                report = str(self.env.context.get("report"))
                pdf = self.env["ir.actions.report"]._render_qweb_pdf(report, record.id)
                Attachment = self.env["ir.attachment"].sudo()
                b64_pdf = base64.b64encode(pdf[0])
                name = ""
                if active_model == "res.partner":
                    if report == "account_followup.action_report_followup":
                        name = "Followups-%s" % record.id
                elif active_model == "stock.picking":
                    name = (
                        record.state in ("done")
                        and _("Delivery slip - %s") % record.name
                    ) or _("Picking Operations - %s") % record.name
                elif active_model == "account.move":
                    name = (record.state in ("posted") and record.name) or _(
                        "Draft - %s"
                    ) % record.name
                else:
                    name = (
                        record.state in ("draft", "sent")
                        and _("Quotation - %s") % record.name
                    ) or _("Order - %s") % record.name

                name = "%s.pdf" % name
                attac_id = Attachment.search([("name", "=", name)], limit=1)
                if report == "account_followup.action_report_followup":
                    attac_id = Attachment
                if len(attac_id) == 0:
                    attac_id = Attachment.create(
                        {
                            "name": name,
                            "type": "binary",
                            "datas": b64_pdf,
                            "res_model": "instagram.history",
                        }
                    )
                if active_model == "res.partner":
                    result["partner_id"] = record.id
                else:
                    if record._fields.get("partner_id"):
                        result["partner_id"] = record.partner_id.id
                    else:
                        result["partner_id"] = False
                result["attachment_ids"] = [(4, attac_id.id)]
        if active_model or self._context.get("default_model"):
            model = active_model or self._context.get("default_model")
            template_domain += [("model", "=", model)]
        template_ids = self.messenger_template_id.search(template_domain)
        self.domain_template_ids = [(6, 0, template_ids.ids)]
        return result

    body = fields.Html("Contents", default="", sanitize_style=True)
    partner_id = fields.Many2one("res.partner")
    messenger_template_id = fields.Many2one(
        "messenger.template", "Use template", index=True
    )
    domain_template_ids = fields.Many2many(
        comodel_name="messenger.template", string="domain template ids"
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "instagram_compose_message_ir_attachments_rel",
        "instagram_wizard_id",
        "attachment_id",
        "Attachments",
    )
    model = fields.Char("Related Document Model", index=True)
    res_id = fields.Integer("Related Document ID", index=True)
    messenger_provider_id = fields.Many2one("messenger.provider", "Messenger Provider")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    messenger_allowed_provider_ids = fields.Many2many(
        "messenger.provider",
        "Messenger Providers",
        compute="update_messenger_allowed_providers",
    )

    @api.depends("company_id")
    def update_messenger_allowed_providers(self):
        self.messenger_allowed_provider_ids = self.env.user.messenger_provider_ids

    # @api.depends('messenger_provider_id')
    # def compute_message_app(self):
    #     if self.messenger_provider_id.social_media_type == 'instagram':
    #         self.message_app = 'instagram'
    #     if self.messenger_provider_id.social_media_type == 'messenger':
    #         self.message_app = 'facebook'

    @api.onchange("company_id", "messenger_provider_id")
    def onchange_messenger_company_provider(self):
        self.messenger_template_id = False
        self.domain_template_ids = False
        domain = []
        if self._context.get("active_model") or self._context.get("default_model"):
            domain += [
                (
                    "model_id.model",
                    "=",
                    self._context.get("active_model")
                    or self._context.get("default_model"),
                )
            ]
        if self.messenger_provider_id:
            domain += [("messenger_provider_id", "=", self.messenger_provider_id.id)]
        template_ids = self.messenger_template_id.search(domain)
        self.domain_template_ids = [(6, 0, template_ids.ids)]

    @api.onchange("messenger_template_id")
    def onchange_template_id_wrapper(self):
        self.ensure_one()
        if "active_model" in self.env.context:
            active_model = str(self.env.context.get("active_model"))
            active_record = self.env[active_model].browse(
                self.env.context.get("active_id")
            )
            for record in self:
                if record.messenger_template_id:
                    record.body = tools.html2plaintext(
                        record.messenger_template_id.body_html
                    )
                else:
                    record.body = ""
        else:
            active_record = self.env[self.model].browse(self.res_id)
            for record in self:
                if record.messenger_template_id:
                    record.body = record.messenger_template_id._render_field(
                        "body_html", [active_record.id], compute_lang=True
                    )[active_record.id]
                else:
                    record.body = ""

    def send_instagram_message(self):
        if not (self.body or self.messenger_template_id or self.attachment_ids):
            return {}

        active_model = str(self.env.context.get('active_model')) if self.env.context.get('active_model',
                                                                                         False) else self.model
        active_id = self.env.context.get('active_id') if self.env.context.get('active_id', False) else self.res_id
        record = self.env[active_model].browse(active_id)

        # Multi Companies and Multi Providers Code Here
        channel = self.messenger_provider_id._get_instagram_messenger_channel(self.partner_id, self.env.user)

        if channel:
            message_values = {
                'body': tools.html2plaintext(self.body) if self.body else '',
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.user.partner_id.email or '',
                'model': active_model,
                'message_type': 'insta_msgs',
                "isInstaMsgs": True,
                'subtype_id': self.env['ir.model.data'].sudo()._xmlid_to_res_id('mail.mt_comment'),
                'partner_ids': [(4, self.messenger_provider_id.user_id.partner_id.id)],
                'res_id': active_id,
                'reply_to': self.env.user.partner_id.email,
                'attachment_ids': [(4, attac_id.id) for attac_id in self.attachment_ids],
            }
            context_vals = {'provider_id': self.messenger_provider_id}
            if self.messenger_template_id:
                context_vals.update(
                    {'template_send': True, 'messenger_template': self.messenger_template_id, 'active_model_id': active_id,
                     'active_model': active_model, 'partner_id': self._context.get('partner_id') or self.partner_id.id,
                     'attachment_ids': self.attachment_ids})

            mail_message = self.env['mail.message'].sudo().with_context(context_vals).create(
                message_values)
            channel._notify_thread(mail_message, message_values)

