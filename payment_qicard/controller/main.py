import logging
import pprint

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class QiCardController(http.Controller):
    _return_url = '/payment/qicard/return'
    _webhook_url = '/payment/qicard/webhook'

    @http.route(
        _return_url, 
        type='http', 
        auth='public', 
        methods=['GET'], 
    )
    def qicard_return_from_checkout(self, **data):
        """ Process the return from QiCard payment form. """
        try:
            # Find and process the transaction
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'qicard', data
            )

            tx_sudo._process_notification_data(data)
            request.env['payment.transaction.log'].create({
                'transaction_id': tx_sudo.id,
                'status':  data.get('status', 'unknown'),
                'raw_response': data
            })
            tx_sudo._handle_notification_data('qicard', data)
        except ValidationError as e:
            _logger.exception("Unable to handle the return data: %s", str(e))

        # Redirect to the standard payment status page
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def qicard_webhook(self, **data):
        """ Process the webhook notification from QiCard. """        
        try:
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'qicard', data
            )
            tx_sudo._handle_notification_data('qicard', data)
            tx_sudo._process_notification_data(data)
            request.env['payment.transaction.log'].create({
                'transaction_id': tx_sudo.id,
                'status':  data.get('status', 'unknown'),
                'raw_response': data
            })
        except ValidationError as e:
            _logger.exception("Unable to handle the notification data: %s", str(e))
            return {'status': 'error', 'message': str(e)}
        
        return {'status': 'ok'}