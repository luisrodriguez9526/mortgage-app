import streamlit as st
from matching_engine import MortgageIntelligenceEngine, MortgageScenario

st.set_page_config(page_title="Mortgage AI Underwriter", layout="wide", page_icon="🏦")
st.title("🏦 Mortgage Intelligence Engine")

with st.sidebar:
    st.header("Borrower Profile")
    # Income Types expanded per AD Matrix
    inc_type = st.selectbox("Income Type", ["W2", "1099", "Bank Statements", "P&L", "DSCR"])
    is_fn = st.toggle("Foreign National Borrower")
    
    if is_fn:
        fn_credit = st.radio("Credit History", ["No US Credit", "Has US FICO"])
        fico = 0 if "No" in fn_credit else st.slider("US FICO Score", 600, 850, 700)
    else:
        fico = st.slider("FICO Score", 600, 850, 680)
    
    st.divider()
    
    # Restored Loan Details
    purpose = st.selectbox("Loan Purpose", ["Purchase", "Rate/Term Refi", "Cash-Out Refi"])
    occ = st.selectbox("Occupancy", ["Primary", "Second Home", "Investment"])
    
    st.divider()
    
    loan_amt = st.number_input("Loan Amount ($)", value=400000, step=10000)
    prop_val = st.number_input("Property Value ($)", value=500000, step=10000)
    
    if inc_type == "DSCR":
        income = st.number_input("Est. Monthly Rent ($)", value=4000)
        debts = 0
    else:
        income = st.number_input("Monthly Gross Income ($)", value=12000)
        debts = st.number_input("Monthly Personal Debts ($)", value=500)

# Calculations
ltv = (loan_amt / prop_val) * 100
engine = MortgageIntelligenceEngine()
results = engine.run_analysis(MortgageScenario(
    fico=fico, ltv=ltv, loan_amount=loan_amt, monthly_income=income, 
    other_debts=debts, occupancy=occ, is_foreign_national=is_fn, 
    income_type=inc_type, loan_purpose=purpose
))

# Top Metric Dashboard
res = results[0]
m1, m2, m3, m4 = st.columns(4)
m1.metric("LTV Ratio", f"{ltv:.1f}%")
m2.metric("Est. Rate", f"{res['rate']:.3f}%")
m3.metric("DTI / DSCR", res['dti'])
m4.metric("Monthly PITIA", f"${res['pitia']:,.2f}")

st.divider()

# Cash to Close Calculations
down_payment = max(0, prop_val - loan_amt) if purpose == "Purchase" else 0
closing_costs = loan_amt * 0.03 # Standard 3% estimate
total_cash = down_payment + closing_costs + res['reserves']

st.subheader("💰 Liquidity Analysis (Cash to Close)")
c1, c2, c3, c4 = st.columns(4)
c1.info(f"**Down Payment:**\n${down_payment:,.0f}")
c2.info(f"**Closing Costs (3%):**\n${closing_costs:,.0f}")
c3.info(f"**Required Reserves:**\n${res['reserves']:,.0f}")
c4.success(f"**TOTAL LIQUIDITY:**\n${total_cash:,.0f}")

st.markdown("---")

# Eligibility Results
for r in results:
    is_pass = "✅" in r['status']
    with st.expander(f"{r['status']} | {r['bank']}", expanded=is_pass):
        if not is_pass:
            for reason in r['reasons']: st.error(reason)
        else:
            st.write(f"**Program:** {inc_type} - {purpose}")
            st.write(f"**Occupancy:** {occ}")
            st.write(f"**Reserves Required:** {int(r['reserves']/r['pitia'])} Months")
            st.success(f"Borrower is eligible. Ensure verified assets exceed ${total_cash:,.2f}")