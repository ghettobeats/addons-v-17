import csv
from datetime import datetime as dt

from odoo import models, fields, _


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def import_file(self):
        return super(
            AccountBankStatementImport, self.with_context(skip_csv_check=True)
        ).import_file()

    def _is_bdr_file(self, reader_stmt):

        column_headers = {
            0: "Producto",
            1: "Fecha",
            2: "Concepto",
            3: "Id de transacción",
            4: "Débito",
            5: "Crédito",
            6: "Balance",
            7: "Descripción",
            8: "Referencia",
        }

        # Here we only read the first row
        for row in reader_stmt:
            for i, col in enumerate(row[0:9]):
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
                    (x.replace("\0", "").replace("ÿþ", "") for x in data),
                    delimiter=",",
                    quotechar='"',
                )

                if self._is_bdr_file(reader):
                    account_number = None
                    date_today = fields.Date.context_today(self)
                    current_statement = {
                        "name": _("BDR %s Bank Statement" % date_today),
                        "transactions": [],
                    }

                    for line in reader:
                        try:
                            date = dt.strptime(line[1], "%d/%m/%Y")
                        except ValueError:
                            splited_date = line[1].split("/")
                            day = splited_date[0]
                            month = splited_date[1]
                            year = splited_date[2]
                            full_date = day.zfill(2) + "/" + month.zfill(2) + "/" + year
                            date = dt.strptime(full_date, "%d/%m/%y")
                        except:
                            continue

                        amount = (
                            float(str(line[4]).replace(",", "")) * -1
                            if float(line[4].replace(",", ""))
                            else float(str(line[5]).replace(",", ""))
                        )

                        account_number = line[0]
                        try:
                            refer = "Reference:  " + line[8]
                            vals = {
                                "payment_ref": line[2],
                                "date": date,
                                "amount": amount,
                                "account_number": account_number,
                                "ref": line[7],
                                "narration": refer
                                if int(line[8]) != 0
                                else False,
                            }
                        except IndexError:
                            continue
                        current_statement["transactions"].append(vals)
                        current_statement["date"] = date

                    stmts_vals.append(current_statement)

                    # BDR file format does not specify currency code
                    return None, account_number, stmts_vals

                return super(AccountBankStatementImport, self)._parse_file(data_file)

        except csv.Error:
            return super(AccountBankStatementImport, self)._parse_file(data_file)
