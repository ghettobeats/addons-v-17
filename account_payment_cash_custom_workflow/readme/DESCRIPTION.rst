This module adds the following changes to the workflow of payments:

Journals
--------

1. Add a boolean "Cash Control Journal" to the journals that indicates whether it is a petty cash journal.

Payments
--------

1. Add a boolean "Cash Replenishment" to indicate if it is a Petty Cash Replenishment (it would only be shown if it is Internal Transfer).
2. Add a boolean "Refunded".
3. Add a many2many to relate to other payments.

Custom Workflow When the field Cash Replenishment is active:
------------------------------------------------------------

1. The many2many field of payments is shown to indicate the payments to be refunded.
2. The destination journal only shows journals that are marked as "Cash Control Journal".
3. Fill the Amount field with the total amount of the payments selected to be refunded.
4. When the payment is confirmed the field "Refunded" of payments selected is marked as True.
