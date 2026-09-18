{
    "name": "Dominican Batch Payment Base",
    "version": "15.0.0.0.0",
    "category": "Accounting",
    "author": "Indexa",
    "website": "https://www.indexa.do",
    "depends": [
        "account",
        "l10n_do_banks",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/l10n_do_account_batch_payment_wizard_views.xml",
        "views/l10n_do_account_batch_payment_base_views.xml",
    ],
    "installable": True,
}
