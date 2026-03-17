import streamlit as st
from matching_engine import MortgageIntelligenceEngine, MortgageScenario

st.set_page_config(page_title="Mortgage comparison Engine", layout="wide")
st.title("🏦 Mortgage Intelligence Engine")

with st.sidebar:
    # RESTORED: Borrower Name
    client_name = st.text_input("Borrower Name", value="New Client")
    st.divider()
    
    inc_type = st.selectbox("Income Type", ["W2", "1099", "Bank Statements", "P&L", "DSCR"])
    is_fn = st.toggle("Foreign National Borrower")
    
    # FIXED: Conditional FICO Logic
    if is_fn:
        fn_mode = st.radio("Credit History", ["No US Credit", "Has US FICO"])
        fico = 0 if "No" in fn_mode else st.slider("US FICO Score", 600, 850, 700)
    else:
        fico = st.slider("FICO Score", 600, 850, 680)
    
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
        income = st.number_input("Monthly Gross Income ($)", value=12000)
        debts = st.number_input("Monthly Personal Debts ($)", value=500)

# EXECUTION
ltv = (loan_amt / prop_val) * 100
engine = MortgageIntelligenceEngine()
results = engine.run_analysis(MortgageScenario(
    borrower_name=client_name, fico=fico, ltv=ltv, loan_amount=loan_amt, 
    monthly_income=income, other_debts=debts, occupancy=occ, 
    is_foreign_national=is_fn, income_type=inc_type, loan_purpose=purpose
))

st.header(f"Qualification Report: {client_name}")

# DASHBOARD METRICS
res = results[0]
m1, m2, m3, m4 = st.columns(4)
m1.metric("LTV Ratio", f"{ltv:.1f}%")
m2.metric("Market Rate", f"{res['rate']:.3f}%")
m3.metric("Income Ratio", res['dti'])
m4.metric("Monthly P&I+", f"${res['pitia']:,.2f}")

st.divider()

# LENDER CARDS (ALL LENDERS SHOW RED ON FAILURE)
st.subheader("Lender Eligibility Comparison")
for r in results:
    is_fail = "❌" in r['status']
    # Expander remains open if the user needs to see why it failed
    with st.expander(f"{r['status']} | {r['bank']}", expanded=True):
        col_main, col_audit = st.tabs(["Eligibility Results", "🔍 Evidence Trail"])
        
        with col_main:
            if is_fail:
                for msg in r['reasons']:
                    st.error(f"LENDER DECLINE: {msg}")
            else:
                st.success(f"APPROVED: {r['bank']} accepts this scenario.")
                st.write(f"**Program:** {inc_type} {purpose}")
                st.write(f"**Required Reserves:** ${r['reserves']:,.2f}")
        
        with col_audit:
            if r['audit']:
                for entry in r['audit']:
                    st.info(f"Source: {entry['doc']} | Rule: {entry['rule']}")
            else:
                st.caption("Using standard Non-QM guideline overlays for this lender.")