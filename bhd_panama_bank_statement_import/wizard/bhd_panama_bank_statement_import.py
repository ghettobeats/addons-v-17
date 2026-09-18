import xlrd
from datetime import datetime as dt

from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _get_bhd_panama_reader(self, stmt):
        sheet = stmt.sheet_by_index(0)
        reader = []
        for row_idx in range(0, sheet.nrows):
            row = []
            for col_idx in range(0, sheet.ncols):
                cell_obj = sheet.cell(row_idx, col_idx)
                row.append(cell_obj.value)
            reader.append(row)
        return reader

    def _is_bhd_panama_file(self, reader_stmt):

        column_headers = {
            0: "",
            1: "",
            2: "",
            3: "",
            4: "",
            5: "",
            6: "",

        }

        try:
            row = self._get_bhd_panama_reader(reader_stmt)[7]
            for c, col in enumerate(row):
                col = col.strip()
                if not col == column_headers[c]:
                    return False
            return True
        except KeyError:
            return False

    def _parse_file(self, data_file):

        # tries to open the file as xlsx if not delegates the responsibility to another module
        try:

            stmts_vals = []

            with open("/tmp/statement.xlsx", "wb") as w_file:
                w_file.write(data_file)

            with xlrd.open_workbook("/tmp/statement.xlsx") as data:
                if self._is_bhd_panama_file(data):

                    reader = self._get_bhd_panama_reader(data)
                    line = reader[2][6].split("/")
                    account_number = line[0]
                    currency_code = False

                    date_today = fields.Date.context_today(self)
                    current_statement = {
                        "name": _("BHD Panama %s Bank Statement" % date_today),
                        "transactions": [],
                    }
                    line = reader[6][6].split("/")
                    balance_start = float(str(line[0]).replace(",", ""))
                    balance_end_real = False

                    for line in reader[11:]:
                        # cleans the line if it has quotation marks ("") at the ends
                        if len(line) == 1 and '"' in line[0]:
                            line = self.clean_line(line)
                        if line[0] != "":
                            try:
                                vals = {
                                    "payment_ref":  line[1],
                                    "date": dt.strptime(line[0], "%d/%m/%Y"),
                                    "amount": float(str(line[4]).replace(",", "")) * -1
                                    if line[4]
                                    else float(str(line[5]).replace(",", "")),
                                    "unique_import_id": False,  # BHD file format do not provide an unique
                                    # transaction id
                                    "account_number": False,  # BHD file format does not provide a valid account number
                                }
                                balance_end_real = line[6]
                            except IndexError:
                                continue
                            except Exception:
                                raise UserError(
                                    "Error reading statement values,"
                                    "\nFile does not meet BHD Panama statement file structure"
                                )
                            current_statement["transactions"].append(vals)

                    current_statement["date"] = dt.strptime(line[0], "%d/%m/%Y")
                    current_statement["balance_start"] = balance_start
                    current_statement["balance_end_real"] = balance_end_real
                    stmts_vals.append(current_statement)

                    return currency_code, account_number, stmts_vals

            return super(AccountBankStatementImport, self)._parse_file(data_file)

        except xlrd.biffh.XLRDError:
            # delegates the responsibility to other module if xlsx reading fails
            return super(AccountBankStatementImport, self)._parse_file(data_file)
