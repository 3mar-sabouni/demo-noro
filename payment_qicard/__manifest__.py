# -*- coding: utf-8 -*-
{
    'name': 'Payment Provider: QiCard',
    'version': '1.0',
    'category': 'Payment',
    'summary': 'QiCard Payment Gateway Integration for Odoo',
    'sequence': 1,
    'author': 'Uruk',
    'website': 'https://www.uruk.com',
    'depends': ['payment', 'payment_transaction_log'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'views/payment_templates.xml',
        'data/payment_provider_data.xml',
        'data/payment_method.xml',
    ],
}
