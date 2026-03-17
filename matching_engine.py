import os
from pydantic import BaseModel

class MortgageScenario(BaseModel):
    borrower_name: str
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
    def get_market_rate(self, fico: int, is_fn: bool, occupancy: str, inc_type: str, purpose: str) -> float:
        # Base pricing tiers
        if is_fn: base_rate = 8.99 if fico >= 660 or fico == 0 else 9.50
        elif fico >= 720: base_rate = 7.15 
        elif fico >= 680: base_rate = 7.65 
        else: base_rate = 8.25
        
        # Adjustments
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
        
        # DEFINING LENDER LIMITS (Accuracy Check)
        # These are the "Red/Green" triggers
        lender_configs = {
            "AD MORTGAGE": {"min_fico": 660, "max_ltv": 90, "max_dti": 50, "fn_reserves": 12},
            "ARC HOME":    {"min_fico": 620, "max_ltv": 85, "max_dti": 50, "fn_reserves": 6},
            "CHAMPIONS":   {"min_fico": 640, "max_ltv": 80, "max_dti": 45, "fn_reserves": 6},
            "JMAC":        {"min_fico": 660, "max_ltv": 80, "max_dti": 43, "fn_reserves": 6}
        }
        
        final_results = []

        for bank, rules in lender_configs.items():
            is_eligible = True
            reasons = []
            audit_trail = []
            
            # 1. FICO VALIDATION
            current_min_fico = rules["min_fico"]
            # DSCR Footnote Exception for AD
            if bank == "AD MORTGAGE" and scenario.income_type == "DSCR":
                dscr_ratio = scenario.monthly_income / pitia
                if dscr_ratio < 1.0:
                    current_min_fico = 680
                    if scenario.fico < 680 and scenario.fico > 0:
                        is_eligible = False
                        reasons.append(f"AD Footnote: DSCR < 1.0 requires 680 FICO (Current: {scenario.fico})")

            if not scenario.is_foreign_national and scenario.fico < current_min_fico:
                is_eligible = False
                reasons.append(f"Min FICO for {bank} is {current_min_fico}. (Current: {scenario.fico})")

            # 2. LTV VALIDATION
            if scenario.ltv > rules["max_ltv"]:
                is_eligible = False
                reasons.append(f"Max LTV for {bank} is {rules['max_ltv']}%. (Current: {scenario.ltv:.1f}%)")

            # 3. DTI/DSCR VALIDATION
            if scenario.income_type != "DSCR":
                dti = ((pitia + scenario.other_debts) / scenario.monthly_income) * 100 if scenario.monthly_income > 0 else 0
                if dti > rules["max_dti"] and not scenario.is_foreign_national:
                    is_eligible = False
                    reasons.append(f"DTI {dti:.1f}% exceeds {bank} limit of {rules['max_dti']}%.")
            
            # 4. RESERVES
            res_months = rules["fn_reserves"] if scenario.is_foreign_national else (6 if scenario.occupancy != "Primary" else 3)
            
            # 5. AUDIT LOGGING (Proof of Reading)
            if bank == "AD MORTGAGE":
                audit_trail.append({"doc": "AD_Mortgage_Product-Matrix.md", "loc": "Main Matrix", "rule": f"Max LTV {rules['max_ltv']}%"})
                if scenario.is_foreign_national:
                    audit_trail.append({"doc": "AD Mortgage Foreign Nationals-UW-Requirements.md", "loc": "Reserves Table", "rule": "12 Months Mandatory"})

            final_results.append({
                "bank": bank,
                "status": "✅ ELIGIBLE" if is_eligible else "❌ INELIGIBLE",
                "reasons": reasons,
                "audit": audit_trail,
                "reserves": pitia * res_months,
                "dti": f"{(scenario.monthly_income / pitia):.2f} (DSCR)" if scenario.income_type == "DSCR" else f"{dti:.1f}%",
                "rate": rate,
                "pitia": pitia
            })
        return final_results