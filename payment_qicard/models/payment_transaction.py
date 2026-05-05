import base64
import logging
import uuid
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
import requests
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from ..utils.error_handler import QiCardErrorHandler
from ..controller.main import QiCardController
from requests.auth import HTTPBasicAuth

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    qicard_payment_id = fields.Char(string="QiCard Payment ID", readonly=True)
    qicard_request_id = fields.Char(string="QiCard Request ID", readonly=True)
    qicard_refund_id = fields.Char(string="QiCard Refund ID", readonly=True)

    def _get_specific_rendering_values(self, processing_values):
        """ Override to return QiCard-specific rendering values. """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'qicard':
            return res

        base_url = self.provider_id.get_base_url().rstrip('/')
        return_url = base_url + QiCardController._return_url
        notification_url = base_url + QiCardController._webhook_url
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        self.write({'qicard_request_id': request_id})

        # Prepare customer info
        partner = self.partner_id
        customer_info = {
            'fullName': partner.display_name or '',
            'email': partner.email or '',
            'phone': partner.phone or '',
            'address': partner.street or '',
            'city': partner.city or '',
            'countryCode': partner.country_id.code or 'IQ',
        }
        provider = self.provider_id

        # Prepare payment request payload
        payload = {
            'requestId': request_id,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'locale': self.env.lang,
            "withoutAuthenticate": False,
            'customerInfo': customer_info,
            'notificationUrl': notification_url,
            'finishPaymentUrl': return_url,
        }

        signature_parts = [
                    self.provider_id.qicard_terminal_id,
                    request_id,
                    self._format_amount_for_currency(self.amount, self.currency_id.name),
                    self.currency_id.name,
                    'true',
                    '-',
                    '-',
                    '-'
                ]
        
        base_url = provider._qicard_get_api_url()
        url = f"{base_url}/payment"

        response = self._qicard_make_request(url, payload, 'POST', signature_parts)
        
        if not response.get('formUrl'):
            raise ValidationError(_('Payment processing failed. Please try again.'))
        
        self.write({'qicard_payment_id': response['paymentId']})
        return {
            'form_url': response['formUrl'],
            'api_url': response['formUrl'],
            'reference': self.reference,
            "withoutAuthenticate": False,
            'amount': response.get('amount'),
            'currency': response.get('currency'),
            'partner': self.partner_id,
            'provider_code': 'qicard',
            'company': self.company_id,
            'provider': self.provider_id,
            'qicard_payment_id': response['paymentId'],
            "qicard_request_id": response['requestId']
        }

    def _format_amount_for_currency(self, amount, currency_code):
        """Format amount with correct decimal places based on currency"""
        if currency_code == 'IQD':
            return f"{float(amount):.3f}"
        else:
            # Default to 2 decimal places for other currencies
            return f"{float(amount):.2f}"

    def _generate_qicard_signature(self, signature_parts=[]):
        """Generate QiCard RSA signature for authentication using YOUR private key"""
        provider = self.provider_id
        
        # signature_string = 222222|6dfc60c1-7c46-4e66-8203-6c5a796e03c3|20000.000|IQD|-|-|-|- 
        signature_string = "|".join(signature_parts)
        
        # Convert to UTF-8 bytes
        signature_bytes = signature_string.encode('utf-8')
        
        # Load YOUR RSA private key
        try:
            if not provider.qicard_my_private_key_pem:
                raise ValidationError(_('RSA private key not configured. Use "Generate Keys" button in provider settings.'))
            
            # Load your private key
            private_key = serialization.load_pem_private_key(
                provider.qicard_my_private_key_pem.encode('utf-8'),
                password=None
            )
            
            # Sign the data using RSA with PKCS1v15 padding and SHA-256
            signature = private_key.sign(
                signature_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Encode signature in Base64
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            
            return signature_b64
            
        except Exception as e:
            raise ValidationError(_('Failed to generate RSA signature: %s') % str(e))

    def _qicard_make_request(self, url, payload, method='POST', signature_parts=[]):
        """Make authenticated request to QiCard API"""
        provider = self.provider_id

        # Generate RSA signature using YOUR private key
        signature = self._generate_qicard_signature(signature_parts)

        basic_auth = (provider.qicard_username, provider.qicard_password)

        # Prepare headers with signature authentication
        headers = {
            'X-Terminal-Id': provider.qicard_terminal_id,
            'X-Signature': signature,
            'Content-Type': 'application/json',
        }

        try:
            if method == 'POST':
                response = requests.post(url, auth=basic_auth, json=payload, headers=headers, timeout=30)
            elif method == 'GET':
                response = requests.get(url, auth=basic_auth, headers=headers, timeout=30)
            else:
                raise ValidationError(_('Unsupported HTTP method: %s') % method)
            
            # Log the raw response for debugging
            response_json = response.json()
            error_info = ''
            
            # Check for error response
            if 'error' in response_json:
                # Handle QiCard API errors
                error_info = QiCardErrorHandler.handle_qicard_error(response_json)

            self._process_notification_data(response_json)
            self.env['payment.transaction.log'].create({
                'transaction_id': self.id,
                'status': response_json.get('status', 'unknown'),
                'raw_response': response.content
            })
            
            response.raise_for_status()
            return response_json
        
        except requests.exceptions.HTTPError as e:
            raise UserError(error_info if error_info else f"HTTP Error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise UserError(f"Request Error: {str(e)}")

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Find the transaction based on QiCard data. """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'qicard' or len(tx) == 1:
            return tx

        reference = notification_data.get('requestId') or notification_data.get('paymentId')
        if not reference:
            raise ValidationError(
                "QiCard: " + _("No transaction reference found in notification data.")
            )
            
        tx = self.search([
            '|',
            ('qicard_request_id', '=', reference),
            ('qicard_payment_id', '=', reference),
            ('provider_code', '=', 'qicard')
        ], limit=1)
        
        if not tx:
            raise ValidationError(
                "QiCard: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Process the transaction based on QiCard data. """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'qicard':
            return
        # Update payment ID if received
        if not self.qicard_payment_id and notification_data.get('paymentId'):
            self.qicard_payment_id = notification_data['paymentId']

        # Handle payment status
        status = notification_data.get('status')
        msg = notification_data.get('message', 'Unknown error')
        if status == 'SUCCESS':
            self._set_done()
        elif status in ('FAILED', 'AUTHENTICATION_FAILED'):
            error_info = QiCardErrorHandler.handle_qicard_error(notification_data)
            self._set_canceled(_('Payment failed: %s') % error_info)
        elif notification_data.get('canceled'):
            self._set_canceled(_('Payment cancelled: %s') % msg)
        elif status == 'ERROR':
            self._set_error(_('Payment Error: %s') % msg)
        else:
            self._set_pending()

    def action_check_transaction_status(self):
        """ Check the status of the transaction """
        if self.provider_code != 'qicard':
            return super(PaymentTransaction, self).action_check_transaction_status()
        
        provider = self.provider_id
        
        # Get the appropriate API URL based on environment
        base_url = provider._qicard_get_api_url()
        url = f"{base_url}/payment/status/by/request/{self.qicard_request_id}"
        request_id = str(uuid.uuid4())
        # For GET requests, we need to create a minimal payload for signature
        payload = {
            "requestId": request_id
        }
        
        signature_parts = [
            self.provider_id.qicard_terminal_id,
            request_id,
            self.qicard_payment_id,
        ]
        try:
            response_json = self._qicard_make_request(url, payload, 'POST', signature_parts)
            self._process_notification_data(response_json)
        
        except Exception as e:
            _logger.error("Error checking transaction status: %s", str(e))
            raise UserError(_("Failed to check transaction status: %s") % str(e))

    def _send_refund_request(self, **kwargs):
        """ Override of payment to refund. """
        refund_tx = super()._send_refund_request(**kwargs)
        if self.provider_code != 'qicard':
            return refund_tx
        
        # refund the money.
        request_id = str(uuid.uuid4())
        refund_tx.write({
            'qicard_payment_id': self.qicard_payment_id,
            'qicard_request_id': request_id,
        })
        
        payload = {
            'requestId': request_id,
            'amount': self._format_amount_for_currency(kwargs.get('amount_to_refund'), self.currency_id.name),
        }
        
        signature_parts = [
            self.provider_id.qicard_terminal_id,
            request_id,
            self._format_amount_for_currency(kwargs.get('amount_to_refund'), self.currency_id.name),
            self.qicard_payment_id
        ]

        provider = refund_tx.provider_id
        base_url = provider._qicard_get_api_url()
        url = f"{base_url}/payment/{self.qicard_payment_id}/refund"
        response = refund_tx._qicard_make_request(url, payload, 'POST', signature_parts)

        if response.get('status', '').lower() != 'success':
            raise UserError(_("Refund failed. Please try again."))
        
        refund_tx.write({
            'qicard_refund_id': response.get('refundId'),
            'is_refund_tx': True
        })

        refund_tx.action_check_transaction_status()

        return refund_tx
    
    def action_cancel_transaction(self):
        if self.provider_code != 'qicard':
            return super(PaymentTransaction, self).action_cancel_transaction()
        
        provider = self.provider_id
        
        # Get the appropriate API URL based on environment
        base_url = provider._qicard_get_api_url()
        url = f"{base_url}/payment/{self.qicard_payment_id}/cancel"
        request_id = str(uuid.uuid4())
        payload = {
            'requestId': request_id,
            'amount': self._format_amount_for_currency(self.amount, self.currency_id.name),
        }
        signature_parts = [
            self.provider_id.qicard_terminal_id,
            request_id,
            self._format_amount_for_currency(self.amount, self.currency_id.name),
            self.qicard_payment_id,
        ]
        
        try:
            response_json = self._qicard_make_request(url, payload, 'POST', signature_parts)
            response_json['message'] = f'Payment cancelled by {self.env.user.name}.'
            self._process_notification_data(response_json)
            
        except Exception as e:
            _logger.error("Error cancelling transaction: %s", str(e))
            raise UserError(_("Failed to cancel transaction: %s") % str(e))