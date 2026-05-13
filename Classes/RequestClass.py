class Request:
    type = "" # Designates the type of request, for instance marriage
    user_sent = 0 # The id of the user who sent the request

    def __init__(self, type: str, user_sent: int, amount: int = None):
        self.type = type
        self.user_sent = user_sent
        self.amount = amount  # Optional — used by bet requests; None for marriage/adoption

    def set_type(self, type: str):
        self.type = type

    def set_user(self, user_id: int):
        self.user_sent = user_id

    def get_type(self):
        return self.type

    def get_user(self):
        return self.user_sent

    def get_amount(self):
        return self.amount

    def equal_request(self, type, user_sent): # Determines whether two requests are the same
        if self.type == type and user_sent == self.user_sent:
            return True
        return False

    def to_dict(self):
        out = {
            "request_type": self.type,
            "user_id": self.user_sent
        }
        if self.amount is not None:
            out["amount"] = int(self.amount)
        return out
