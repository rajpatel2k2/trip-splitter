from calc import calculate_expense_shares as shares, calculate_member_balances as balances, calculate_settlements as settle

M = [{"id": i, "name": i} for i in "abc"]
E = lambda amt, by, ps: {"amount": amt, "paid_by": by, "participants": ps}


def test_uneven_split_sums_exactly():
    s = shares(E(10000, "a", ["a", "b", "c"]))
    assert sum(s.values()) == 10000 and sorted(s.values()) == [3333, 3333, 3334]


def test_partial_participants_and_zero_paid():
    b = {r["id"]: r for r in balances(M, [E(3000, "a", ["a", "b"])])}
    assert b["a"]["balance"] == 1500 and b["b"]["balance"] == -1500 and b["c"]["balance"] == 0


def test_balances_sum_to_zero_and_settlement_reconciles():
    b = balances(M, [E(9000, "a", ["a", "b", "c"]), E(3000, "b", ["b", "c"]), E(100, "c", ["a", "b", "c"])])
    assert sum(r["balance"] for r in b) == 0
    tx = settle(b)
    assert sum(t["amount"] for t in tx) == sum(r["balance"] for r in b if r["balance"] > 0)
    paid = {r["id"]: r["balance"] for r in b}
    for t in tx:
        paid[t["from"]] += t["amount"]
        paid[t["to"]] -= t["amount"]
    assert all(v == 0 for v in paid.values())


def test_goa_scenario():
    names = ["Rahul", "Amit", "Priya", "Neha", "Jay", "Karan", "Dev"]
    ms = [{"id": n, "name": n} for n in names]
    ex = [E(700000, "Rahul", names), E(210000, "Amit", names), E(140000, "Priya", ["Rahul", "Priya", "Jay", "Karan"]),
          E(280000, "Neha", names)]
    b = {r["id"]: r["balance"] for r in balances(ms, ex)}
    assert b == {"Rahul": 495000, "Amit": 40000, "Priya": -65000, "Neha": 110000, "Jay": -205000, "Karan": -205000, "Dev": -170000}
    assert sum(t["amount"] for t in settle(balances(ms, ex))) == 645000


def test_one_person_pays_everything_and_direct_payment():
    tx = settle(balances(M[:2], [E(1000, "a", ["a", "b"])]))
    assert tx == [{"from": "b", "to": "a", "amount": 500}]
