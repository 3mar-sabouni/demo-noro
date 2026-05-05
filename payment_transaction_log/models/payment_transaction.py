from datetime import timedelta
import logging
from odoo import fields, models, _, api
_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    is_manager = fields.Boolean(string='Is Manager', compute='_compute_is_manager')


    def _compute_is_manager(self):
        for rec in self:
            rec.is_manager = self.env.user.has_group('payment_transaction_log.group_payment_provider_manager')

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    log_history_ids = fields.One2many(
        'payment.transaction.log',
        'transaction_id',
        string='Log History'
    )
    status_count = fields.Integer(compute='_compute_status_count')
    is_refund_tx = fields.Boolean(readonly=True, default=False)
    pending_since = fields.Datetime(
        string='Pending Since',
        help='The date and time when the transaction entered the pending state',
        readonly=True,
        copy=False
    )

    def _compute_status_count(self):
        for transaction in self:
            transaction.status_count = len(transaction.status_history_ids)


    def action_check_transaction_status(self):
        """ Check the status of the transaction """
        pass
    
    def action_cancel_transaction(self):
        """ Cancel the transaction """
        pass
    
    def _set_pending(self, state_message=None, extra_allowed_states=()):
        """Override to record the timestamp when transaction enters pending state."""
        for tx in self:
            if tx.state != 'pending':  # Only set pending_since if it's a new pending transaction
                tx.pending_since = fields.Datetime.now()
                
        return super()._set_pending(state_message=state_message, extra_allowed_states=extra_allowed_states)
        
    @api.model
    def _auto_cancel_expired_pending_transactions(self):
        """
        Auto-cancel pending transactions that have been in that state for more than 1 hour.
        Called by scheduled action.
        """
        one_hour_ago = fields.Datetime.now() - timedelta(days=2)
        expired_txs = self.search([
            ('state', '=', 'pending'),
            ('is_refund_tx', '=' , False),
            ('pending_since', '<', one_hour_ago),
            ('provider_code', 'in', ['qicard', 'fib', 'zain_cash'])
        ])
        
        if not expired_txs:
            _logger.info("No expired pending transactions found")
            return
            
        _logger.info("Found %s expired pending transactions to cancel", len(expired_txs))
        
        for tx in expired_txs:
            try:
                tx.action_cancel_transaction()
                tx._set_canceled(
                    state_message=_("Automatically canceled: payment remained in pending state for over 1 hour")
                )
                self.env.cr.commit()  # Commit after each transaction to avoid losing progress if one fails
                _logger.info("Canceled expired pending transaction %s (ID: %s)", tx.reference, tx.id)
            except Exception as e:
                self.env.cr.rollback()
                _logger.exception("Failed to cancel expired pending transaction %s (ID: %s): %s", 
                                 tx.reference, tx.id, str(e))
                
        return True
