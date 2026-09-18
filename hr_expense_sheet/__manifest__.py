{
    'name': 'Hr Expense Sheet',
    'version': '1.0',
    'category': 'Human Resources/Expenses',
    'summary': '',
    'depends': ['base', 'mail', 'hr', 'hr_expense'],
    'data':
        [   'reports/hr_expenses_report_viaticos.xml',
            'data/email_templates.xml',
            'views/hr_expenses_sheet_views.xml',

        ],
    'auto_install': True,
    'license': 'OEEL-1',
}
