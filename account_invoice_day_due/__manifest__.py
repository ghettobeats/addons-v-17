# -*- coding: utf-8 -*-
{
    'name': "Account Invoice Day Due",

    'summary': """
        Compute invoice due days""",

    'author': "Indexa",
    'website': "https://www.indexa.do",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'views/account_invoice_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': False,
}
