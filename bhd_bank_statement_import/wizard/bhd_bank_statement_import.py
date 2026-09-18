import csv
from datetime import datetime as dt

from odoo import models, fields, _


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def import_file(self):
        return super(
            AccountBankStatementImport, self.with_context(skip_csv_check=True)
        ).import_file()

    def _is_bhd_file(self, reader_stmt):

        column_headers = {
            0: "Fecha",
            1: "Referencia",
            2: "Detalle de Transacciones",
            3: "Débitos",
            4: "Créditos",
            5: "Balance",
        }

        # Here we only read the first row
        for row in reader_stmt:
            for i, col in enumerate(row):
                if not col == column_headers[i]:
                    return False
            return True

    def clean_line(self, line):

        first_section = ["", "", ""]
        debit = False
        credit = False
        balance = False

        line_splited = line[0].split('"')
        first_section = line_splited[0].split(",")[:3]

        # when it comes with debit
        if line_splited[2] == ",,":
            debit = line_splited[1]
            balance = line_splited[3]

        # when it comes with credit
        elif line_splited[2] == ",":
            credit = line_splited[1]
            balance = line_splited[3]

        return first_section + [debit, credit, balance]

    def _parse_file(self, data_file):
        try:
            stmts_vals = []

            with open("/tmp/statement.csv", "w", newline="") as w_file:
                w_file.write(data_file.decode("latin1"))

            with open("/tmp/statement.csv", newline="") as data:
                reader = csv.reader(
                    (x.replace("\0", "") for x in data), delimiter=",", quotechar='"'
                )

                if self._is_bhd_file(reader):

                    date_today = fields.Date.context_today(self)
                    current_statement = {
                        "name": _("BHD %s Bank Statement" % date_today),
                        "transactions": [],
                    }

                    for line in reader:
                        # cleans the line if it has quotation marks ("") at the ends
                        if len(line) == 1 and '"' in line[0]:
                            line = self.clean_line(line)
                        try:
                            account_refer = _("Reference account: ") + line[1]
                            vals = {
                                "payment_ref": line[2],
                                "date": dt.strptime(line[0], "%d/%m/%Y"),
                                "amount": float(str(line[3]).replace(",", "")) * -1
                                if line[3]
                                else float(str(line[4]).replace(",", "")),
                                "account_number": False,  # BHD file format does not provide a valid account number
                                "ref": account_refer
                                if int(line[1]) != 0
                                else False,
                            }
                        except (IndexError, ValueError):
                            # ValueError when the last line is read
                            continue
                        current_statement["date"] = dt.strptime(line[0], "%d/%m/%Y")
                        current_statement["transactions"].append(vals)

                    stmts_vals.append(current_statement)

                    # BHD file format does not specify currency code nor account_number
                    return None, None, stmts_vals

                return super(AccountBankStatementImport, self)._parse_file(data_file)

        except csv.Error:
            return super(AccountBankStatementImport, self)._parse_file(data_file)
