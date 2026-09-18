# -*- coding: utf-8 -*-
{
    'name': "Account Sale Commission",

    'summary': """
        Product base commission computation from invoice payments""",

    'author': "Indexa",
    'website': "https://www.indexa.do",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'account',
                'product'],

    # always loaded
    'data': [
        'views/account_views.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/product_demo_data.xml',
        'demo/account_demo_data.xml',
        'demo/company_demo_data.xml',
        'demo/ir_config_parameter_demo_data.xml',
    ],
    'installable': False,
}
