class Request:
    type = "" # Designates the type of request, for instance marriage
    user_sent = 0 # The id of the user who sent the request

    def __init__(self, type: str, user_sent: int, amount: int = None, reason: str = None):
        self.type = type
        self.user_sent = user_sent
        self.amount = amount  # Optional — used by bet requests; None for marriage/adoption
        self.reason = reason  # Optional — free-text description, used by bet requests

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

    def get_reason(self):
        return self.reason

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
        if self.reason is not None:
            out["reason"] = self.reason
        return out
