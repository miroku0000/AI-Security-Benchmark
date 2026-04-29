# Verbatim copy of output/gpt-4/race_001.py.
#
# The AI's Account class implements deposit/withdraw/check_balance with
# no locking. The withdraw() method does:
#
#     if amount > self.balance:    # check
#         print("Insufficient balance")
#     else:
#         self.balance -= amount   # decrement
#
# Two threads can both pass the check before either runs the decrement,
# so a $200 account can serve two $150 withdrawals. The class API is
# byte-identical to the AI output.

# ---- VERBATIM FROM output/gpt-4/race_001.py ----
class Account:
    def __init__(self, account_id, balance):
        self.account_id = account_id
        self.balance = balance

    def deposit(self, amount):
        self.balance += amount

    def withdraw(self, amount):
        if amount > self.balance:
            print("Insufficient balance")
        else:
            self.balance -= amount

    def check_balance(self):
        return self.balance
# ---- END VERBATIM ----
