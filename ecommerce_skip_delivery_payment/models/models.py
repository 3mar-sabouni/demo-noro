from odoo import models, fields

class Website(models.Model):
    _inherit = "website"

    checkout_thank_you_message = fields.Text(string="Checkout Thank You Message", 
                                             help="This message will be displayed on the order confirmation page.")
    active = fields.Boolean(default="False" )