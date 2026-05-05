import logging
from odoo import _, fields, models, api
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from odoo.exceptions import ValidationError, UserError
import base64

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('qicard', "QiCard")], 
        ondelete={'qicard': 'set default'}
    )
    qicard_username = fields.Char(
        string="API Username",
        required_if_provider='qicard',
        groups='base.group_user'
    )
    
    qicard_password = fields.Char(
        string="API Password",
        required_if_provider='qicard',
        groups='base.group_user'
    )
    
    qicard_terminal_id = fields.Char(
        string="Terminal ID",
        help="The terminal identifier provided by QiCard",
        required_if_provider='qicard',
        groups='base.group_user'
    )
    
    qicard_my_private_key_pem = fields.Text(
        string="My Private Key (PEM)",
        help="Your RSA private key for signing requests. Keep this secret!",
        groups='base.group_user'
    )
    
    qicard_my_public_key_pem = fields.Text(
        string="My Public Key (PEM)",
        help="Your RSA public key. Send this to QiCard for registration.",
        readonly=True,
        groups='base.group_user'
    )
    
    qicard_pg_public_key_pem = fields.Text(
        string="QiCard Public Key (PEM)",
        help="QiCard's public key from pg_pubkey_sandbox.pem file",
        groups='base.group_user'
    )
    
    qicard_test_url = fields.Char(
        string="Test API URL",
        required_if_provider='qicard',
        groups='base.group_user'
    )
    
    qicard_production_url = fields.Char(
        string="Production API URL",
        required_if_provider='qicard',
        groups='base.group_user'
    )

    def _qicard_get_api_url(self):
        """ Return the API URL according to the provider state. """
        self.ensure_one()
        return self.qicard_test_url if self.state == 'test' else self.qicard_production_url

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'qicard').update({
            'support_refund': 'partial',
        })

    @api.constrains('state', 'code', 'qicard_my_private_key_pem', 'qicard_pg_public_key_pem')
    def _check_qicard_required_fields(self):
        """Validate QiCard required fields when provider is enabled"""
        # Skip validation if we're in key generation context
        if self.env.context.get('skip_qicard_validation'):
            return
            
        for provider in self:
            if provider.code == 'qicard' and provider.state == 'enabled':
                if not provider.qicard_my_private_key_pem:
                    raise ValidationError(_('My Private Key (PEM) is required for QiCard provider. Please generate RSA keys first.'))
                if not provider.qicard_pg_public_key_pem:
                    raise ValidationError(_('QiCard Public Key (PEM) is required for QiCard provider. Please add the content of pg_pubkey_sandbox.pem file.'))

    def action_generate_qicard_keys(self):
        """
        Generate RSA key pair for QiCard integration.
        After running this, you need to send the public key to QiCard for registration.
        """
        self.ensure_one()
        if self.code != 'qicard':
            raise ValidationError(_('This action is only available for QiCard providers.'))
        
        try:
            # Generate RSA-2048 private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Serialize YOUR private key to PEM format (for storage)
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            # Generate YOUR public key from private key
            public_key = private_key.public_key()
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            
            # Store YOUR keys - temporarily disable constraints during write
            self.with_context(skip_qicard_validation=True).write({
                'qicard_my_private_key_pem': private_key_pem,
                'qicard_my_public_key_pem': public_key_pem,
            })
            
        except Exception as e:
            raise ValidationError(_('Failed to generate RSA keys: %s') % str(e))

    def action_test_qicard_config(self):
        """Test QiCard configuration"""
        self.ensure_one()
        if self.code != 'qicard':
            return
        
        errors = []
        
        if not self.qicard_terminal_id:
            errors.append(_('Terminal ID is missing'))
        if not self.qicard_my_private_key_pem:
            errors.append(_('Private key is missing - use "Generate Keys" button'))
        if not self.qicard_pg_public_key_pem:
            errors.append(_('QiCard public key is missing - add content from pg_pubkey_sandbox.pem'))
        if not self.qicard_test_url:
            errors.append(_('Test API URL is missing'))
        
        # Test key format
        if self.qicard_my_private_key_pem:
            try:
                serialization.load_pem_private_key(
                    self.qicard_my_private_key_pem.encode('utf-8'),
                    password=None
                )
            except Exception as e:
                errors.append(_('Invalid private key format: %s') % str(e))
        
        if self.qicard_pg_public_key_pem:
            try:
                serialization.load_pem_public_key(
                    self.qicard_pg_public_key_pem.encode('utf-8')
                )
            except Exception as e:
                errors.append(_('Invalid QiCard public key format: %s') % str(e))
        
        if errors:
            message = _('Configuration errors found:\n') + '\n'.join(errors)
            message_type = 'danger'
        else:
            message = _('QiCard configuration is valid!')
            message_type = 'success'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }

    def verify_qicard_response(self, signature_b64, data):
        """
        Verify QiCard's signature on webhooks/responses using their public key.
        """
        self.ensure_one()
        try:
            if not self.qicard_pg_public_key_pem:
                return False
            
            # Load QiCard's public key
            qicard_public_key = serialization.load_pem_public_key(
                self.qicard_pg_public_key_pem.encode('utf-8')
            )
            
            # Decode the signature
            signature = base64.b64decode(signature_b64)
            
            # Verify the signature
            qicard_public_key.verify(
                signature,
                data.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return True
            
        except Exception as e:
            _logger.warning("QiCard signature verification failed: %s", str(e))
            return False