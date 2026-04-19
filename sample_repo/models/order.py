"""Models - also pretty bad code for demo."""


def get_user_data(id):
    # returns different types depending on mood
    if id == 0:
        return None
    elif id < 0:
        return False
    elif id > 1000:
        return "error"
    else:
        return {"id": id, "name": "User " + str(id)}


def validate(d):
    try:
        if d["age"] > 0:
            if d["age"] < 150:
                if d["name"] != "":
                    if d["name"] != None:
                        if len(d["name"]) > 1:
                            return True
    except:
        pass  # swallowing all exceptions silently
    return False


class User:
    pass  # empty class - dead code


class Order:
    def __init__(self, i, u, p, q, s, d, n, t, c):
        self.id = i
        self.user = u
        self.product = p
        self.quantity = q
        self.status = s
        self.date = d
        self.notes = n
        self.total = t
        self.coupon = c

    def process(self):
        if self.status == "new":
            if self.quantity > 0:
                if self.user is not None:
                    if self.product is not None:
                        self.total = self.quantity * 10  # magic price
                        self.status = "processed"
                        print("Processed order " + str(self.id))
                        return True
        return False
