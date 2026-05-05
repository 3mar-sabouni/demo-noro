import logging
import requests
import jwt
import time
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('zain_cash', 'Zain Cash')], 
        ondelete={'zain_cash': 'set default'}
    )
    
    zain_cash_msisdn = fields.Char(
        string='Wallet Phone Number', 
        required_if_code='zain_cash', 
        groups='base.group_system'
    )
    zain_cash_merchant_id = fields.Char(
        string='Merchant ID', 
        required_if_code='zain_cash', 
        groups='base.group_system'
    )
    zain_cash_secret = fields.Char(
        string='Merchant Secret', 
        required_if_code='zain_cash', 
        groups='base.group_system'
    )
    zain_cash_test_url = fields.Char(
        string='Test API URL',
        required_if_code='zain_cash',
        groups='base.group_system'
    )
    zain_cash_production_url = fields.Char(
        string='Production API URL',
        required_if_code='zain_cash',
        groups='base.group_system'
    )

    def _get_zain_cash_api_url(self, endpoint):
        """Return the appropriate API URL based on environment"""
        base_url = self.zain_cash_test_url if self.state == 'test' else self.zain_cash_production_url
        return f"{base_url}/{endpoint}"