"""Pure money logic. All amounts are integers in minor units (paise/cents), so no float errors."""


def calculate_expense_shares(exp):
    """Split one expense equally; leftover paise go 1 each to the first participants so shares sum exactly."""
    ids = exp["participants"]
    if not ids:
        return {}
    base, rem = divmod(exp["amount"], len(ids))
    return {pid: base + (1 if i < rem else 0) for i, pid in enumerate(ids)}


def calculate_member_balances(members, expenses):
    rows = {m["id"]: {"id": m["id"], "name": m["name"], "paid": 0, "share": 0} for m in members}
    for e in expenses:
        if e["paid_by"] in rows:
            rows[e["paid_by"]]["paid"] += e["amount"]
        for pid, s in calculate_expense_shares(e).items():
            if pid in rows:
                rows[pid]["share"] += s
    for r in rows.values():
        r["balance"] = r["paid"] - r["share"]  # + gets money, - pays money
    return list(rows.values())


def calculate_settlements(balances):
    """Greedy: biggest debtor pays biggest creditor. Few transactions, totals always reconcile."""
    cred = sorted(([b["id"], b["balance"]] for b in balances if b["balance"] > 0), key=lambda x: -x[1])
    debt = sorted(([b["id"], -b["balance"]] for b in balances if b["balance"] < 0), key=lambda x: -x[1])
    out, i, j = [], 0, 0
    while i < len(debt) and j < len(cred):
        x = min(debt[i][1], cred[j][1])
        out.append({"from": debt[i][0], "to": cred[j][0], "amount": x})
        debt[i][1] -= x
        cred[j][1] -= x
        if debt[i][1] == 0:
            i += 1
        if cred[j][1] == 0:
            j += 1
    return out
