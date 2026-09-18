import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # moving menus back to account module
    # this is necessary because once you uninstall account_accountant
    # without this hook the menu will remain without parent.
    # hence, appearing as an separate module.
    invoicing_menu = env.ref("account.menu_finance")
    menus_to_move = [
        "odoo_cheque_management.wk_bank_cheque_management_menu",
    ]

    for menu_xmlids in menus_to_move:
        try:
            env.ref(menu_xmlids).parent_id = invoicing_menu
        except ValueError as e:
            _logger.warning(e)
