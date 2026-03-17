import streamlit as st
from matching_engine import MortgageIntelligenceEngine, MortgageScenario

st.set_page_config(page_title="Mortgage AI Underwriter", layout="wide", page_icon="🏦")
st.title("🏦 Mortgage Intelligence Engine")

with st.sidebar:
    st.header("Quick Input")
    borrower_name = st.text_input("Borrower Name", value="New Prospect")
    
    # 1. Core Profile
    inc_type = st.selectbox("Income Type", ["W2", "1099", "Bank Statements", "DSCR"])
    is_fn = st.toggle("Foreign National Borrower")
    
    if is_fn:
        fn_mode = st.radio("Credit History", ["No US Credit", "Has US FICO"])
        fico = 0 if "No" in fn_mode else st.slider("US FICO Score", 600, 850, 700)
    else:
        fico = st.slider("FICO Score", 600, 850, 667)
    
    st.divider()
    
    # 2. Loan Details (Restored Purpose & Occupancy)
    purpose = st.selectbox("Loan Purpose", ["Purchase", "Rate/Term Refi", "Cash-Out Refi"])
    occ = st.selectbox("Occupancy", ["Primary", "Second Home", "Investment"])
    
    st.divider()
    
    # 3. Financials
    loan_amt = st.number_input("Loan Amount ($)", value=400000, step=5000)
    prop_val = st.number_input("Property Value ($)", value=500000, step=5000)
    
    if inc_type == "DSCR":
        income = st.number_input("Monthly Rent ($)", value=3500)
        debts = 0
    else:
        income = st.number_input("Monthly Income ($)", value=15000)
        debts = st.number_input("Monthly Debts ($)", value=1000)

# Calculations
ltv = (loan_amt / prop_val) * 100
engine = MortgageIntelligenceEngine()
results = engine.run_analysis(MortgageScenario(
    fico=fico, ltv=ltv, loan_amount=loan_amt, monthly_income=income, 
    other_debts=debts, occupancy=occ, is_foreign_national=is_fn, 
    income_type=inc_type, loan_purpose=purpose
))

# Dashboard
res = results[0]
m1, m2, m3, m4 = st.columns(4)
m1.metric("LTV Ratio", f"{ltv:.1f}%")
m2.metric("Market Rate", f"{res['rate']:.3f}%")
m3.metric("DTI / Ratio", res['dti'])
m4.metric("Monthly P&I+", f"${res['pitia']:,.2f}")

st.divider()

# Cash Breakdown (Fixed Logic)
down_payment = max(0, prop_val - loan_amt) if purpose == "Purchase" else 0
closing_costs = loan_amt * 0.03
total_cash = down_payment + closing_costs + res['reserves']

st.subheader("💰 Liquidity Analysis")
c1, c2, c3, c4 = st.columns(4)
c1.info(f"**Down Payment:** ${down_payment:,.0f}")
c2.info(f"**Closing Costs:** ${closing_costs:,.0f}")
c3.info(f"**Required Reserves:** ${res['reserves']:,.0f}")
c4.success(f"**Total Cash Needed:** ${total_cash:,.0f}")

st.markdown("---")

# Eligibility Results
for r in results:
    is_pass = "✅" in r['status']
    with st.expander(f"{r['status']} | {r['bank']}", expanded=is_pass):
        if not is_pass:
            for reason in r['reasons']: st.error(reason)
        else:
            st.write(f"**Program:** {inc_type} {purpose} for {occ}")
            st.write(f"**Analysis Note:** Based on current {inc_type} guidelines for a {fico if fico > 0 else 'No-Score FN'} FICO.")