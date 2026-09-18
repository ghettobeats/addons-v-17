import csv
from datetime import datetime as dt
from dateutil import parser
from odoo import models, fields, _


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _is_apap_file(self, reader_stmt):

        column_headers = {
            0: "TRANSACCIONES",
            1: "CUENTA",
            2: "TITULO CUENTA",
            3: "MONEDA",
            4: "FECHA VALOR",
            5: "DESCRIPCION",
            6: "REFERENCIA TXN.",
            7: "FECHA",
            8: "MONTO",
        }

        # Here we read the first column of the file until the row with the remaining headers
        for i, row in enumerate(reader_stmt):
            if i == 4:
                for j, col in enumerate(row, start=4):
                    # Here we read the row with the remaining headers
                    if not col == column_headers[j]:
                        return False
                return True
            else:
                if not row[0] == column_headers[i]:
                    return False
        return True

    def _parse_file(self, data_file):
        try:
            stmts_vals = []
            account_number = ""

            with open("/tmp/statement.csv", "w", newline="") as w_file:
                w_file.write(data_file.decode("latin1"))

            with open("/tmp/statement.csv", newline="") as data:
                reader = csv.reader(
                    (
                        x.replace("\0", "").replace("ï»¿", "").replace(" :", "")
                        for x in data
                    ),
                    delimiter=",",
                    quotechar='"',
                )

                if self._is_apap_file(reader):
                    date_today = fields.Date.context_today(self)
                    current_statement = {
                        "name": _("APAP %s Bank Statement" % date_today),
                        "transactions": [],
                    }

                    balance_start = False
                    balance_end_real = False

                    for line in reader:
                        if not any(line) or len(line[0]) == 1:
                            continue
                        if "SALDO INICIAL" in line[1]:
                            balance_start = float(str(line[4]).replace(",", ""))
                            continue
                        if "SALDO AL FINAL DEL PERIODO" in line[1]:
                            balance_end_real = float(str(line[4]).replace(",", ""))
                            continue

                        try:
                            date = dt.strptime(line[3], "%d/%m/%Y")
                        except ValueError:
                            # This part of the code converts from "01 JAN 23" to 01/01/2023
                            formated_date = str(parser.parse(line[3]).date()).replace("-", "/")
                            date = dt.strptime(formated_date, "%Y/%m/%d")

                        except:
                            continue

                        try:

                            txn_refer = _("REFERENCE TXN: ") + line[2]
                            vals = {
                                "payment_ref": line[1],
                                "date": date,
                                "amount": float(str(line[4]).replace(",", "")),
                                "unique_import_id": False,
                                "ref": txn_refer
                                if str(line[2]) != "" and str(line[2]) != "0000000000-00000000"
                                else False,
                                "narration": _("Date to Value: ") + line[0],
                            }
                        except IndexError:
                            continue
                        current_statement["transactions"].append(vals)

                    current_statement["balance_start"] = balance_start
                    current_statement["balance_end_real"] = balance_end_real
                    current_statement["date"] = date
                    stmts_vals.append(current_statement)

                    return None, account_number, stmts_vals

                return super(AccountBankStatementImport, self)._parse_file(data_file)

        except csv.Error:
            return super(AccountBankStatementImport, self)._parse_file(data_file)
