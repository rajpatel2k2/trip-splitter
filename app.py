"""Trip Splitter - Streamlit UI. Run: streamlit run app.py"""
import json
import uuid
from datetime import date
from urllib.parse import quote

import pandas as pd
import streamlit as st

from calc import calculate_expense_shares, calculate_member_balances, calculate_settlements
from storage import load_trip, new_trip, save_trip, update_trip

st.set_page_config(page_title="Trip Splitter", page_icon="🧳")
st.markdown("""<style>
/* Streamlit's toolbar floats over the top of the page, so the container must keep
   that space clear: padding-top below is toolbar height (3.75rem) + breathing room. */
.block-container{padding:3.75rem 1rem 4rem;max-width:760px}
h1{font-size:1.7rem!important;line-height:1.2}
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button,.stLinkButton>a{min-height:2.75rem}
input,textarea{font-size:16px!important}
/* long share links wrap inside the expander instead of being clipped */
[data-testid="stCode"],[data-testid="stCode"] *{max-width:100%;min-width:0;white-space:pre-wrap!important;word-break:break-all;overflow-wrap:anywhere}
[data-testid="stCode"] pre{font-size:.8rem}
/* header row: square tap target for the refresh button, long trip names ellipsis */
.st-key-hdr [data-testid="stButton"] button{min-width:2.75rem;height:2.75rem;padding:0;font-size:1.15rem;line-height:1}
.st-key-hdr [data-testid="stHeading"] h1{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* summary cards: 2x2 on phones, 1 row on desktop */
.st-key-summary [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.5rem}
.st-key-summary [data-testid$="olumn"]{flex:1 1 calc(50% - .5rem)!important;min-width:calc(50% - .5rem)!important}
@media(min-width:640px){.st-key-summary [data-testid$="olumn"]{flex:1 1 0!important;min-width:0!important}}
/* rows that must stay side by side on phones */
.st-key-hdr [data-testid="stHorizontalBlock"],.st-key-members [data-testid="stHorizontalBlock"],[class*="st-key-acts_"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:.5rem}
.st-key-hdr [data-testid$="olumn"],.st-key-members [data-testid$="olumn"],[class*="st-key-acts_"] [data-testid$="olumn"]{min-width:0!important}
@media(max-width:480px){.block-container{padding-top:3rem}}
</style>""", unsafe_allow_html=True)
uid = lambda: uuid.uuid4().hex[:8]


def money(p, cur="₹"):
    a = abs(p)
    return f"{'-' if p < 0 else ''}{cur}{a // 100:,}" + (f".{a % 100:02d}" if a % 100 else "")


def app_url(tid):
    try:
        h = st.context.headers
        host = h.get("Host", "localhost:8501")
        proto = h.get("X-Forwarded-Proto") or ("http" if host.startswith(("localhost", "127.")) else "https")
        return f"{proto}://{host}/?trip={tid}"
    except Exception:
        return f"?trip={tid}"


def demo_trip():
    t = new_trip("Goa Trip")
    names = ["Rahul", "Amit", "Priya", "Neha", "Jay", "Karan", "Dev"]
    ms = {n: uid() for n in names}
    allm = list(ms.values())
    ex = lambda d, rs, by, ps=None: {"id": uid(), "description": d, "amount": rs * 100, "paid_by": ms[by],
                                     "participants": [ms[p] for p in ps] if ps else allm, "date": ""}
    t["members"] = [{"id": i, "name": n} for n, i in ms.items()]
    t["expenses"] = [ex("Hotel", 7000, "Rahul"), ex("Dinner", 2100, "Amit"),
                     ex("Petrol", 1400, "Priya", ["Rahul", "Priya", "Jay", "Karan"]), ex("Tickets", 2800, "Neha")]
    save_trip(t)
    return t


