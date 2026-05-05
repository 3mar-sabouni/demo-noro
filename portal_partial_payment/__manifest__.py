# -*- coding: utf-8 -*-
{
    'name': 'Portal Partial Payment',
    'version': '1.0',
    'summary': 'Add the functionality to pay partially on the website',
    'description': "Add the functionality to pay partially on the website",
    'author': "Uruk",
    'website': "https://www.urukco.com",
    'category': 'Payment',
    'depends': ['account_payment'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_portal_templates.xml',
        'views/partner_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'portal_partial_payment/static/src/js/payment_form.js'
        ],
    },
}
