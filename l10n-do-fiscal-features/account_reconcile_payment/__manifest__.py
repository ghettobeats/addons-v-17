{
    "name": "Account Reconcile Payment",
    "summary": """
        Reconcile invoice payments from Journal entries""",
    "author": "Indexa",
    "website": "https://www.indexa.do",
    "category": "Accounting",
    "version": "15.0.1.0.1",
    "depends": ["l10n_do_accounting"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_tax_views.xml",
        "views/account_payment_views.xml",
        "views/account_journal_views.xml",
    ],
    "installable": True,
}
