# -*- coding: utf-8 -*-
{
    "name": "DGII Reports Enterprise",
    "summary": """
        Set DGII Reports parent menu as Accounting""",
    "author": "Indexa",
    "website": "https://www.indexa.do",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    "category": "Uncategorized",
    "version": "0.1",
    # any module necessary for this one to work correctly
    "depends": ["dgii_reports", "account_accountant"],
    # always loaded
    "data": [
        "data/dgii_report_data.xml",
    ],
    "auto_install": True,
    "installable": True,
}
