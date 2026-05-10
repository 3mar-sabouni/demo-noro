from odoo import http, _,fields
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

class WebsiteSaleSkipAddress(WebsiteSale):

    @http.route('/shop/checkout', type='http', auth='public', website=True, sitemap=False, methods=['GET', 'POST'],csrf=False)
    def shop_checkout(self, **post):
        order_sudo = request.website.sale_get_order()

        if not order_sudo or order_sudo.state != 'draft' or not order_sudo.order_line:
            return request.redirect('/shop/cart')

        # Get customer details from URL parameters
        customer_name = post.get('customer_name')
        customer_phone = post.get('customer_phone')
        customer_address = post.get('customer_address')

        checkout_mode = request.website.account_on_checkout

        is_public_user = request.env.user._is_public()

        # =========================
        # Mandatory Login
        # =========================
        if checkout_mode == 'mandatory' and is_public_user:
            return request.redirect('/web/login?redirect=/shop/cart')

        # =========================
        # Logged In User
        # =========================
        if not is_public_user:
            request.env.user.partner_id.write({
                'phone': customer_phone,
                'street': customer_address,
            })

            partner = request.env.user.partner_id

        # =========================
        # Guest Checkout Allowed
        # optional / disabled
        # =========================
        else:
            partner = request.env['res.partner'].sudo().create({
                'name': customer_name,
                'phone': customer_phone,
                'street': customer_address,
            })

        # Assign partner to the order
        order_sudo.write({
            'partner_id': partner.id,
        })

        website_salesperson_id = request.website.salesperson_id.id
        order_sudo.activity_schedule(
            activity_type_id = request.env.ref('mail.mail_activity_data_todo').id,
            user_id= website_salesperson_id,
            note=_("""Order Confirmed by :  "%s"
                   Phone Number : "%s"
                   Address : "%s" """) % (
                    customer_name, 
                    customer_phone, 
                    customer_address
                ), 
            summary=_("Review Order Confirmation Details"),
            date_deadline=fields.Date.today(),
        )

        # Confirm the order
        order_sudo.action_confirm()
        request.website.sale_reset()
        msg =request.website.checkout_thank_you_message
        return request.render("ecommerce_skip_delivery_payment.custom_order_confirmation", {
            'order': order_sudo,
            'thank_you_message': msg
        })
