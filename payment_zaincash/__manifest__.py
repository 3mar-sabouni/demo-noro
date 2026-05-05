# -*- coding: utf-8 -*-
{
    'name': 'Payment Provider: Zain Cash',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Integration with Zain Cash Payment Gateway',
        'description': """
    Integrate Zain Cash payment gateway in Odoo
    
    To use this module:
    1. For testing: Use provided test credentials
    2. For live: 
       - Register a Zain Cash wallet
       - Email bd@zaincash.iq for live credentials
    
    Credentials needed:
    - Wallet Phone Number (MSISDN)
    - Merchant ID
    - Merchant Secret
    """,
    'author': "Uruk",
    'website': "https://www.urukco.com",
    'category': 'Payment',
    'depends': ['payment', 'payment_transaction_log'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'views/payment_templates.xml',
        'data/payment_provider_data.xml',
        'data/payment_method.xml',
    ],
    "external_dependencies": {
        'python': ['PyJWT']
    },
}