def landing(msg=None):
    st.title("🧳 Trip Splitter")
    st.write("Split group trip expenses and see **who pays whom**. No login. Every trip has its own private link.")
    if msg:
        st.error(msg)
    t1, t2 = st.tabs(["Create a trip", "Open with code"])
    with t1:
        with st.form("create"):
            name = st.text_input("Trip name", placeholder="Goa Trip")
            cur = st.text_input("Currency symbol", "₹", max_chars=4)
            if st.form_submit_button("Create trip", type="primary"):
                if not name.strip():
                    st.warning("Give the trip a name.")
                else:
                    st.query_params["trip"] = new_trip(name.strip(), cur.strip() or "₹")["id"]
                    st.rerun()
        if st.button("Try a demo trip (Goa)"):
            st.query_params["trip"] = demo_trip()["id"]
            st.rerun()
    with t2, st.form("open"):
        code = st.text_input("Trip code")
        if st.form_submit_button("Open"):
            st.query_params["trip"] = code.strip()
            st.rerun()


def check(desc, amt, payer, parts):
    if not desc.strip():
        return "Add a short description."
    if not amt or amt <= 0:
        return "Amount must be greater than zero."
    if not payer:
        return "Choose who paid."
    if not parts:
        return "Select at least one participant."


tid = st.query_params.get("trip")
trip = load_trip(tid) if tid else None
if not trip:
    landing("Trip not found. Check the link or code." if tid else None)
    st.stop()


def mutate(fn):
    update_trip(tid, fn)
    st.rerun()


def mem_mutate(fn):
    st.session_state["mem_open"] = True  # keep the Members section open after changes
    mutate(fn)


cur, members, expenses = trip["currency"], trip["members"], trip["expenses"]
ids = [m["id"] for m in members]
nm = lambda i: next((m["name"] for m in members if m["id"] == i), "?")
bal = calculate_member_balances(members, expenses)
tx = calculate_settlements(bal)
total = sum(e["amount"] for e in expenses)

# ---- Header + share ----
c1, c2 = st.container(key="hdr").columns([5, 1])
c1.title(f"🧳 {trip['name']}")
c2.button("🔄", help="Refresh to see new expenses")
with st.expander("🔗 Share this trip with your group"):
    url = app_url(tid)
    st.code(url, language=None)
    st.link_button("Share on WhatsApp", "https://wa.me/?text=" + quote(f"Add your expenses for {trip['name']}: {url}"))
    st.caption("Anyone with this link can view and add expenses. Only share it with your group.")

# ---- Summary ----
a, b, c, d = st.container(key="summary").columns(4)
a.metric("Total", money(total, cur))
b.metric("Members", len(members))
c.metric("Expenses", len(expenses))
d.metric("Per person", money(round(total / len(members)), cur) if members else money(0, cur))

# ---- Who pays whom ----
st.subheader("Who pays whom?")
if tx:
    for t in tx:
        st.success(f"**{nm(t['from'])}** pays **{money(t['amount'], cur)}** to **{nm(t['to'])}**", icon="💸")
    st.caption("All expenses are settled after these payments.")
else:
    st.info("Everyone is settled." if expenses else "Add an expense to see who pays whom.")

# ---- Members ----
with st.expander(f"👥 Members ({len(members)})", expanded=st.session_state.get("mem_open", not members)):
    with st.form("add_member", clear_on_submit=True):
        n = st.text_input("Add member")
        if st.form_submit_button("Add"):
            if not n.strip():
                st.warning("Enter a name.")
            elif n.strip().lower() in [m["name"].lower() for m in members]:
                st.warning("That name already exists.")
            else:
                mem_mutate(lambda t: t["members"].append({"id": uid(), "name": n.strip()}))
    _ml = st.container(key="members")
    for m in members:
        x, y = _ml.columns([5, 1])
        new = x.text_input("Name", m["name"], key=f"mn_{m['id']}", label_visibility="collapsed")
        if new.strip() and new.strip() != m["name"]:
            mem_mutate(lambda t, i=m["id"], v=new.strip(): next(q for q in t["members"] if q["id"] == i).update(name=v))
        if y.button("✕", key=f"rm_{m['id']}"):
            if any(m["id"] == e["paid_by"] or m["id"] in e["participants"] for e in expenses):
                st.error(f"{m['name']} is in existing expenses. Delete or edit those first.")
            else:
                mem_mutate(lambda t, i=m["id"]: t.update(members=[q for q in t["members"] if q["id"] != i]))

