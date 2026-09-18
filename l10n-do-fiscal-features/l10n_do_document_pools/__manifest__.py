{
    "name": "NCF Sequence Manager",
    "summary": """
        Allows company to set limit on NCF sequences""",
    "author": "Indexa",
    "website": "https://www.indexa.do",
    "category": "Localization",
    "version": "15.0.0.3.2",
    "depends": ["l10n_do_accounting"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule_data.xml",
        "data/ir_cron_data.xml",
        "data/mail_template_data.xml",
        "wizard/l10n_do_journal_document_type_validate_wizard_views.xml",
        "views/res_config_settings_view.xml",
        "views/account_views.xml",
    ],
    "installable": True,
    "auto_install": False,  # please don't :')
}
