# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

{
    'name': 'Petty Cash Management, Petty Cash Request, Petty Cash Expense',
    'version': '16.0.1.0',
    'sequence': 1,
    'category': 'Accouting',
    'description':
        """
        This Module add below functionality into odoo

        1.Petty Cash Management
        
        Odoo Petty Cash Management
Efficient Petty Cash System
Petty Cash Handling in Odoo
Odoo Petty Cash Module
Streamlined Petty Cash Management
Petty Cash Workflow in Odoo
Odoo Petty Cash Control
Petty Cash Tracking and Reporting
Odoo Petty Cash Expenses
Petty Cash Reconciliation in Odoo
Odoo Petty Cash Fund Management
Petty Cash Handling Procedures
Odoo Petty Cash Register
Petty Cash Accountability in Odoo
Odoo Petty Cash Expense Management \n


odoo app allow Petty Cash Management, Petty Cash Request, Petty cash expense, Petty Cash Workflow approval process, Petty Cash Request balance, Petty Cash Expense Remaing Balance, Petty Cash due balance, Petty Cash user wise allocation, Cash flow Petty Cash management in odoo

    """,
    'summary': 'odoo app allow Petty Cash Management, Petty Cash Request, Petty cash expense, Petty Cash Workflow approval process, Petty Cash Request balance, Petty Cash Expense Remaing Balance, Petty Cash due balance, Petty Cash user wise allocation, Cash flow Petty Cash management in odoo',
    'depends': ['hr','l10n_do_accounting', 'analytic'],
    'data': ['security/security.xml',
            'security/ir.model.access.csv',
            'data/ez_sequence.xml',
            'views/petty_cash_request_views.xml',
            'views/petty_cash_expense_views.xml',
'report/petty_cash_reports.xml',
'report/petty_cash_templates.xml',
            'views/account_move_views.xml',],
    "external_dependencies": {
            "python": ["python-stdnum"],
        },
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # author and support Details =============#
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',    
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd', 
    'support': 'devintelle@gmail.com',
    'price':14.0,
    'currency':'EUR',
    #'live_test_url':'https://youtu.be/A5kEBboAh_k',
    'license': 'LGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
