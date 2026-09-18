import xlrd
from datetime import datetime as dt
from datetime import timedelta as td

from odoo import fields, models, _
from odoo.exceptions import UserError


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

    def _is_jmmb_file(self, reader_stmt):

        column_headers = {
            0: "",
            1: "NUMERO",
            2: "",
            3: "CODIGO",
            4: "",
            5: "",
            6: "DESCRIPCION",
            7: "",
            8: "",
            9: "FECHA",
            10: "",
            11: "DEBITO",
            12: "CREDITO",
            13: "",
            14: "BALANCE",
        }

        try:
            row = self.get_reader(reader_stmt)[20]
            for c, col in enumerate(row):
                if not col == column_headers[c]:
                    return False
            return True
        except (KeyError, IndexError):
            return False

    def _parse_file(self, data_file):

        # tries to open the file as xls if not delegates the responsibility to another module
        try:

            stmts_vals = []

            with open("/tmp/statement.xls", "wb") as w_file:
                w_file.write(data_file)

            with xlrd.open_workbook("/tmp/statement.xls") as data:
                if self._is_jmmb_file(data):
                    try:
                        reader = self.get_reader(data)
                        acc_line = reader[13][2].split("(")[0].replace("-", "")
                        account_number = acc_line
                        self.env.ref("base.DOP").write(
                            {
                                "active": True,
                            }
                        )
                        currency_code = "DOP"
                    except IndexError:
                        raise UserError(
                            "File does not meet JMMB statement file structure"
                        )

                    act_date = reader[22][2]
                    current_statement = {
                        "name": _("JMMB %s Bank Statement" % act_date),
                        "transactions": [],
                    }
                    balance_start = False
                    balance_end_real = False

                    for line in reader[23:]:
                        if not any(line):
                            continue
                        try:
                            if not balance_start:
                                balance_start = float(line[11])
                                balance_end_real = float(line[11])
                            base_date = dt.strptime("01/01/1900", "%m/%d/%Y")
                            date_line = base_date + td(days=line[6] - 2)
                            vals = {
                                "date": date_line,
                                "payment_ref": str((line[5])),
                                "amount": float(line[8]) * -1
                                if float(line[8]) > 0
                                else float(line[10]),
                                "unique_import_id": False,
                                "account_number": account_number,
                                "ref": _("Transaction Number: ") + str(int(line[1])),
                                "narration": "Code: " + str(line[3]),
                            }

                        except (IndexError, TypeError):
                            continue

                        current_statement["date"] = date_line
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
