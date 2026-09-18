# -*- coding: utf-8 -*-
{
    'name': "mitur_check_printing",

    'summary': """
        Formatos de Impresión de Cheques para MITUR
        """,

    'description': """
        Formatos de Impresión de Cheques para el MITUR
    """,

    'author': "Ministerio de Turismo",
    'website': "https://www.mitur.gob.do/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'account_check_printing',
        'l10n_us_check_printing',],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'report/paper_data.xml',
        'report/report_data.xml',
        'report/report_template.xml',
        'views/check_report_config_view.xml',
        'views/account_view.xml'
    ],
    'installable': True,
    'auto_install': False,
}
