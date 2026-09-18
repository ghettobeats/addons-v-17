# -*- coding: utf-8 -*-
{
    'name': "Correspondence Management",
    'summary': """
       Gestionar de correspondencia de Mitur""",
    'description': """
       El Sistema de Gestión de Correspondencia es una solución integral diseñada para optimizar y automatizar el manejo de la correspondencia en una organización. Este sistema permite registrar, clasificar, distribuir y archivar toda la correspondencia entrante y saliente de manera eficiente y segura.
    """,
    'author': "Mitur",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Mitur/Correspondencia',
    'version': '0.1.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'hr', 'contacts'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/correspondence_group_security.xml',
        'views/correspondence_menus.xml',
        'views/correspondence_views.xml',
        'wizard/correspondence_wizard_view.xml',
        'reports/correspondence_delivery_ticket.xml',
        'reports/correspondence_status_report.xml'
    ],
    "application": True,
    # installable
    # auto_install
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

}
