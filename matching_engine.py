import chromadb
import re
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
        # 1. Base FICO Pricing
        if is_fn: base_rate = 9.25 if fico == 0 else 8.99
        elif fico >= 760: base_rate = 7.15
        elif fico >= 700: base_rate = 7.55
        elif fico >= 660: base_rate = 7.99
        else: base_rate = 8.50
        
        # 2. Income Type Adjustments
        if inc_type == "Bank Statements": base_rate += 0.50
        if inc_type == "1099": base_rate += 0.25
        if inc_type == "DSCR": base_rate += 0.875
        
        # 3. Occupancy & Purpose Adjustments
        if occupancy == "Second Home": base_rate += 0.250
        if occupancy == "Investment": base_rate += 0.375
        if purpose == "Cash-Out Refi": base_rate += 0.500
        
        return base_rate

    def calculate_pitia(self, loan_amount: float, rate: float):
        mr = (rate / 100) / 12
        pi = loan_amount * (mr * (1 + mr)**360) / ((1 + mr)**360 - 1)
        ti = ((loan_amount / 0.8) * 0.015) / 12 # 1.5% Est for T&I
        return pi + ti

    def run_analysis(self, scenario: MortgageScenario):
        rate = self.get_market_rate(scenario.fico, scenario.is_foreign_national, 
                                   scenario.occupancy, scenario.income_type, scenario.loan_purpose)
        pitia = self.calculate_pitia(scenario.loan_amount, rate)
        
        # Reserves logic
        res_months = 12 if scenario.is_foreign_national else 6 if scenario.occupancy != "Primary" else 3
        reserves = pitia * res_months
        
        is_eligible = True
        reasons = []

        # Guideline Checks
        if scenario.ltv > 90 and scenario.loan_purpose == "Purchase":
            is_eligible = False
            reasons.append(f"LTV {scenario.ltv:.1f}% exceeds 90% Purchase cap.")
        if scenario.ltv > 80 and scenario.loan_purpose == "Cash-Out Refi":
            is_eligible = False
            reasons.append(f"LTV {scenario.ltv:.1f}% exceeds 80% Cash-Out cap.")

        dti = ((pitia + scenario.other_debts) / scenario.monthly_income) * 100 if scenario.monthly_income > 0 else 0
        if scenario.income_type != "DSCR" and dti > 50 and not scenario.is_foreign_national:
            is_eligible = False
            reasons.append(f"DTI {dti:.1f}% exceeds 50% max.")

        lenders = ["ARC HOME", "CHAMPIONS", "JMAC"]
        return [{
            "bank": b, 
            "status": "✅ ELIGIBLE" if is_eligible else "❌ INELIGIBLE",
            "reasons": reasons,
            "reserves": reserves,
            "dti": "N/A (DSCR)" if scenario.income_type == "DSCR" else f"{dti:.1f}%",
            "rate": rate,
            "pitia": pitia
        } for b in lenders]