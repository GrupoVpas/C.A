# -*- coding: utf-8 -*-
{
    "name": "POS Analytic Account",
    'version': '1.0',
    'author': 'Preway IT Solutions',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'summary': 'This module is allow you to set analytic account on pos orders and journal entries | Analytic Account on pos orders | Analyitc Account on pos journal entries',
    'description': """
This module is allow you to set analytic account on pos orders and journal entries | Analytic Account on pos orders | Analyitc Account on pos journal entries
    """,
    "data" : [
        'views/pos_config.xml',
        'views/pos_order.xml',
    ],
    'price': 10.0,
    'currency': "EUR",
    'application': True,
    'installable': True,
    "license": "LGPL-3",
    "images":["static/description/Banner.png"],
}
