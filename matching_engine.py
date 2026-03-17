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
        # Base pricing tiers
        if is_fn: base_rate = 9.25 if fico == 0 else 8.99
        elif fico >= 760: base_rate = 7.15
        elif fico >= 700: base_rate = 7.65
        else: base_rate = 8.25
        
        # Income Type Adjustments (Non-QM hits)
        if inc_type == "Bank Statements": base_rate += 0.25
        if inc_type == "DSCR": base_rate += 0.75
        if occupancy == "Investment": base_rate += 0.375
        
        return base_rate

    def calculate_pitia(self, loan_amount: float, rate: float):
        mr = (rate / 100) / 12
        pi = loan_amount * (mr * (1 + mr)**360) / ((1 + mr)**360 - 1)
        ti = ((loan_amount / 0.8) * 0.015) / 12
        return pi + ti

    def run_analysis(self, scenario: MortgageScenario):
        rate = self.get_market_rate(scenario.fico, scenario.is_foreign_national, scenario.occupancy, scenario.income_type)
        pitia = self.calculate_pitia(scenario.loan_amount, rate)
        
        # Reserves Logic
        res_months = 12 if scenario.is_foreign_national else 6 if scenario.occupancy == "Investment" else 3
        reserves = pitia * res_months
        
        # DTI vs DSCR Logic
        is_eligible = True
        reason = ""
        
        if scenario.income_type == "DSCR":
            # Assuming rent is 1.2x the payment for this example
            dti_display = "N/A (DSCR)"
        else:
            dti = ((pitia + scenario.other_debts) / scenario.monthly_income) * 100 if scenario.monthly_income > 0 else 0
            dti_display = f"{dti:.1f}%"
            if dti > 50 and not scenario.is_foreign_national:
                is_eligible = False
                reason = "DTI exceeds 50% limit."

        lenders = ["ARC HOME", "CHAMPIONS", "JMAC"]
        return [{
            "bank": b, 
            "status": "✅ ELIGIBLE" if is_eligible else "❌ INELIGIBLE",
            "reason": reason,
            "reserves": reserves,
            "dti": dti_display,
            "rate": rate,
            "pitia": pitia
        } for b in lenders]