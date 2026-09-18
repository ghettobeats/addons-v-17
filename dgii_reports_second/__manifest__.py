# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2018 José López <jlopez@indexa.do>
# © 2018 Gustavo Valverde <gustavo@iterativo.do>
# © 2018 Eneldo Serrata <eneldo@marcos.do>

{
    'name': "Declaraciones DGII",

    'summary': """
        Este modulo adecua los documentos de ventas y compras con campos computados adicionales
        para poder ejecutar los reportes para enviar a la DGII""",

    'author': "Indexa, SRL, adaptado y mejorado a version 14 por ThinkWise Dominicana",
    'license': 'LGPL-3',
    'category': 'Accounting',
    'version': '14.0.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base','account_accountant','mail', 'l10n_do', 'l10n_do_accounting',
                'smile_advance_payment_base'],

    # always loaded
    'data': [
        'data/invoice_service_type_detail_data.xml',
        'security/ir_rule.xml',
        'views/res_partner_views.xml',
        'views/account_account_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_view.xml',
        'views/dgii_report_views.xml',
        'wizard/dgii_report_regenerate_wizard_views.xml',
        'views/account_tax_views.xml',
        'data/account_tax_types_corrections.xml',
        "views/account_report.xml",
        "views/report_payment_receipt_templates.xml",
        "views/report_cert_tax_daterange_receipt_templates.xml",
        "views/res_company_views.xml",
        "wizard/create_withholding_tax_cert.xml",
        "wizard/account_payment_register_views.xml",
        'security/ir.model.access.csv',
        'wizard/correct_reconciliation_report.xml',
        "views/correct_reconciliation_report_templates.xml",


    ],
'assets': {
        'web.assets_backend': [
            'dgii_reports_second/static/src/js/widget.js',
            '/dgii_reports_second/static/src/css/formularios.css',
            '/dgii_reports_second/static/src/less/dgii_reports.css',


        ],}
}
