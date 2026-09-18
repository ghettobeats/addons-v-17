{
    "name": "Dominican Batch Payment BPD",
    "summary": """
    Banco Popular Payment Batch
        """,
    "version": "15.0.0.0.0",
    "category": "Accounting",
    "author": "Indexa",
    "website": "https://www.indexa.do",
    "depends": [
        "l10n_do_account_batch_payment_base",
    ],
    "demo": ["demo/account_batch_payment_bpd_demo.xml", "demo/res_company_demo.xml"],
    "data": [
        "data/res_currency_data.xml",
        "data/res_bank_data.xml",
        "data/ir_sequence_data.xml",
        "views/res_company_views.xml",
        "views/res_currency_views.xml",
        "wizard/account_batch_payment_bpd_views.xml",
    ],
    "installable": True,
}
