# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

{
    "name": "Cancel Inventory | Delete Stock Picking | Delete Scrap Order | Delete Stock Moves",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Warehouse",
    "license": "OPL-1",
    "summary": "Stock Cancel, Cancel Inventory, Cancel Stock Picking, Cancel Scrap, Cancel Inventory Picking,Cancel stock moves, Adjustment Cancel,delete inventory,remove inventory cancel stock adjustment remove Inventory adjustment Odoo",
    "description": """This module helps to cancel stock-picking, scrap orders & stock moves. You can also cancel multiple stock-picking,scrap orders & stock moves from the tree view. You can cancel the stock-picking,& scrap orders in 3 ways,

1) Cancel Only: When you cancel the stock-picking,scrap orders then the stock-picking,scrap orders are cancelled and the state is changed to "cancelled".
2) Cancel and Reset to Draft: When you cancel the stock-picking,scrap orders, first stock-picking,scrap orders are cancelled and then reset to the draft state.
3) Cancel and Delete: When you cancel the stock-picking, scrap orders then first the stock-picking,scrap orders are cancelled and then the stock-picking,scrap orders will be deleted.""",
    "version": "15.0.1",
    "depends": [
                "stock",

    ],
    "application": True,
    "data": [
        'security/stock_security.xml',
        'data/server_action_data.xml',
        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
        'views/scrap_views.xml',
    ],
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True,
    "price": 20,
    "currency": "EUR"
}
