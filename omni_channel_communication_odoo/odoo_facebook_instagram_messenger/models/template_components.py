from odoo import fields, models


class TemplateComponents(models.Model):
    _name = "template.components"

    messenger_template_id = fields.Many2one(
        comodel_name="messenger.template", string="Messenger Template"
    )
    type = fields.Selection(
        [("media", "Media"), ("body", "BODY"), ("buttons", "BUTTONS")],
        "Type",
        default="media",
    )

    media_type = fields.Selection(
        [
            ("document", "DOCUMENT"),
            ("video", "VIDEO"),
            ("image", "IMAGE"),
        ],
        "Media Type",
        default="document",
    )
    attachment_ids = fields.Many2many("ir.attachment", string="Attach Document")

    text = fields.Text("Text")

    model_id = fields.Many2one("ir.model")

    button_type = fields.Selection(
        [
            ("none", "None"),
            ("call_to_action", "Call To Action"),
            ("quick_reply", "Quick Reply"),
        ],
        "Button Type",
        default="none",
    )
    template_button_ids = fields.One2many(
        comodel_name="template.buttons",
        inverse_name="messenger_component_id",
        string="Buttons",
    )
