import logging
import pprint
import jwt
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class ZainCashController(http.Controller):
    _return_url = '/payment/zain_cash/return'

    @http.route(
        _return_url, 
        type='http', 
        auth='public', 
        methods=['GET', 'POST'], 
        csrf=False,
        save_session=False
    )
    def zain_cash_return_from_checkout(self, **data):
        """ Process the return from Zain Cash payment form. """
        _logger.info("Handling return from Zain Cash with data:\n%s", pprint.pformat(data))

        # Retrieve the token from URL parameters
        token = data.get('token')
        
        if not token:
            _logger.error("No token received from Zain Cash")
            return request.redirect('/payment/status')

        try:
            # Retrieve Zain Cash provider configuration
            provider = request.env['payment.provider'].sudo().search([
                ('code', '=', 'zain_cash')
            ], limit=1)
            
            if not provider:
                _logger.error("Zain Cash payment provider not found")
                return request.redirect('/payment/status')
            
            # Decode the JWT token using the provider's secret
            decoded_token = jwt.decode(
                token, 
                provider.zain_cash_secret, 
                algorithms=['HS256']
            )
            
            # Convert to dictionary if it's not already
            if not isinstance(decoded_token, dict):
                decoded_token = dict(decoded_token)
            _logger.info(f"Decoded token: {decoded_token}")
            # Extract transaction details
            order_id = decoded_token.get('orderid')
            transaction_id = decoded_token.get('id')
            
            # Find the corresponding payment transaction
            tx_sudo = request.env['payment.transaction'].sudo()
            tx = tx_sudo.search([
                ('zain_cash_transaction_id', '=', transaction_id),
                ('reference', '=', order_id),
                ('provider_code', '=', 'zain_cash')
            ], limit=1)
            
            if not tx:
                _logger.error(f"No transaction found for order {order_id}")
                return request.redirect('/payment/status')
            
            request.env['payment.transaction.log'].create({
                'transaction_id': tx.id,
                'status':  decoded_token.get('status', 'unknown'),
                'raw_response': decoded_token
            })
            # Handle the transaction based on its status
            tx._handle_notification_data('zain_cash', decoded_token)
            
        except jwt.ExpiredSignatureError:
            _logger.error("JWT token has expired")
        except jwt.InvalidTokenError:
            _logger.error("Invalid JWT token")
        except Exception as e:
            _logger.exception("Error processing Zain Cash return: %s", str(e))
        
        # Always redirect to payment status page
        return request.redirect('/payment/status')