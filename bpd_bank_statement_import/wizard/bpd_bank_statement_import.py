from datetime import datetime as dt

from odoo import models, fields, _


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _is_bpd_file(self, stmt_line):
        """
        Compare each statement line column length. If not match,
        is not a BPD file
        """
        stmt_line_list = stmt_line.split(",")

        try:
            stmt_line_list[5] = stmt_line_list[5].rstrip("\n\r").ljust(120)
        except IndexError:
            return False

        if len(stmt_line_list) not in (8, 9):
            return False
        bpd_column_len_map = {
            0: 21,
            1: 10,
            2: 13,
            3: 12,
            4: 2,
            5: 120,
            6: 3,
            7: 13,
            8: 0,
        }
        for i, column in enumerate(stmt_line_list):
            if bpd_column_len_map[i] != len(column.rstrip("\n\r")):
                return False

        return True

    def get_currency_code(self, line_label):
        currency_map = {
            "RD$": "DOP",
            "EUR": "EUR",
            "USD": "USD",
        }
        for k, v in currency_map.items():
            if k in line_label:
                return v
        else:
            return self.env.user.company_id.currency_id.name

    def _parse_file(self, data_file):

        currency_code = False
        account_number = False
        stmts_vals = []

        with open("/tmp/statement.txt", "w") as w_file:
            if data_file.decode("latin1")[-1] == ",":
                w_file.write(data_file.decode("latin1")[: len(data_file) - 1])
            else:
                w_file.write(data_file.decode("latin1"))

        with open("/tmp/statement.txt", "r") as data:

            if self._is_bpd_file(data.readline()):

                data.seek(0)
                date_today = fields.Date.context_today(self)
                current_statement = {
                    "name": _("BPD %s Bank Statement" % date_today),
                    "balance_start": False,  # BPD bank statement do not provide this info
                    "balance_end_real": False,  # BPD bank statement do not provide this info
                    "transactions": [],
                }
                for line in data:
                    line = line.split(",")
                    try:
                        amount = line[3].lstrip("0")
                    except IndexError:
                        # For any reason BPD bank statements could have a linebreak
                        # between lines, causing IndexError error. This try block jump
                        # to the next line if that is the case.
                        continue

                    line_label = line[5]
                    account_number = line[0][-9:]  # bpd accounts must have 9 digits
                    currency_code = self.get_currency_code(line_label)
                    # Retrieving the account number for each transaction
                    # depending based on transaction code
                    transaction_account_number = None
                    if int(line[6]) in (201, 409):
                        # if after removing leading 0s the account still has more
                        # than 7 digits then it's a valid account number
                        if len(line[2].lstrip("0")) >= 7:
                            transaction_account_number = line[2][
                                -9:
                            ]  # bpd accounts must have 9 digits

                    date = dt.strptime(line[1], "%d/%m/%Y")
                    ref = (
                        _("Check Number: %(number)s") % {"number": line[2]}
                        if line[2] and int(line[2]) != 0
                        else ""
                    )
                    current_statement["transactions"].append(
                        {
                            "payment_ref": line[5],
                            "date": date,
                            "amount": amount if line[4] == "CR" else float(amount) * -1,
                            "ref": ref,
                            "account_number": transaction_account_number,
                        }
                    )
                    current_statement["date"] = date

                stmts_vals.append(current_statement)

            if stmts_vals:
                return currency_code, account_number, stmts_vals

        return super(AccountBankStatementImport, self)._parse_file(data_file)
