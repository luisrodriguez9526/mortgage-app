import streamlit as st
from matching_engine import MortgageIntelligenceEngine, MortgageScenario

# 1. Set page config FIRST
st.set_page_config(page_title="Mortgage comparison Engine", layout="wide")
st.title("🏦 Mortgage Intelligence Engine")

# 2. Sidebar Inputs
with st.sidebar:
    st.header("Borrower Profile")
    inc_type = st.selectbox("Income Type", ["W2", "1099", "Bank Statements", "P&L", "DSCR"])
    is_fn = st.toggle("Foreign National Borrower")
    fico = st.slider("FICO Score", 0, 850, 700)
    
    st.divider()
    purpose = st.selectbox("Loan Purpose", ["Purchase", "Rate/Term Refi", "Cash-Out Refi"])
    occ = st.selectbox("Occupancy", ["Primary", "Second Home", "Investment"])
    
    st.divider()
    loan_amt = st.number_input("Loan Amount ($)", value=400000)
    prop_val = st.number_input("Property Value ($)", value=500000)
    income = st.number_input("Monthly Income/Rent ($)", value=12000)
    debts = st.number_input("Monthly Debts ($)", value=500)

# 3. Logic Execution
ltv = (loan_amt / prop_val) * 100
engine = MortgageIntelligenceEngine()
results = engine.run_analysis(MortgageScenario(
    fico=fico, ltv=ltv, loan_amount=loan_amt, monthly_income=income, 
    other_debts=debts, occupancy=occ, is_foreign_national=is_fn, 
    income_type=inc_type, loan_purpose=purpose
))

# 4. Results Section (This was where your error was)
st.subheader("Lender Eligibility & Detailed Source Audit")

for r in results:
    is_eligible = "✅" in r['status']
    with st.expander(f"{r['status']} | {r['bank']}", expanded=True):
        tab_details, tab_audit = st.tabs(["Decision Details", "🔍 Structural Source Audit"])
        
        with tab_details:
            if not is_eligible:
                for msg in r['reasons']: st.error(msg)
            else:
                st.success(f"Qualified for {r['bank']} at {r['rate']:.3f}%")
                st.write(f"**Monthly P&I:** ${r['pitia']:,.2f} | **Reserves:** ${r['reserves']:,.2f}")

        with tab_audit:
            for entry in r['audit']:
                st.markdown(f"**📄 Document:** `{entry['doc']}`")
                st.markdown(f"**🏷️ Program:** {entry['program']}")
                st.markdown(f"**📍 Location:** {entry['location']}")
                st.markdown(f"**📝 Rule:** {entry['context']}")
                st.divider()