{
    "name": "Dominican Government Purchase Features",
    "summary": """
    Adds Dominican Republic Government Purchase features
    """,
    "author": "Indexa",
    "website": "https://indexa.do",
    "category": "Accounting",
    "version": "15.0.1.0.0",
    "depends": ["purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order.xml",
        "views/account_journal.xml",
        "views/account_payment.xml",
        "views/res_partner.xml",
        "views/purchase_mode.xml",
        "data/purchase_mode_data.xml",
    ],
    "installable": False,
}
