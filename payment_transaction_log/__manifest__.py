# -*- coding: utf-8 -*-
{
    'name': 'Payment Transaction History Log',
    'version': '1.0',
    'summary': 'Show the logs of payment transaction',
    'description': "Show the logs of payment transaction, and a scheduled action to auto-cancel pending transactions that have been in that state for more than 1 hour.",
    'author': "Uruk",
    'website': "https://www.urukco.com",
    'category': 'Payment',
    'depends': ['payment'],
    'data': [
        'security/ir.model.access.csv',
        'security/res_group.xml',
        'views/payment_transaction_views.xml',
        'views/payment_transaction_log_views.xml',
        'data/payment_cron.xml',
    ],
}
