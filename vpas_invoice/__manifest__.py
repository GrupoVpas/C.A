# -*- coding: utf-8 -*-
{
    'name': "VPAS Invoice",

    'summary': """
        invoice and modifications for the vpas company""",

    'description': """
        invoice and modifications for the vpas company
    """,

    'author': "Fabio Tamburini",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'invoicing',
    'version': '16.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/paper_format.xml',
        'views/vpas_report.xml',
        'reports/vpas_invoice.xml',
    ],
}
