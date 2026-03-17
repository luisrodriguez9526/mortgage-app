import streamlit as st
from matching_engine import MortgageIntelligenceEngine, MortgageScenario

st.set_page_config(page_title="Mortgage AI", layout="wide")
st.title("🏦 Mortgage Intelligence Engine")

with st.sidebar:
    st.header("Borrower Profile")
    inc_type = st.selectbox("Income Type", ["W2", "1099", "Bank Statements", "DSCR"])
    is_fn = st.checkbox("Foreign National")
    
    if is_fn:
        fn_mode = st.radio("Credit", ["No US Credit", "Has US FICO"])
        fico = 0 if fn_mode == "No US Credit" else st.slider("US FICO", 600, 850, 700)
    else:
        fico = st.slider("FICO Score", 600, 850, 700)
        
    st.divider()
    loan_amt = st.number_input("Loan Amount ($)", value=400000)
    prop_val = st.number_input("Property Value ($)", value=500000)
    
    if inc_type == "DSCR":
        st.info("DSCR uses property rent to qualify.")
        income = st.number_input("Est. Monthly Rent ($)", value=3500)
        debts = 0
    else:
        income = st.number_input("Monthly Gross Income ($)", value=15000)
        debts = st.number_input("Monthly Personal Debts ($)", value=1000)
        
    occ = st.selectbox("Occupancy", ["Primary", "Investment"])

# Calculation
ltv = (loan_amt / prop_val) * 100
engine = MortgageIntelligenceEngine()
results = engine.run_analysis(MortgageScenario(
    fico=fico, ltv=ltv, loan_amount=loan_amt, monthly_income=income, 
    other_debts=debts, occupancy=occ, is_foreign_national=is_fn, income_type=inc_type
))

# Dashboard Display
res = results[0]
m1, m2, m3, m4 = st.columns(4)
m1.metric("LTV", f"{ltv:.1f}%")
m2.metric("Market Rate", f"{res['rate']}%")
m3.metric("Monthly PITIA", f"${res['pitia']:,.2f}")
cash = (prop_val - loan_amt) + (loan_amt * 0.03) + res['reserves']
m4.metric("TOTAL CASH", f"${cash:,.0f}")

st.divider()
for r in results:
    with st.expander(f"{r['status']} | {r['bank']}"):
        st.write(f"**Income Method:** {inc_type}")
        if "❌" in r['status']: st.error(r['reason'])
        st.write(f"**DTI/Ratio:** {r['dti']}")
        st.write(f"**Req. Reserves:** ${r['reserves']:,.2f}")