# ---- Add expense ----
st.subheader("+ Add Expense")
if not members:
    st.info("Add members first.")
else:
    with st.form("add_exp", clear_on_submit=True):
        desc = st.text_input("What was it for?", placeholder="Hotel, Dinner, Petrol…")
        x, y = st.columns(2)
        amt = x.number_input("Amount", min_value=0.0, step=50.0, format="%.2f")
        payer = y.selectbox("Paid by", ids, index=None, format_func=nm, placeholder="Who paid?")
        when = st.date_input("Date (optional)", value=None)
        parts = st.multiselect("Split between", ids, default=ids, format_func=nm)
        if st.form_submit_button("+ Add Expense", type="primary"):
            err = check(desc, amt, payer, parts)
            if err:
                st.error(err)
            else:
                e = {"id": uid(), "description": desc.strip(), "amount": round(amt * 100), "paid_by": payer,
                     "participants": parts, "date": when.isoformat() if when else ""}
                mutate(lambda t: t["expenses"].append(e))

# ---- Expense list ----
st.subheader(f"Expenses ({len(expenses)})")
if not expenses:
    st.caption("No expenses yet.")
for e in reversed(expenses):
    with st.expander(f"{e['description']} · {money(e['amount'], cur)} · paid by {nm(e['paid_by'])}"):
        st.caption(f"{len(e['participants'])} people" + (f" · {e['date']}" if e.get("date") else ""))
        st.markdown("\n".join(f"- {nm(p)} — {money(s, cur)}" for p, s in calculate_expense_shares(e).items()))
        x, y = st.container(key=f"acts_{e['id']}").columns(2)
        with x.popover("✏️ Edit"), st.form(f"ef_{e['id']}"):
            d2 = st.text_input("Description", e["description"])
            a2 = st.number_input("Amount", 0.0, value=e["amount"] / 100, step=50.0, format="%.2f")
            p2 = st.selectbox("Paid by", ids, index=ids.index(e["paid_by"]) if e["paid_by"] in ids else None, format_func=nm)
            s2 = st.multiselect("Split between", ids, default=[i for i in e["participants"] if i in ids], format_func=nm)
            if st.form_submit_button("Save"):
                err = check(d2, a2, p2, s2)
                if err:
                    st.error(err)
                else:
                    mutate(lambda t, i=e["id"]: next(q for q in t["expenses"] if q["id"] == i).update(
                        description=d2.strip(), amount=round(a2 * 100), paid_by=p2, participants=s2))
        with y.popover("🗑️ Delete"):
            st.write("Delete this expense?")
            if st.button("Yes, delete", key=f"del_{e['id']}"):
                mutate(lambda t, i=e["id"]: t.update(expenses=[q for q in t["expenses"] if q["id"] != i]))

# ---- Balances ----
st.subheader("Balances")
if bal:
    st.dataframe(pd.DataFrame([{"Member": r["name"], "Paid": money(r["paid"], cur), "Share": money(r["share"], cur),
                                "Balance": ("+" if r["balance"] > 0 else "") + money(r["balance"], cur),
                                "Status": "Gets" if r["balance"] > 0 else "Pays" if r["balance"] < 0 else "Settled"}
                               for r in bal]), hide_index=True, use_container_width=True)

# ---- Backup (JSON) ----
with st.expander("💾 Backup & restore (JSON)"):
    st.download_button("Download backup", json.dumps(trip, indent=2, ensure_ascii=False),
                       file_name=f"{trip['name']}-{date.today()}.json", mime="application/json")
    up = st.file_uploader("Restore from a backup file", type="json")
    if up and st.button("Replace this trip with the backup"):
        try:
            data = json.load(up)
            assert isinstance(data["members"], list) and isinstance(data["expenses"], list)
            mutate(lambda t: t.update(name=data.get("name", t["name"]), currency=data.get("currency", t["currency"]),
                                      members=data["members"], expenses=data["expenses"]))
        except Exception:
            st.error("That file is not a valid trip backup.")
