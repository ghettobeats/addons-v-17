import csv
from datetime import datetime as dt

from odoo import models, fields, _


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def import_file(self):
        return super(
            AccountBankStatementImport, self.with_context(skip_csv_check=True)
        ).import_file()

    def _is_blh_file(self, reader_stmt):

        column_headers = {
            0: "Fecha de Posteo",
            1: "Fecha Efectiva",
            2: "No. Cheque",
            3: "No. Referencia",
            4: "Descripción",
            5: "Retiros",
            6: "Depósitos",
            7: "Balance",
        }

        try:
            for r, row in enumerate(reader_stmt[8][:8]):
                if not row == column_headers[r]:
                    return False
        except IndexError:
            return False
        return True

    def _parse_file(self, data_file):
        try:
            with open("/tmp/statement.csv", "w", newline="\n") as w_file:
                w_file.write(data_file.decode("latin1"))

            with open("/tmp/statement.csv", newline="\n") as data:
                reader = csv.reader(
                    (x.replace("\0", "").replace("Ã³", "ó") for x in data),
                    delimiter=",",
                    quotechar='"',
                )
                reader = [line for line in reader]

                if not self._is_blh_file(reader):
                    return super(AccountBankStatementImport, self)._parse_file(
                        data_file
                    )

                stmts_vals = []
                date_today = fields.Date.context_today(self)
                account_number = reader[3][7] if reader[3][7] else None
                current_statement = {
                    "name": _("BLH %s Bank Statement" % date_today),
                    "transactions": [],
                }

                for i, line in enumerate(reader[9:]):
                    try:
                        check_number = _("No. Check: ") + line[2]
                        refer = _("No. Reference: ") + line[3]
                        date = dt.strptime(line[1], "%d/%m/%Y")
                        vals = {
                            "payment_ref": line[4],
                            "date": date,
                            "amount": float(str(line[6]).replace(",", ""))
                            if float(str(line[6]).replace(",", ""))
                            else float(str(line[5]).replace(",", "")) * -1,
                            "account_number": account_number,
                            "ref": refer
                            if str(line[3]) != "" and str(line[3]) != "00000"
                            else False,
                            "narration": check_number
                            if str(line[2]) != "" and str(line[2]) != "00000"
                            else False,
                        }
                        current_statement["date"] = date
                        current_statement["transactions"].append(vals)

                    except (IndexError, ValueError):
                        continue

                stmts_vals.append(current_statement)
                # The BLH file format does not specify currency code
                return None, account_number, stmts_vals

        except csv.Error:
            return super(AccountBankStatementImport, self)._parse_file(data_file)
