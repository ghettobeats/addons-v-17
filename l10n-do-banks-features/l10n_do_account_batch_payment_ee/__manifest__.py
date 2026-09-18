{
    "name": "Dominican Batch Payment Enterprise",
    "version": "15.0.0.0.0",
    "category": "Accounting",
    "author": "Indexa",
    "website": "https://www.indexa.do",
    "depends": [
        "l10n_do_account_batch_payment_base",
        "account_batch_payment",
    ],
    "data": [
        "views/l10n_do_account_batch_payment_base_views.xml",
        "views/view_batch_payment_form.xml",
        "wizard/l10n_do_account_batch_payment_wizard_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "uninstall_hook": "uninstall_hook",
}
