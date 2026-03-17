import streamlit as st
from matching_engine import MortgageIntelligenceEngine, MortgageScenario

st.set_page_config(page_title="Mortgage comparison Engine", layout="wide")
st.title("🏦 Mortgage Intelligence Engine")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("Borrower Profile")
    inc_type = st.selectbox("Income Type", ["W2", "1099", "Bank Statements", "P&L", "DSCR"])
    is_fn = st.toggle("Foreign National Borrower")
    
    if is_fn:
        fn_credit = st.radio("Credit History", ["No US Credit", "Has US FICO"])
        fico = 0 if "No" in fn_credit else st.slider("US FICO Score", 600, 850, 700)
    else:
        fico = st.slider("FICO Score", 600, 850, 700)
    
    st.divider()
    purpose = st.selectbox("Loan Purpose", ["Purchase", "Rate/Term Refi", "Cash-Out Refi"])
    occ = st.selectbox("Occupancy", ["Primary", "Second Home", "Investment"])
    
    st.divider()
    loan_amt = st.number_input("Loan Amount ($)", value=400000, step=10000)
    prop_val = st.number_input("Property Value ($)", value=500000, step=10000)
    
    if inc_type == "DSCR":
        income = st.number_input("Est. Monthly Rent ($)", value=4000)
        debts = 0
    else:
        income = st.number_input("Monthly Gross Income ($)", value=15000)
        debts = st.number_input("Monthly Personal Debts ($)", value=500)

# --- RUN ANALYSIS ---
ltv = (loan_amt / prop_val) * 100
engine = MortgageIntelligenceEngine()
results = engine.run_analysis(MortgageScenario(
    fico=fico, ltv=ltv, loan_amount=loan_amt, monthly_income=income, 
    other_debts=debts, occupancy=occ, is_foreign_national=is_fn, 
    income_type=inc_type, loan_purpose=purpose
))

# --- DASHBOARD HEADER ---
res = results[0] # Using first result for basic math
m1, m2, m3, m4 = st.columns(4)
m1.metric("LTV Ratio", f"{ltv:.1f}%")
m2.metric("Est. Market Rate", f"{res['rate']:.3f}%")
m3.metric("Income Ratio", res['dti'])
m4.metric("Monthly P&I+", f"${res['pitia']:,.2f}")

st.divider()

# --- LENDER COMPARISON SECTION ---
st.subheader("Lender Eligibility Comparison")
for r in results:
    is_eligible = "✅" in r['status']
    # If ineligible, the expander is red-tinted via the status text
    with st.expander(f"{r['status']} | {r['bank']}", expanded=True):
        if not is_eligible:
            # Show why they can't do the deal
            for reason in r['reasons']:
                st.error(f"Guideline Violation: {reason}")
        else:
            # Show the winning details
            st.success(f"{r['bank']} can fund this deal.")
            c1, c2 = st.columns(2)
            c1.write(f"**Required Reserves:** ${r['reserves']:,.2f}")
            c2.write(f"**Program:** {inc_type} {purpose}")

# --- CASH TO CLOSE (Based on AD Mortgage logic as worst-case) ---
st.divider()
st.subheader("💰 Estimated Cash to Close")
down_payment = max(0, prop_val - loan_amt) if purpose == "Purchase" else 0
closing_costs = loan_amt * 0.03
# Use AD Mortgage reserves as the safe "High" estimate
max_reserves = next((r['reserves'] for r in results if r['bank'] == "AD MORTGAGE"), res['reserves'])
total_cash = down_payment + closing_costs + max_reserves

col1, col2, col3 = st.columns(3)
col1.metric("Down Payment", f"${down_payment:,.0f}")
col2.metric("Closing Costs", f"${closing_costs:,.0f}")
col3.metric("Total Liquid Assets Needed", f"${total_cash:,.0f}")