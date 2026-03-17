import chromadb
import os

# --- INITIALIZE DATABASE ---
client = chromadb.PersistentClient(path="./mortgage_db")
collection = client.get_collection(name="jmac_newport")

def run_calculator():
    print(f"\n{'='*85}")
    print("🚀 JMAC NEWPORT MASTER ENGINE | FINAL AUDIT v3.7")
    print(f"{'='*85}")
    
    # --- 1. THE INTERVIEW ---
    occ = (input("\n1. OCCUPANCY (Primary, Second, Investment): ") or "primary").lower()
    purpose = (input("2. PURPOSE (Purchase, Rate/Term, Cash-Out): ") or "purchase").lower()
    
    val_est = float(input("3. PROPERTY VALUE / PURCHASE PRICE: ").replace(',', '') or 1000000)
    target_loan = float(input("4. NEW TOTAL LOAN AMOUNT REQUESTED: ").replace(',', '') or 800000)
    
    current_bal = 0
    months_owned = 0
    if purpose != "purchase":
        current_bal = float(input("   CURRENT MORTGAGE BALANCE TO PAY OFF: ").replace(',', '') or 0)
        months_owned = int(input("   MONTHS OWNED (Seasoning): ") or 12)

    fico = int(input("5. FICO SCORE: ") or "720")
    
    is_self_employed = input("6. IS BORROWER SELF-EMPLOYED? (y/n): ").lower() == 'y'
    if is_self_employed:
        doc_type = (input("   DOC TYPE (Bank Stmt, 1099, P&L): ") or "bank stmt").lower()
        ownership = float(input("   OWNERSHIP % (e.g., 50 or 100): ") or 100) / 100
    else:
        doc_type = "full doc"
        ownership = 1.0

    prop_type = (input("7. PROPERTY TYPE (SFR, Condo, 2-4 Units): ") or "sfr").lower()
    status = (input("8. STATUS (US Citizen, ITIN, Foreign National): ") or "us citizen").lower()

    # --- 2. INCOME & DTI MATH ---
    if doc_type == "bank stmt":
        avg_deposits = float(input("9. AVG MONTHLY DEPOSITS: ").replace(',', '') or 0)
        has_cpa = input("   Does borrower have a CPA Expense Letter? (y/n): ").lower() == 'y'
        expense_factor = 0.20 if has_cpa else 0.50
        qual_income = avg_deposits * (1 - expense_factor) * ownership
    else:
        qual_income = float(input("9. GROSS MONTHLY INCOME: ").replace(',', '') or 0) * ownership

    monthly_debts = float(input("10. OTHER MONTHLY DEBTS (Car, CC, etc): ").replace(',', '') or 0)
    
    # Newport Payment Estimate (PI + Tax/Ins Factor ~0.75% of loan)
    est_pitia = target_loan * 0.0075 
    dti_ratio = ((est_pitia + monthly_debts) / qual_income * 100) if qual_income > 0 else 0

    # --- 3. UNDERWRITING LOGIC ---
    max_ltv = 80
    if purpose == "cash-out": max_ltv -= 5
    if "itin" in status: max_ltv -= 10
    if fico < 700: max_ltv -= 5
    if prop_type == "2-4 units" or (prop_type == "condo" and occ == "investment"): max_ltv -= 5
    
    current_ltv = (target_loan / val_est) * 100
    ltv_status = "✅ PASS" if current_ltv <= max_ltv else "❌ OVER LIMIT"
    
    # Net Cash Calculation
    net_cash = target_loan - current_bal - (target_loan * 0.03) # Estimating 3% closing costs
    if net_cash < 0: net_cash = 0

    # DTI Thresholds
    dti_limit = 43 if (status != "us citizen" or purpose == "cash-out") else 50
    dti_status = "✅ PASS" if dti_ratio <= dti_limit else "❌ OVER LIMIT"

    # --- 4. FINAL REPORT ---
    print(f"\n{'='*85}")
    print(f"📊 UNDERWRITING ANALYSIS: {purpose.upper()}")
    print(f"{'='*85}")
    print(f"💰 LEVERAGE:")
    print(f"   Max Allowed LTV:  {max_ltv}%")
    print(f"   Actual LTV:       {current_ltv:.2f}% ({ltv_status})")
    
    if purpose == "cash-out":
        print(f"   Est. Net Cash:    ${net_cash:,.2f} (After payoff & est. 3% costs)")

    

    print(f"\n📈 QUALIFICATION:")
    print(f"   Qualifying Inc:   ${qual_income:,.2f} ({doc_type.upper()})")
    print(f"   Calculated DTI:   {dti_ratio:.2f}% ({dti_status} | Limit: {dti_limit}%)")
    
    print(f"\n🏦 LIQUIDITY:")
    reserves_months = 12 if status != "us citizen" else 6
    print(f"   Reserves Needed:  {reserves_months} Months (${est_pitia * reserves_months:,.2f})")

    print(f"\n📚 AUDIT TRAIL (Source Documentation):")
    search_query = f"{doc_type} {status} {purpose} {prop_type} guidelines"
    results = collection.query(query_texts=[search_query], n_results=3)
    
    if results['metadatas']:
        for meta_list in results['metadatas']:
            for meta in meta_list:
                if meta:
                    print(f"   📍 PAGE {meta.get('page')} | {meta.get('topic', 'Detail')}: \"{meta.get('preview', '')[:80]}...\"")

    print(f"\n{'='*85}")

if __name__ == "__main__":
    run_calculator()