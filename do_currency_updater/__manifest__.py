
{
    'name': "Gestor de Tasas",
    'version': '14.0.1.1.0',
    'summary': """
        Gestor de tasas.
    """,
    'author': "Kevin Villar, "
              "ThinkWise SRL",
    'license': 'LGPL-3',
    'category': 'Localization',

    # any module necessary for this one to work correctly
    'depends': ['account', 'l10n_do', 'l10n_do_accounting'],

    'data': [

        'views/res_currency_view.xml',
        'views/res_config_settings_views.xml',
        'data/ir_cron_data.xml',
        'views/account_move_views.xml',

    ],
    "installable": True,
}
