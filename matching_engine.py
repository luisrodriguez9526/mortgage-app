import chromadb
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
    def __init__(self, db_path="./mortgage_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="lender_guidelines")

    def get_market_rate(self, fico: int, is_fn: bool, occupancy: str, inc_type: str, purpose: str) -> float:
        # AD Mortgage Based Tiers
        if is_fn: 
            base_rate = 8.99 if fico >= 660 or fico == 0 else 9.50
        elif fico >= 720: base_rate = 7.15  # Super Prime
        elif fico >= 660: base_rate = 7.75  # Prime
        else: base_rate = 8.35             # Standard Non-QM
        
        # Income Type Hits (Based on AD Matrix)
        if inc_type in ["Bank Statements", "1099", "P&L"]: base_rate += 0.50
        if inc_type == "DSCR": base_rate += 0.875
        
        # Occupancy & Purpose Adjustments
        if occupancy == "Second Home": base_rate += 0.25
        if occupancy == "Investment": base_rate += 0.375
        if purpose == "Cash-Out Refi": base_rate += 0.50
        
        return base_rate

    def calculate_pitia(self, loan_amount: float, rate: float):
        mr = (rate / 100) / 12
        pi = loan_amount * (mr * (1 + mr)**360) / ((1 + mr)**360 - 1)
        # AD Mortgage typically uses 1.25% - 1.5% for Est. Taxes/Ins
        ti = ((loan_amount / 0.8) * 0.015) / 12 
        return pi + ti

    def run_analysis(self, scenario: MortgageScenario):
        rate = self.get_market_rate(scenario.fico, scenario.is_foreign_national, 
                                   scenario.occupancy, scenario.income_type, scenario.loan_purpose)
        pitia = self.calculate_pitia(scenario.loan_amount, rate)
        
        # AD SPECIFIC RESERVES: 12 Months for FN, 6 for Inv/Self-Employed, 3 for W2 Primary
        if scenario.is_foreign_national:
            res_months = 12
        elif scenario.occupancy != "Primary" or scenario.income_type in ["Bank Statements", "1099", "P&L"]:
            res_months = 6
        else:
            res_months = 3
            
        reserves = pitia * res_months
        
        is_eligible = True
        reasons = []

        # AD GUIDELINE CHECKS
        if scenario.is_foreign_national and scenario.fico > 0 and scenario.fico < 660:
            is_eligible = False
            reasons.append("AD Mortgage Foreign National requires min 660 FICO (if score exists).")

        if scenario.income_type == "DSCR":
            dscr_ratio = scenario.monthly_income / pitia
            dti_display = f"{dscr_ratio:.2f} (DSCR)"
            if dscr_ratio < 1.0 and scenario.fico < 680:
                is_eligible = False
                reasons.append("DSCR < 1.00 requires a minimum 680 FICO score.")
        else:
            dti = ((pitia + scenario.other_debts) / scenario.monthly_income) * 100 if scenario.monthly_income > 0 else 0
            dti_display = f"{dti:.1f}%"
            if dti > 50 and not scenario.is_foreign_national:
                is_eligible = False
                reasons.append("DTI exceeds 50% max limit for domestic borrowers.")

        if scenario.ltv > 90:
            is_eligible = False
            reasons.append("LTV exceeds 90% (AD Mortgage Max).")

        return [{
            "bank": "AD MORTGAGE", 
            "status": "✅ ELIGIBLE" if is_eligible else "❌ INELIGIBLE",
            "reasons": reasons,
            "reserves": reserves,
            "dti": dti_display,
            "rate": rate,
            "pitia": pitia
        }]