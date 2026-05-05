/** @odoo-module **/

import PaymentForm from '@payment/js/payment_form';

PaymentForm.include({
    /**
     * @override method from @payment/js/payment_form
     * @private
     * @return {object} The extended transaction route params.
     */
    _prepareTransactionRouteParams() {
        const transactionRouteParams = this._super(...arguments);
        const inputTag = document.querySelector('#partial_amount')
        if (inputTag) {
            var partialAmountInput = document.querySelector('#partial_amount').value;
            if (partialAmountInput > transactionRouteParams.amount) {
                partialAmountInput = transactionRouteParams.amount;
            }
        } else {
            var partialAmountInput = transactionRouteParams.amount;
        }
        return {...transactionRouteParams, 'amount': partialAmountInput};
    },
    
});

// Full Amount Handler remains the same
window.setFullAmount = function() {
    const $partialAmount = $('#partial_amount');
    $partialAmount.val($partialAmount.attr('max'));
    $partialAmount.trigger('change');
};