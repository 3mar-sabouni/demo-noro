import logging
from odoo import _, fields, models

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    allow_partial_payment = fields.Boolean(string="Allow Partial Payment", default=True)
