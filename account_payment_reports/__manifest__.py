{
    'name': 'Reporte de cuentas de pagos',
    'version': '1.0',
    'category': 'Accounting/',
    'summary': '',
    'depends': ['base', 'mail', 'account_accountant'],
    'data':
        ['reports/batch_payment_report.xml',
         'reports/cash_delivery_authorization_report.xml',
         'reports/office_benefits_report.xml',
         'reports/proof_of_delivery_of_funds_report.xml',
         'reports/summary_petty_cash_replenishment_report.xml',
         'reports/cash_delivery_authorization_transfer_report.xml',
         'reports/transfer_authorization_report.xml',
         'views/account_move.xml'],
    'auto_install': False,
    'license': 'OEEL-1',
}
