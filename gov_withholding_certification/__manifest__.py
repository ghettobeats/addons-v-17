{
    "name": "Dominican Government Withholding Certification",
    "summary": """
        Adds release number to Withholding Certification
    """,
    "author": "Indexa",
    "website": "https://www.indexa.do",
    "category": "Uncategorized",
    "version": "15.0.1.0.0",
    "depends": [
        "l10n_do_withholding_certification",
        "l10n_do_gov_purchase",
        "account_check_printing",
    ],
    "data": ["views/report_withholding_cert.xml"],
    "installable": True,
}
