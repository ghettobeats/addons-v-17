# -*- coding: utf-8 -*-
{
    'name': "mitur_reports",

    'summary': """
        Formatos de Impresión de Reportes para MITUR
        """,

    'description': """
        Formatos de Impresión de Reportes para el MITUR
    """,

    'author': "Ministerio de Turismo",
    'website': "https://www.mitur.gob.do/",

    'category': 'Customizations',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account_batch_payment','web','hr_expense','contacts'],

    # always loaded
    'data': [
        'views/relacion_pago_personal/custom_header_relacion_pago.xml',
        'views/relacion_pago_personal/footer_relacion_pago_personal.xml',
        'views/relacion_pago_personal/relacion_pago_personal_view.xml',
        'views/relacion_pago_personal/relacion_pago_personal.xml',
        'views/header_footer_mitur.xml',
    ],
}