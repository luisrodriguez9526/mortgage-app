import streamlit as st
from matching_engine import MortgageIntelligenceEngine, MortgageScenario

st.set_page_config(page_title="Mortgage AI", layout="wide", page_icon="🏦")
st.title("🏦 Mortgage Intelligence Engine")

with st.sidebar:
    st.header("Borrower Profile")
    inc_type = st.selectbox("Income Type", ["W2", "1099", "Bank Statements", "DSCR"])
    is_fn = st.toggle("Foreign National")
    
    if is_fn:
        fn_credit = st.radio("Credit History", ["No US Credit", "Has US FICO"])
        fico = 0 if "No" in fn_credit else st.slider("US FICO", 600, 850, 700)
    else:
        fico = st.slider("FICO Score", 600, 850, 680)
        
    st.divider()
    loan_amt = st.number_input("Loan Amount ($)", value=400000, step=10000)
    prop_val = st.number_input("Property Value ($)", value=500000, step=10000)
    
    if inc_type == "DSCR":
        income = st.number_input("Est. Monthly Rent ($)", value=4000)
        debts = 0
    else:
        income = st.number_input("Monthly Gross Income ($)", value=12000)
        debts = st.number_input("Monthly Personal Debts ($)", value=500)
        
    occ = st.selectbox("Occupancy", ["Primary", "Investment"])

# Engine Execution
ltv = (loan_amt / prop_val) * 100
engine = MortgageIntelligenceEngine()
results = engine.run_analysis(MortgageScenario(
    fico=fico, ltv=ltv, loan_amount=loan_amt, monthly_income=income, 
    other_debts=debts, occupancy=occ, is_foreign_national=is_fn, income_type=inc_type
))

# Top Metric Dashboard
res = results[0] 
m1, m2, m3, m4 = st.columns(4)
m1.metric("LTV Ratio", f"{ltv:.1f}%")
m2.metric("Market Rate", f"{res['rate']:.3f}%")
m3.metric("Monthly PITIA", f"${res['pitia']:,.2f}")

# Fixed Cash to Close Logic
down_payment = max(0, prop_val - loan_amt) 
closing_costs = loan_amt * 0.03
total_liquidity = down_payment + closing_costs + res['reserves']
m4.metric("TOTAL CASH REQUIRED", f"${total_liquidity:,.0f}")

st.divider()

# Cash Breakdown
st.subheader("💰 Liquidity Breakdown")
c1, c2, c3 = st.columns(3)
c1.warning(f"Down Payment: ${down_payment:,.0f}")
c2.info(f"Closing Costs (3%): ${closing_costs:,.0f}")
c3.success(f"Required Reserves: ${res['reserves']:,.0f}")

st.markdown("---")

# Lender Display
for r in results:
    is_pass = "✅" in r['status']
    with st.expander(f"{r['status']} | {r['bank']}", expanded=is_pass):
        if not is_pass:
            for reason in r['reasons']: st.error(reason)
        else:
            st.write(f"**Program:** {inc_type} | {'Foreign National' if is_fn else 'Domestic'}")
            st.write(f"**DTI/Ratio:** {r['dti']}")
            st.write(f"**Required Reserves:** ${r['reserves']:,.2f}")