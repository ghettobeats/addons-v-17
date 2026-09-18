from datetime import datetime as dt

from odoo import models, fields, _


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _is_bnc_file(self, stmt_line):
        """
        Compare each statement line column length. If not match,
        is not a Banesco file
        """
        stmt_line_list = stmt_line.split(" \n")
        bnc_column_len_map = {
            0: "Estado de Cuentas",
        }

        if stmt_line_list[0] != bnc_column_len_map[0]:
            return False
        return True

    def _parse_file(self, data_file):

        currency_code = False
        account_number = False
        balance_end_real = False
        balance_start = False
        stmts_vals = []

        with open("/tmp/statement.txt", "w") as w_file:
            if data_file.decode("latin1")[-1] == ",":
                w_file.write(data_file.decode("latin1")[: len(data_file) - 1])
            else:
                w_file.write(data_file.decode("latin1"))

        with open("/tmp/statement.txt", "r") as data:

            if self._is_bnc_file(data.readline()):

                data.seek(0)
                date_today = fields.Date.context_today(self)
                current_statement = {
                    "name": _("Bnc %s Bank Statement" % date_today),
                    "transactions": [],
                }
                data_line = []
                reader = data.readlines()
                for line in reader[18:]:
                    line = line.split("  ")

                    if len(data_line) != 4:
                        for data in line:
                            data_line.append(data)
                        if len(data_line) == 4:
                            try:
                                amount = float(data_line[2].replace(",", ""))
                                balance = float(data_line[3].replace(",", ""))
                                if not balance_start:
                                    balance_start = balance - amount
                                    balance_end_real = balance
                                if round(balance_end_real - amount, 2) == balance:
                                    amount = amount * -1
                                balance_end_real = balance
                                vals = {
                                    "date": dt.strptime(data_line[0].replace("\n", ""), "%d/%m/%y"),
                                    "payment_ref": data_line[1].replace("\n", ""),
                                    "amount": amount,
                                    "unique_import_id": False,
                                    "account_number": False,
                                }
                            except IndexError:
                                continue

                            current_statement["date"] = dt.strptime(data_line[0].replace("\n", ""), "%d/%m/%y")
                            current_statement["transactions"].append(vals)
                            data_line = []

                current_statement["balance_end_real"] = balance_end_real
                current_statement["balance_start"] = balance_start
                stmts_vals.append(current_statement)

            if stmts_vals:
                return currency_code, account_number, stmts_vals

        return super(AccountBankStatementImport, self)._parse_file(data_file)
