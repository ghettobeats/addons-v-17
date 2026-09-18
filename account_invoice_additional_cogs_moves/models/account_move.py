# Copyright 2020-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _has_computed_the_cogs_move_lines(self, stock_move, sale_order):
        """Check if the stock move has already the COGS move lines computed
        for the stock move, in an invoice of the sale order."""

        # Retrieve accounts needed to generate the COGS.
        accounts = stock_move.product_id.product_tmpl_id.with_context(
            force_company=stock_move.company_id.id
        ).get_product_accounts(fiscal_pos=self.fiscal_position_id)
        debit_interim_account = accounts["stock_output"]
        credit_expense_account = accounts["expense"]

        move_line_interim_account = sale_order.mapped("invoice_ids.line_ids").filtered(
            lambda line: line.account_id == debit_interim_account
            and line.stock_move_origin_id == stock_move
        )

        move_line_expense_account = sale_order.mapped("invoice_ids.line_ids").filtered(
            lambda line: line.account_id == credit_expense_account
            and line.stock_move_origin_id == stock_move
        )

        return bool(move_line_interim_account and move_line_expense_account)

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        lines_vals_list = super()._stock_account_prepare_anglo_saxon_out_lines_vals()

        for move in self:
            if (
                not move.is_sale_document(include_receipts=True)
                or not move.company_id.anglo_saxon_accounting
            ):
                continue

            sale_orders = move.mapped("invoice_line_ids.sale_line_ids.order_id")
            for sale_order in sale_orders:
                pickings = sale_order.picking_ids.filtered(
                    lambda p: p.picking_type_code == "outgoing" and p.state == "done"
                )
                for picking in pickings:
                    stock_moves = picking.move_lines.filtered(
                        lambda sm: sm.state == "done"
                        and not sm.returned_move_ids.filtered(
                            lambda smr: smr.state == "done"
                        )
                        and (
                            not sm.sale_line_id
                            or sm.sale_line_id.product_id != sm.product_id
                        )
                    )

                    for stock_move in stock_moves.filtered(
                        lambda sm: sm.stock_valuation_layer_ids
                    ):

                        # Filter out lines being not eligible for COGS.
                        if (
                            stock_move.product_id.type != "product"
                            or stock_move.product_id.valuation != "real_time"
                        ):
                            continue

                        # Retrieve accounts needed to generate the COGS.
                        accounts = stock_move.product_id.product_tmpl_id.with_context(
                            force_company=stock_move.company_id.id
                        ).get_product_accounts(fiscal_pos=move.fiscal_position_id)
                        debit_interim_account = accounts["stock_output"]
                        credit_expense_account = accounts["expense"]
                        if not credit_expense_account:
                            if self.type == "out_refund":
                                credit_expense_account = (
                                    self.journal_id.default_credit_account_id
                                )
                            else:  # out_invoice/out_receipt
                                credit_expense_account = (
                                    self.journal_id.default_debit_account_id
                                )
                        if not debit_interim_account or not credit_expense_account:
                            continue

                        if self._has_computed_the_cogs_move_lines(
                            stock_move, sale_order
                        ):
                            continue

                        # Compute accounting fields.
                        sign = -1 if move.type == "out_refund" else 1
                        price_unit = stock_move.stock_valuation_layer_ids[0].unit_cost
                        balance = sign * stock_move.quantity_done * price_unit

                        # Add interim account line.
                        lines_vals_list.append(
                            {
                                "name": "%s: %s" % (picking.name, stock_move.name[:64]),
                                "move_id": move.id,
                                "product_id": stock_move.product_id.id,
                                "product_uom_id": stock_move.product_uom.id,
                                "quantity": stock_move.quantity_done,
                                "price_unit": price_unit,
                                "debit": balance < 0.0 and -balance or 0.0,
                                "credit": balance > 0.0 and balance or 0.0,
                                "account_id": debit_interim_account.id,
                                "exclude_from_invoice_tab": True,
                                "is_anglo_saxon_line": True,
                                "stock_move_origin_id": stock_move.id,
                            }
                        )

                        # Add expense account line.
                        lines_vals_list.append(
                            {
                                "name": "%s: %s" % (picking.name, stock_move.name[:64]),
                                "move_id": move.id,
                                "product_id": stock_move.product_id.id,
                                "product_uom_id": stock_move.product_uom.id,
                                "quantity": stock_move.quantity_done,
                                "price_unit": -price_unit,
                                "debit": balance > 0.0 and balance or 0.0,
                                "credit": balance < 0.0 and -balance or 0.0,
                                "account_id": credit_expense_account.id,
                                "analytic_account_id": (
                                    sale_order.analytic_account_id
                                    and sale_order.analytic_account_id.id
                                ),
                                "exclude_from_invoice_tab": True,
                                "is_anglo_saxon_line": True,
                                "stock_move_origin_id": stock_move.id,
                            }
                        )
        return lines_vals_list
