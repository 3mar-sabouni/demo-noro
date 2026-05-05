import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.CheckoutValidation = publicWidget.Widget.extend({
    selector: 'a[name="order_confirm"]',
    events: {
        'click': '_onCheckoutClick',
    },

    _onCheckoutClick: function (event) {
        const name = document.getElementById('customer_name').value;
        const phone = document.getElementById('customer_phone').value;
        const address = document.getElementById('customer_address').value;
    
        if (name && phone && address) {
            // Redirect with URL parameters
            const url = `/shop/checkout?customer_name=${encodeURIComponent(name)}&customer_phone=${encodeURIComponent(phone)}&customer_address=${encodeURIComponent(address)}`;
            window.location.href = url;
        } else {
            alert("Please fill in all required fields.");
        }
    },
});
