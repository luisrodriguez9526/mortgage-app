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
        # Base pricing tiers
        if is_fn: base_rate = 8.99 if fico >= 660 or fico == 0 else 9.50
        elif fico >= 720: base_rate = 7.15 
        elif fico >= 660: base_rate = 7.75 
        else: base_rate = 8.35
        
        # Adjustments
        if inc_type in ["Bank Statements", "1099", "P&L"]: base_rate += 0.50
        if inc_type == "DSCR": base_rate += 0.875
        if occupancy == "Second Home": base_rate += 0.25
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
        
        # 1. Setup Lender List
        lenders = ["ARC HOME", "CHAMPIONS", "JMAC", "AD MORTGAGE"]
        final_results = []

        for bank in lenders:
            is_eligible = True
            reasons = []
            
            # --- GLOBAL CHECKS (Apply to all) ---
            if scenario.ltv > 90:
                is_eligible = False
                reasons.append(f"Max LTV is 90%. Current: {scenario.ltv:.1f}%")
            
            # --- LENDER SPECIFIC RULES (AD MORTGAGE) ---
            bank_reserves = pitia * (6 if scenario.occupancy != "Primary" else 3)
            
            if bank == "AD MORTGAGE":
                if scenario.is_foreign_national:
                    bank_reserves = pitia * 12 # AD Rule: 12mo for FN
                if scenario.income_type == "DSCR":
                    dscr_ratio = scenario.monthly_income / pitia
                    if dscr_ratio < 1.0 and scenario.fico < 680 and scenario.fico > 0:
                        is_eligible = False
                        reasons.append("AD Rule: DSCR < 1.0 requires 680 FICO")
            
            # --- INCOME/DTI CHECKS ---
            if scenario.income_type == "DSCR":
                dti_val = f"{(scenario.monthly_income / pitia):.2f} (DSCR)"
            else:
                dti = ((pitia + scenario.other_debts) / scenario.monthly_income) * 100 if scenario.monthly_income > 0 else 0
                dti_val = f"{dti:.1f}%"
                if dti > 50 and not scenario.is_foreign_national:
                    is_eligible = False
                    reasons.append("DTI exceeds 50% max")

            final_results.append({
                "bank": bank,
                "status": "✅ ELIGIBLE" if is_eligible else "❌ INELIGIBLE",
                "reasons": reasons,
                "reserves": bank_reserves,
                "dti": dti_val,
                "rate": rate,
                "pitia": pitia
            })

        return final_results