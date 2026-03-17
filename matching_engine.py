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

class MortgageIntelligenceEngine:
    def __init__(self, db_path="./mortgage_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="lender_guidelines")

    def get_market_rate(self, fico: int, is_fn: bool, occupancy: str, inc_type: str) -> float:
        # Base pricing tiers based on FICO
        if is_fn: base_rate = 9.25 if fico == 0 else 8.99
        elif fico >= 760: base_rate = 7.15
        elif fico >= 700: base_rate = 7.50
        elif fico >= 660: base_rate = 7.99
        else: base_rate = 8.50
        
        # Non-QM Income "Hits" (Adjustments)
        if inc_type == "Bank Statements": base_rate += 0.50
        if inc_type == "1099": base_rate += 0.25
        if inc_type == "DSCR": base_rate += 0.875
        
        # Investment Hit
        if occupancy == "Investment": base_rate += 0.375
        
        return base_rate

    def calculate_pitia(self, loan_amount: float, rate: float):
        mr = (rate / 100) / 12
        pi = loan_amount * (mr * (1 + mr)**360) / ((1 + mr)**360 - 1)
        # Standard estimate for Taxes/Insurance
        ti = ((loan_amount / 0.8) * 0.012) / 12 
        return pi + ti

    def run_analysis(self, scenario: MortgageScenario):
        rate = self.get_market_rate(scenario.fico, scenario.is_foreign_national, scenario.occupancy, scenario.income_type)
        pitia = self.calculate_pitia(scenario.loan_amount, rate)
        
        # Reserves logic: 12mo FN, 6mo Investment/Self-Employed, 3mo W2
        res_months = 12 if scenario.is_foreign_national else 6 if scenario.income_type in ["Bank Statements", "1099"] else 3
        reserves = pitia * res_months
        
        is_eligible = True
        reasons = []

        # Eligibility Checks
        if scenario.ltv > 90:
            is_eligible = False
            reasons.append(f"LTV {scenario.ltv:.1f}% exceeds max 90% limit.")
        
        if scenario.income_type != "DSCR":
            dti = ((pitia + scenario.other_debts) / scenario.monthly_income) * 100 if scenario.monthly_income > 0 else 0
            if dti > 50 and not scenario.is_foreign_national:
                is_eligible = False
                reasons.append(f"DTI {dti:.1f}% exceeds 50% limit.")
        else:
            dti = 0 # Placeholder for DSCR

        lenders = ["ARC HOME", "CHAMPIONS", "JMAC"]
        return [{
            "bank": b, 
            "status": "✅ ELIGIBLE" if is_eligible else "❌ INELIGIBLE",
            "reasons": reasons,
            "reserves": reserves,
            "dti": "N/A" if scenario.income_type == "DSCR" else f"{dti:.1f}%",
            "rate": rate,
            "pitia": pitia
        } for b in lenders]