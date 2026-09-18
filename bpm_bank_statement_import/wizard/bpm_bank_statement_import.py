import xlrd
from datetime import datetime as dt

from odoo import fields, models, _
from odoo.exceptions import UserError

currency_codes = {"DO$": "DOP", "US$": "USD"}


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def get_reader(self, stmt):
        sheet = stmt.sheet_by_index(0)
        reader = []
        for row_idx in range(0, sheet.nrows):
            row = []
            for col_idx in range(0, sheet.ncols):
                cell_obj = sheet.cell(row_idx, col_idx)
                row.append(cell_obj.value)
            reader.append(row)
        return reader

    def _is_bpm_file(self, reader_stmt):

        column_headers = {
            0: "Fecha de Posteo",
            1: "Fecha Efectiva",
            2: "No. Secuencia",
            3: "Código de Transacción",
            4: "No. Referencia",
            5: "Descripción",
            6: "Retiros",
            7: "Depósitos",
            8: "Balance",
        }

        try:
            row = self.get_reader(reader_stmt)[7]
            for c, col in enumerate(row):
                col = col.strip()
                if not col == column_headers[c]:
                    return False
            return True
        except KeyError:
            return False

    def _parse_file(self, data_file):

        # tries to open the file as xls if not delegates the responsibility to another module
        try:

            stmts_vals = []

            with open("/tmp/statement.xls", "wb") as w_file:
                w_file.write(data_file)

            with xlrd.open_workbook("/tmp/statement.xls") as data:
                if self._is_bpm_file(data):

                    try:
                        reader = self.get_reader(data)
                        line = reader[4][0].split("/")
                        account_number = line[1]
                        currency_code = line[2][:3]
                        if currency_code in currency_codes:
                            currency_code = currency_codes[currency_code]
                        else:
                            currency_code = False
                    except IndexError:
                        raise UserError(
                            "Error reading currency code,"
                            "\nFile does not meet BPM statement file structure"
                        )

                    date_today = fields.Date.context_today(self)
                    current_statement = {
                        "name": _("BPM %s Bank Statement" % date_today),
                        "transactions": [],
                    }
                    balance_start = False
                    balance_end_real = False

                    for line in reader[8:]:
                        try:
                            if not balance_start:
                                balance_start = float(line[8])
                                balance_end_real = float(line[8])

                            ref_value = _("No. Reference: %s") % (line[4]) if line[4] and int(line[4]) != 0 else ""
                            date = dt.strptime(line[1], "%d/%m/%Y")

                            vals = {
                                "date": date,
                                "payment_ref": line[5],
                                "ref": ref_value,
                                "narration": _("Transaction Code: %s") % line[3],
                                "amount": float(line[6]) * -1
                                if float(line[6]) > 0
                                else float(line[7]),
                                "unique_import_id": False,
                            }
                        except IndexError:
                            continue
                        except Exception:
                            raise UserError(
                                "Error reading statement values,"
                                "\nFile does not meet BPM statement file structure"
                            )

                        current_statement["date"] = date
                        current_statement["transactions"].append(vals)
                        balance_end_real += vals["amount"]

                    current_statement["balance_start"] = balance_start
                    current_statement["balance_end_real"] = balance_end_real
                    stmts_vals.append(current_statement)

                    return currency_code, account_number, stmts_vals

            return super(AccountBankStatementImport, self)._parse_file(data_file)

        except xlrd.biffh.XLRDError:
            # delegates the responsibility to other module if xls reading fails
            return super(AccountBankStatementImport, self)._parse_file(data_file)
