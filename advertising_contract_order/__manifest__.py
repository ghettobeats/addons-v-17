
{
    'name': "advertising_contract_order",

    'summary': """
        Campos para Ordenes de Compra de Contratos de Publicidad
        """,

    'description': """
        Campos para Ordenes de Compra de Contratos de Publicidad
    """,

    'author': "Ministerio de Turismo",
    'website': "https://www.mitur.gob.do/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '15.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['purchase','stock'],

    # always loaded
    'data': [
        'views/purchase_order_contract_view.xml',
        'views/purchase_order_contract_tree_view.xml',
        'reports/purchase_order_contract_report.xml'
    ],
    
    'installable': True,
    'auto_install': False,
}
