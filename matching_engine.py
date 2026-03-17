import chromadb
import re
import os
from pydantic import BaseModel
from typing import List

class MortgageScenario(BaseModel):
    name: str           
    fico: int 
    ltv: float
    loan_amount: float
    monthly_income: float
    other_debts: float
    property_type: str 
    loan_purpose: str   
    occupancy: str      
    income_type: str    
    is_foreign_national: bool
    state: str
    interest_rate: float = 0.0 

class MortgageIntelligenceEngine:
    def __init__(self, db_path="./mortgage_db"):
        abs_db_path = os.path.abspath(db_path)
        self.client = chromadb.PersistentClient(path=abs_db_path)
        self.collection = self.client.get_or_create_collection(name="lender_guidelines")

    def get_market_rate(self, fico: int, is_fn: bool, occupancy: str) -> float:
        if is_fn:
            base_rate = 9.25 if fico == 0 else 8.99
        else:
            if fico == 0: base_rate = 9.50 
            elif fico >= 760: base_rate = 7.15
            elif fico >= 720: base_rate = 7.45
            elif fico >= 700: base_rate = 7.65
            elif fico >= 680: base_rate = 7.85
            elif fico >= 660: base_rate = 8.15
            else: base_rate = 8.75
        
        if occupancy == "Investment":
            base_rate += 0.375
        return base_rate

    def calculate_pitia(self, loan_amount: float, rate: float):
        monthly_rate = (rate / 100) / 12
        pi = loan_amount * (monthly_rate * (1 + monthly_rate) ** 360) / ((1 + monthly_rate) ** 360 - 1)
        est_value = loan_amount / 0.8 
        ti = (est_value * 0.015) / 12
        return pi + ti

    def calculate_reserves(self, pitia: float, occupancy: str, is_fn: bool) -> float:
        months = 12 if is_fn else (6 if occupancy == "Investment" else 3)
        return pitia * months

    def run_analysis(self, scenario: MortgageScenario):
        all_data = self.collection.get(include=["metadatas"])
        metadatas = all_data['metadatas'] if all_data and all_data['metadatas'] else []
        lenders = sorted(list({m.get("bank") for m in metadatas if m.get("bank")}))
        if not lenders: lenders = ["ARC HOME", "CHAMPIONS", "JMAC"]

        scenario.interest_rate = self.get_market_rate(scenario.fico, scenario.is_foreign_national, scenario.occupancy)
        pitia = self.calculate_pitia(scenario.loan_amount, scenario.interest_rate)
        reserves = self.calculate_reserves(pitia, scenario.occupancy, scenario.is_foreign_national)
        dti_ratio = ((pitia + scenario.other_debts) / scenario.monthly_income) * 100 if scenario.monthly_income > 0 else 0
        
        results_list = []
        for bank in lenders:
            results = self.collection.query(
                query_texts=[f"{scenario.loan_purpose} {scenario.income_type} {scenario.occupancy} guidelines"], 
                n_results=5, where={"bank": bank}
            )
            docs = results['documents'][0] if results and results['documents'] else []
            score, reasons = 100, []

            if not scenario.is_foreign_national and dti_ratio > 50:
                score -= 100
                reasons.append(f"DTI {dti_ratio:.1f}% exceeds max.")

            results_list.append({
                "bank": bank, 
                "status": "✅ ELIGIBLE" if score > 90 else "❌ NOT ELIGIBLE",
                "reasons": list(set(reasons)),
                "dti": "N/A" if scenario.is_foreign_national else f"{dti_ratio:.1f}%",
                "reserves": reserves,
                "pitia": pitia
            })
        return results_list