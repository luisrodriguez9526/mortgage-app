def run_analysis(self, scenario: MortgageScenario):
        rate = self.get_market_rate(scenario.fico, scenario.is_foreign_national, 
                                   scenario.occupancy, scenario.income_type, scenario.loan_purpose)
        pitia = self.calculate_pitia(scenario.loan_amount, rate)
        
        lenders = ["ARC HOME", "CHAMPIONS", "JMAC", "AD MORTGAGE"]
        final_results = []

        for bank in lenders:
            is_eligible = True
            reasons = []
            audit_trail = [] # Enhanced structural citation list
            
            if bank == "AD MORTGAGE":
                # LTV Rule Citation
                if scenario.ltv > 90:
                    is_eligible = False
                    reasons.append(f"Max LTV is 90%. Current: {scenario.ltv:.1f}%")
                    audit_trail.append({
                        "doc": "AD_Mortgage_Product-Matrix.md",
                        "program": "Non-QM Products (All)",
                        "location": "Main Eligibility Table -> Row: 'Max LTV'",
                        "context": "Matrix specifies a hard ceiling of 90% for Prime/Super Prime tiers."
                    })

                # DSCR Calculation & Footnote Citation
                if scenario.income_type == "DSCR":
                    dscr_ratio = scenario.monthly_income / pitia
                    if dscr_ratio < 1.0 and scenario.fico < 680:
                        is_eligible = False
                        reasons.append("DSCR < 1.0 requires 680 FICO.")
                        audit_trail.append({
                            "doc": "AD_Mortgage_Product-Matrix.md",
                            "program": "DSCR / Foreign National DSCR",
                            "location": "Table 1 -> Column: 'DSCR' -> Row: 'Income Employment Verification'",
                            "context": "Footnote/Note in cell: 'DSCR < 1 requires min FICO 680'"
                        })

                # Foreign National Reserve Requirement Citation
                if scenario.is_foreign_national:
                    res_months = 12
                    audit_trail.append({
                        "doc": "AD Mortgage Foreign Nationals-UW-Requirements.md",
                        "program": "Wholesale Foreign National",
                        "location": "Header Table -> Column: 'Reserves'",
                        "context": "Explicitly stated as '12 months' in the Underwriting Requirements summary table."
                    })
                else:
                    # General Reserve Citation
                    res_months = 6 if scenario.occupancy != "Primary" else 3
                    audit_trail.append({
                        "doc": "AD Mortgage Non-QM-Loan-Eligibility-Guidelines.md",
                        "program": "General Non-QM",
                        "location": "Section 6.8.6 -> Paragraph: 'RESERVES'",
                        "context": "Standard reserve requirements based on occupancy type."
                    })

            # Placeholder for other lenders
            else:
                res_months = 6 if scenario.occupancy != "Primary" else 3
                audit_trail.append({"doc": "Standard Guideline", "program": "Generic", "location": "N/A", "context": "Industry standard logic."})

            final_results.append({
                "bank": bank,
                "status": "✅ ELIGIBLE" if is_eligible else "❌ INELIGIBLE",
                "reasons": reasons,
                "audit": audit_trail,
                "reserves": pitia * res_months,
                "dti": f"{(scenario.monthly_income / pitia):.2f}" if scenario.income_type == "DSCR" else "Calculated",
                "rate": rate,
                "pitia": pitia
            })
        return final_results