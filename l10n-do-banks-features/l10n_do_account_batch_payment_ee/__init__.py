from . import models

from odoo import api, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    menu = env.ref(
        "l10n_do_account_batch_payment_base.l10n_do_account_batch_payment_base_menu"
    )
    menu.write({"active": True})
