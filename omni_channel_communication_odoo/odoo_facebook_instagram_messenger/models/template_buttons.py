from odoo import fields, models


class TemplateButtons(models.Model):
    _name = "template.buttons"

    button_action = fields.Selection(
        [
            ("web_url", "Web Url"),
            ("postback", "Postback"),
            ("phone_number", "Phone Number"),
        ],
        string="Button Action",
    )
    button_text = fields.Char(string="Text")
    website_url = fields.Char(string="Website URL")
    phone_number = fields.Char(string="Phone Number")
    payload = fields.Char(string="Payload")
    messenger_component_id = fields.Many2one(
        comodel_name="template.components", string="Messenger Component"
    )
