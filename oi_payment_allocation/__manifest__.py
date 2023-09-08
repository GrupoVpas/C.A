# -*- coding: utf-8 -*-
##############################################################################

{
    'name': 'Advance Payment Allocation / Reconciliation',
    'summary': 'Payment Allocation, Partial Payment Allocation, Payment Distribution, Payment Reconciliation, Partial Payment Distribution, Sales Allocation, Purchase Allocation',
    'version': '16.0.1.2.8',
    'author': 'Openinside',
    'website': "https://www.open-inside.com",
    'category': 'Accounting',
    'description': """
        
    """,
    
    'depends' : ['account'],
    'data': [        
        'views/account_payment_allocation.xml',
        'views/account_partial_reconcile.xml',
        'views/account_full_reconcile.xml',
        'views/account_payment.xml',
        'views/action.xml',
        'views/menu.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    "license": "OPL-1",
    "price" : 69.99,
    "currency": 'USD',
    'odoo-apps' : True,
    'images':[
            'static/description/cover.png'
        ],                  
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
