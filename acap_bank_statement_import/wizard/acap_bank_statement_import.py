import csv
from datetime import datetime as dt

from odoo import models, fields, _


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def import_file(self):
        return super(
            AccountBankStatementImport, self.with_context(skip_csv_check=True)
        ).import_file()

    def _is_acap_file(self, reader_stmt):

        column_headers = {
            0: "FECHA TRANSACCION",
            1: "FECHA ENTRADA",
            2: "NUMERO REFERENCIA",
            3: "DESCRIPCION",
            4: "DESCRIPCION_2",
            5: "DESCRIPCION_3",
            6: "ORIGEN",
            7: "VALOR",
            8: "SALDO",
        }

        # Here we only read the first row
        for row in reader_stmt:
            for i, col in enumerate(row):
                if not col == column_headers[i]:
                    return False
            return True
        return True

    def _parse_file(self, data_file):
        try:
            stmts_vals = []

            with open("/tmp/statement.csv", "w", newline="") as w_file:
                w_file.write(data_file.decode("latin1"))

            with open("/tmp/statement.csv", newline="") as data:
                reader = csv.reader(
                    (x.replace("\0", "") for x in data), delimiter=";", quotechar='"'
                )

                if self._is_acap_file(reader):
                    date_today = fields.Date.context_today(self)
                    current_statement = {
                        "name": _("ACAP %s Bank Statement" % date_today),
                        "transactions": [],
                    }

                    for line in reader:
                        try:
                            account_refer = _("Account Number Reference: ") + line[2]
                            vals = {
                                "date": dt.strptime(line[0], "%Y%m%d"),
                                "payment_ref": line[3],
                                "amount": line[7]
                                if line[6] == "CR"
                                else float(line[7]) * -1,
                                "account_number": False,  # ACAP file format does not provide a valid account number
                                "ref": line[4],
                                "narration": account_refer
                                if str(line[2]) != ""
                                else False,
                            }
                        except IndexError:
                            continue
                        current_statement["date"] = dt.strptime(line[0], "%Y%m%d")
                        current_statement["transactions"].append(vals)

                    stmts_vals.append(current_statement)

                    # ACAP file format does not specify currency code nor account_number
                    return None, None, stmts_vals

                return super(AccountBankStatementImport, self)._parse_file(data_file)

        except csv.Error:
            return super(AccountBankStatementImport, self)._parse_file(data_file)
