import csv
from datetime import datetime as dt

from odoo import models, fields, _


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def import_file(self):
        return super(
            AccountBankStatementImport, self.with_context(skip_csv_check=True)
        ).import_file()

    def _is_bsc_file(self, reader_stmt):

        number_column = {0: 6, 1: 6, 2: 1, 3: 2, 4: 4, 5: 0, 6: 6, 7: 3}

        for i, column in enumerate(reader_stmt):
            if i == 8:
                return True
            if len(column) == number_column[i]:
                continue
            else:
                return False
        return True

    def _parse_file(self, data_file):
        try:
            stmts_vals = []

            with open("/tmp/statement.csv", "w", newline="\n") as w_file:
                w_file.write(data_file.decode("latin1"))

            with open("/tmp/statement.csv", newline="\n") as data:
                reader = csv.reader(
                    (x.replace("\0", "") for x in data), delimiter=",", quotechar='"'
                )

                if not self._is_bsc_file(reader):
                    return super(AccountBankStatementImport, self)._parse_file(
                        data_file
                    )

            with open("/tmp/statement.csv", newline="\n") as data:
                reader = csv.reader(
                    (x.replace("\0", "") for x in data), delimiter=",", quotechar='"'
                )

                date_today = fields.Date.context_today(self)
                current_statement = {
                    "name": _("BSC %s Bank Statement" % date_today),
                    "transactions": [],
                }

                for i, line in enumerate(reader):
                    if i > 7:
                        try:
                            vals = {
                                "payment_ref": line[1],
                                "date": dt.strptime(line[0], "%d/%m/%Y"),
                                "amount": float(str(line[2]).replace(",", "")) * -1
                                if line[2]
                                else str(line[3]).replace(",", ""),
                                "unique_import_id": False,  # BSC file format do not provide an unique transaction id
                                "account_number": False,  # The BSC file format does not provide a valid account number
                            }
                        except IndexError:
                            continue
                        current_statement["date"] = dt.strptime(line[0], "%d/%m/%Y")
                        current_statement["transactions"].append(vals)

                stmts_vals.append(current_statement)

                # The BSC file format does not specify currency code nor account_number
                return None, None, stmts_vals

        except csv.Error:
            return super(AccountBankStatementImport, self)._parse_file(data_file)
