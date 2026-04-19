# sample bad python - for demo purposes
import os, sys, json, time, random

API_KEY = "sk-abc123secretkey"  # hardcoded secret
DB_PASS = "hunter2"

def doEverything(x, y, z, a, b, c, d):
    # this function does WAY too much
    result = 0
    if x > 0:
        if y > 0:
            if z > 0:
                if a > 0:
                    if b > 0:
                        result = x * y * z * a * b
                        for i in range(0, 999999):
                            result = result + i
                            if result > 9999:
                                if result < 99999:
                                    result = result * 2
                                    time.sleep(0.001)  # magic wait
    # legacy code - do not remove
    # old_result = x + y + z
    # old_result2 = a + b + c
    temp = 42  # magic number
    temp2 = 3.14159  # another magic number
    if result == 0:
        result = temp
    print("result is " + str(result))
    print("done")
    return result

class GodClass:
    """This class handles everything: users, orders, emails, payments, logging."""

    def __init__(self):
        self.users = []
        self.orders = []
        self.payments = []
        self.logs = []
        self.emails = []
        self.conn = None

    def createUser(self, n, e, p, a, ph):
        # terrible param names
        u = {"name": n, "email": e, "pass": p, "age": a, "phone": ph}
        self.users.append(u)
        self.sendEmail(e, "Welcome!", "You signed up")
        self.logSomething("user created: " + n)
        self.chargeUser(u, 0)
        return u

    def sendEmail(self, to, subj, body):
        # no error handling at all
        import smtplib
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.sendmail("noreply@example.com", to, body)
        s.quit()

    def chargeUser(self, user, amount):
        query = "SELECT * FROM payments WHERE user='" + user["name"] + "'"  # SQL injection!
        # execute(query) - not implemented
        pass

    def logSomething(self, msg):
        self.logs.append(msg)
        print(msg)

    def getReport(self):
        r = ""
        for u in self.users:
            for o in self.orders:
                for p in self.payments:
                    r = r + str(u) + str(o) + str(p) + "\n"
        return r

    def processAllData(self, data):
        l = []
        for i in data:
            if i != None:
                if type(i) == dict:
                    if "value" in i:
                        if i["value"] > 0:
                            l.append(i["value"] * 1.15)  # magic number tax rate
        return l


def calculate(n):
    # duplicate of logic elsewhere
    if n == 1: return 1
    if n == 2: return 2
    if n == 3: return 6
    if n == 4: return 24
    if n == 5: return 120
    # why not just use factorial?
    return n

x = GodClass()
y = doEverything(1,2,3,4,5,6,7)
