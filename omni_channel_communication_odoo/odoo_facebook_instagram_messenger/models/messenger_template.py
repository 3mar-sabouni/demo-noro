from odoo import fields, models


class MessengerTemplates(models.Model):
    _name = "messenger.template"

    def _get_current_user_provider(self):
        # Multi Companies and Multi Providers Code Here
        provider_id = self.env.user.messenger_provider_ids.filtered(
            lambda x: x.company_id == self.env.company
        )
        if provider_id:
            return provider_id[0]
        return False

    name = fields.Char("Name", translate=True, required=True)
    messenger_provider_id = fields.Many2one(
        "messenger.provider", "Provider", default=_get_current_user_provider
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Applies to",
        help="The type of document this template can be used with",
        ondelete="cascade",
    )
    model = fields.Char(
        "Related Document Model",
        related="model_id.model",
        index=True,
        store=True,
        readonly=True,
    )
    body_html = fields.Html(
        "Body", render_engine="qweb", translate=True, prefetch=True, sanitize=False
    )
    state = fields.Selection(
        [
            ("draft", "DRAFT"),
            ("imported", "IMPORTED"),
            ("added", "ADDED TEMPLATE"),
        ],
        string="State",
        default="draft",
    )

    lang = fields.Many2one("res.lang", "Language", required=True)
    template_components_ids = fields.One2many(
        "template.components", "messenger_template_id", "Template Components"
    )
    template_category = fields.Selection(
        [
            ("button_template", "Button template"),
            ("custom_template", "Custom template"),
            ("customer_feedback_template", "Customer Feedback template"),
            ("generic_template", "Generic template"),
            ("media_template", "Media template"),
            ("product_template", "Product template"),
            ("receipt_template", "Receipt template"),
        ],
        string="Template Category",
    )
