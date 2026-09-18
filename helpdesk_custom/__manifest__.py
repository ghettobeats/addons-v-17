# -*- coding: utf-8 -*-
{
    'name': "   helpdesk_custom   ",
    'summary': """   Extiende la funcionalidad original de Helpdesk   """,
    'description': """   Module description   """,
    'author': "Mitur",
    'website': "https://mitur.gob.do",
    'category': 'Mitur/',
    'version': '0.1.1',
    'depends': ['base', 'mail', 'helpdesk', 'account', 'hr'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/helpdesk_custom_views.xml',
        'views/helpdesk_custom_stage_view_form.xml'
    ],
    "application": False,
    'demo': [
        'demo/demo.xml',
    ],

}
