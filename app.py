import streamlit as st
from matching_engine import MortgageIntelligenceEngine, MortgageScenario

st.set_page_config(page_title="Mortgage AI", layout="wide")
st.title("🏦 Mortgage Intelligence Engine")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Borrower Profile")
    is_fn = st.checkbox("Foreign National Borrower")
    if is_fn:
        credit_type = st.radio("Credit History", ["No US Credit", "Has US FICO"])
        fico = 0 if "No" in credit_type else st.slider("US FICO Score", 600, 850, 700)
    else:
        fico = st.slider("FICO Score", 600, 850, 667)
    
    st.divider()
    loan_amt = st.number_input("Loan Amount ($)", value=400000)
    prop_val = st.number_input("Property Value ($)", value=500000)
    
    st.divider()
    income = st.number_input("Monthly Income ($)", value=15000)
    debts = st.number_input("Monthly Debts ($)", value=1000)
    occ = st.selectbox("Occupancy", ["Primary", "Second Home", "Investment"])

# --- CALCULATIONS ---
ltv = (loan_amt / prop_val) * 100
down_payment = prop_val - loan_amt
est_closing_costs = loan_amt * 0.03 # 3% average

engine = MortgageIntelligenceEngine()
rate = engine.get_market_rate(fico, is_fn, occ)
pitia = engine.calculate_pitia(loan_amt, rate)
reserves = engine.calculate_reserves(pitia, occ, is_fn)
total_cash_required = down_payment + est_closing_costs + reserves

# --- METRICS ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("LTV", f"{ltv:.1f}%")
m2.metric("Rate", f"{rate:.3f}%")
m3.metric("Monthly PITIA", f"${pitia:,.2f}")
m4.metric("Total Cash Required", f"${total_cash_required:,.0f}")

st.divider()

# --- CASH BREAKDOWN ---
c1, c2, c3 = st.columns(3)
c1.write(f"📉 **Down Payment:** ${down_payment:,.0f}")
c2.write(f"📝 **Est. Closing Costs (3%):** ${est_closing_costs:,.0f}")
c3.write(f"💰 **Req. Reserves:** ${reserves:,.0f}")

st.markdown("---")

# --- RESULTS ---
scenario = MortgageScenario(
    name="Prospect", fico=fico, ltv=ltv, loan_amount=loan_amt,
    monthly_income=income, other_debts=debts, property_type="SFR",
    loan_purpose="Purchase", occupancy=occ, income_type="Bank Statements", 
    is_foreign_national=is_fn, state="FL"
)

results = engine.run_analysis(scenario)
for res in results:
    is_pass = "✅" in res['status']
    with st.expander(f"{res['status']} | {res['bank']}", expanded=is_pass):
        if not is_pass:
            for r in res['reasons']: st.error(r)
        else:
            st.success(f"Clear to Proceed: Total Liquidity needed: ${total_cash_required:,.2f}")