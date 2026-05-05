import logging
import time
import jwt
from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError
import requests

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    zain_cash_transaction_id = fields.Char(string="Zain Cash Transaction ID", readonly=True)
    cron_job_id = fields.Many2one('ir.cron', string='Cron Job', readonly=True)

    def _get_specific_rendering_values(self, processing_values):
        """ Override to return Zain Cash-specific rendering values. """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'zain_cash':
            return res
        
        response = self._zain_cash_create_transaction()
        
        if not response.get('payment_url'):
            _logger.error('Zain Cash payment creation failed: %s', response)
            raise ValidationError(_('Payment processing failed. Please try again.'))
        
        self.write({'zain_cash_transaction_id': response['transaction_id']})
        return {
            'form_url': response['payment_url'],
            'api_url': response['payment_url'],
            'reference': self.reference,
            'amount': self.amount,
            'currency': "IQD",
            'partner': self.partner_id,
            'provider_code': 'zain_cash',
            'company': self.company_id,
            'provider': self.provider_id,
            'zain_cash_transaction_id': response['transaction_id'],
        }
    
    def _zain_cash_prepare_transaction_token(self):
        """Prepare JWT token for Zain Cash transaction initialization"""
        base_url = self.provider_id.get_base_url().rstrip('/')
        return_url = f'{base_url}/payment/zain_cash/return'
        payload = {
            'amount': self.amount,  # Must be in IQD, minimum 250
            'serviceType': f"Odoo Order {self.reference}",
            'msisdn': self.provider_id.zain_cash_msisdn,
            'orderId': self.reference,
            'redirectUrl': return_url,
            'iat': int(time.time()),
            'exp': int(time.time()) + 60 * 60 * 4  # Token valid for 4 hours
        }
        
        # Encode JWT token
        token = jwt.encode(
            payload, 
            self.provider_id.zain_cash_secret, 
            algorithm='HS256'
        )
        return token
    
    def _zain_cash_create_transaction(self):
        """Create a transaction with Zain Cash"""
        try:
            # Prepare JWT token
            token = self._zain_cash_prepare_transaction_token()
            
            # Prepare POST data
            post_data = {
                'token': token,
                'merchantId': self.provider_id.zain_cash_merchant_id,
                'lang': 'ar'  # Default to English
            }
            _logger.info(f"Zain Cash POST data: {post_data}")
            # Send request to Zain Cash
            init_url = self.provider_id._get_zain_cash_api_url('transaction/init')
            response = requests.post(
                init_url, 
                data=post_data, 
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            _logger.info(f"Zain Cash Response: {response.text}")
            response_data = response.json()
            transaction_id = response_data.get('id')

            self.create_status_checker_scheduler()
            self.env['payment.transaction.log'].create({
                'transaction_id': self.id,
                'status':  response_data.get('status', 'unknown'),
                'raw_response': response.content
            })
            self._process_notification_data(response_data)
            if not transaction_id:
                raise ValidationError(response_data.get('err').get('msg'))
            
            # Redirect URL for payment
            payment_url = f"{self.provider_id._get_zain_cash_api_url('transaction/pay')}?id={transaction_id}"
            
            return {
                'transaction_id': transaction_id,
                'payment_url': payment_url
            }
        
        except Exception as e:
            _logger.error(f"Zain Cash Transaction Error: {str(e)}")
            raise ValidationError(_("Error creating Zain Cash transaction: %s") % str(e))
            
    def _handle_notification_data(self, provider_code, data):
        res = super()._handle_notification_data(provider_code, data)
        
        if provider_code == 'zain_cash':
            try:
                self._process_notification_data(data)
            except Exception as e:
                self.env.cr.rollback()
        return res

    def _process_notification_data(self, notification_data):
        """ Process the transaction based on Zain Cash data. """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'zain_cash':
            return
        
        status = notification_data.get('status', '').upper()
        msg = notification_data.get('msg', 'Unknown error') if notification_data.get('msg') else notification_data.get('due', 'Unknown error')

        if status == 'SUCCESS' or status == 'COMPLETED':
            self._set_done()
            self.cron_job_id.active = False
        elif status == 'FAILED':
            if msg == 'incorrect_otp': 
                self._set_canceled(_('Payment failed: Incorrect OPT.'))
            self._set_canceled(_('Payment failed: %s') % msg)
            self.cron_job_id.active = False
        elif status == 'CANCEL': 
            self._set_canceled(_('Payment cancelled: %s') % msg)
            self.cron_job_id.active = False
        else:
            self._set_pending()

    def action_check_transaction_status(self):
        """ Check the status of the transaction """
        super().action_check_transaction_status()
        if self.provider_code != 'zain_cash':
            return
        # Prepare JWT token
        try:
            payload = {
                'id': self.zain_cash_transaction_id,
                'msisdn': self.provider_id.zain_cash_msisdn,
                'iat': int(time.time()),
                'exp': int(time.time()) + 60 * 60 * 4  # Token valid for 4 hours
            }
            
            # Encode JWT token
            token = jwt.encode(
                payload, 
                self.provider_id.zain_cash_secret, 
                algorithm='HS256'
            )
            post_data = {
                    'token': token,
                    'merchantId': self.provider_id.zain_cash_merchant_id,
                    }
            # Send request to Zain Cash
            init_url = self.provider_id._get_zain_cash_api_url('transaction/get')
            response = requests.post(
                init_url,
                data=post_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            json_response = response.json()
            self._process_notification_data(json_response)
            # Create status record
            self.env['payment.transaction.log'].create({
                'transaction_id': self.id,
                'status':  json_response.get('status', 'unknown'),
                'raw_response': response.content
            })


        except Exception as e:
            _logger.error(f"Zain Cash Transaction Status Error: {str(e)}")
            raise ValidationError(_("Error getting status of Zain Cash transaction: %s") % str(e))


    def create_status_checker_scheduler(self):
        """ Create or update the cron job for checking transaction status """
        cron_model = self.env['ir.cron']
        cron_values = {
            'name': f'Check Zain Cash Transaction Status for TX {self.id}',
            'model_id': self.env['ir.model']._get('payment.transaction').id,
            'state': 'code',
            'code': f"model.browse({self.id}).action_check_transaction_status()",
            'interval_number': 10,
            'interval_type': 'minutes',
            # 'numbercall': -1,
            'active': True,
        }
        if self.cron_job_id:
            self.cron_job_id.write(cron_values)
        else:
            cron_job = cron_model.create(cron_values)
            self.cron_job_id = cron_job.id

    @classmethod
    def _log_payment_method_line_creation_error(cls, error):
        """
        Log errors during payment method line creation
        """
        _logger = logging.getLogger(__name__)
        _logger.error(f"Could not create Zain Cash payment method line: {error}")
