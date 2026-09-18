import datetime
from odoo.http import request
from odoo import http, fields, _
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.mail import _message_post_helper


class PortalAccount(CustomerPortal):
    @http.route(
        ["/my/invoices/<int:invoice_id>"], type="http", auth="public", website=True
    )
    def portal_my_invoice_detail(
        self, invoice_id, access_token=None, report_type=None, download=False, **kw
    ):
        try:
            invoice_sudo = self._document_check_access(
                "account.move", invoice_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=invoice_sudo,
                report_type=report_type,
                report_ref="account.account_invoices",
                download=download,
            )

        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        # Log only once a day
        if invoice_sudo:
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get("view_quote_%s" % invoice_sudo.id)
            if isinstance(session_obj_date, datetime.date):
                session_obj_date = session_obj_date.isoformat()
            if session_obj_date != now and request.env.user.share and access_token:
                request.session["view_quote_%s" % invoice_sudo.id] = now
                body = _("Invoice viewed by customer %s") % invoice_sudo.partner_id.name
                _message_post_helper(
                    "account.move",
                    invoice_sudo.id,
                    body,
                    token=invoice_sudo.access_token,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=invoice_sudo.user_id.sudo().partner_id.ids,
                )

        return super(PortalAccount, self).portal_my_invoice_detail(
            invoice_id,
            access_token,
            report_type,
            download,
            **kw
        )
