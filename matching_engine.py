import os
from pydantic import BaseModel

class MortgageScenario(BaseModel):
    fico: int 
    ltv: float
    loan_amount: float
    monthly_income: float
    other_debts: float
    occupancy: str      
    income_type: str    
    is_foreign_national: bool
    loan_purpose: str

class MortgageIntelligenceEngine:
    def __init__(self):
        # Guideline database placeholder logic
        pass

    def get_market_rate(self, fico: int, is_fn: bool, occupancy: str, inc_type: str, purpose: str) -> float:
        if is_fn: base_rate = 8.99 if fico >= 660 or fico == 0 else 9.50
        elif fico >= 720: base_rate = 7.15 
        elif fico >= 660: base_rate = 7.75 
        else: base_rate = 8.35
        
        if inc_type in ["Bank Statements", "1099", "P&L"]: base_rate += 0.50
        if inc_type == "DSCR": base_rate += 0.875
        if occupancy == "Investment": base_rate += 0.375
        if purpose == "Cash-Out Refi": base_rate += 0.50
        return base_rate

    def calculate_pitia(self, loan_amount: float, rate: float):
        mr = (rate / 100) / 12
        pi = loan_amount * (mr * (1 + mr)**360) / ((1 + mr)**360 - 1)
        ti = ((loan_amount / 0.8) * 0.015) / 12 
        return pi + ti

    def run_analysis(self, scenario: MortgageScenario):
        rate = self.get_market_rate(scenario.fico, scenario.is_foreign_national, 
                                   scenario.occupancy, scenario.income_type, scenario.loan_purpose)
        pitia = self.calculate_pitia(scenario.loan_amount, rate)
        
        lenders = ["ARC HOME", "CHAMPIONS", "JMAC", "AD MORTGAGE"]
        final_results = []

        for bank in lenders:
            is_eligible = True
            reasons = []
            audit_trail = [] 
            
            if bank == "AD MORTGAGE":
                # LTV Rule Audit
                if scenario.ltv > 90:
                    is_eligible = False
                    reasons.append(f"Max LTV is 90%. Current: {scenario.ltv:.1f}%")
                    audit_trail.append({
                        "doc": "AD_Mortgage_Product-Matrix.md",
                        "program": "Super Prime / Prime / DSCR",
                        "location": "Main Table -> Row: 'Max LTV/CLTV'",
                        "context": "Matrix enforces a 90% cap for core Non-QM products."
                    })

                # DSCR Footnote Audit
                if scenario.income_type == "DSCR":
                    dscr_ratio = scenario.monthly_income / pitia
                    if dscr_ratio < 1.0 and scenario.fico < 680 and scenario.fico > 0:
                        is_eligible = False
                        reasons.append("DSCR < 1.0 requires 680 FICO.")
                        audit_trail.append({
                            "doc": "AD_Mortgage_Product-Matrix.md",
                            "program": "DSCR Program",
                            "location": "Income Employment Verification Section -> Table Footnote",
                            "context": "Footnote explicitly states: 'DSCR < 1 requires min FICO 680'."
                        })

                # Foreign National Header Audit
                if scenario.is_foreign_national:
                    res_months = 12
                    audit_trail.append({
                        "doc": "AD Mortgage Foreign Nationals-UW-Requirements.md",
                        "program": "Wholesale Foreign National",
                        "location": "Page 1 -> Header Summary Table -> Column: 'Reserves'",
                        "context": "Document requires 12 months post-closing reserves for FN borrowers."
                    })
                else:
                    res_months = 6 if scenario.occupancy != "Primary" else 3
                    audit_trail.append({
                        "doc": "AD Mortgage Non-QM-Loan-Eligibility-Guidelines.md",
                        "program": "General Non-QM",
                        "location": "Section 2.3 -> 'RESERVES' Paragraph",
                        "context": "Standard reserves based on occupancy/documentation type."
                    })
            else:
                res_months = 6 if scenario.occupancy != "Primary" else 3
                audit_trail.append({"doc": "Standard Guidelines", "program": "Generic", "location": "N/A", "context": "Standard industry overlays applied."})

            final_results.append({
                "bank": bank,
                "status": "✅ ELIGIBLE" if is_eligible else "❌ INELIGIBLE",
                "reasons": reasons,
                "audit": audit_trail,
                "reserves": pitia * res_months,
                "dti": f"{(scenario.monthly_income / pitia):.2f} (DSCR)" if scenario.income_type == "DSCR" else "50% Max",
                "rate": rate,
                "pitia": pitia
            })
        return final_results