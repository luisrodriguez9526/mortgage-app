import os
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# 1. THE DATA MODEL (The "Bouncer")
# This defines exactly what fields the App MUST provide.
class MortgageScenario(BaseModel):
    fico: int
    ltv: float
    loan_amount: float
    occupancy: str
    income_type: str  # <--- Added this to fix your ValidationError
    foreign_national: bool = False

# 2. THE ENGINE CLASS
class GuidelineEngine:
    def __init__(self):
        # Setup paths
        self.db_dir = r"c:/Users/luisr/OneDrive/Desktop/Mortgage_Project/local_db"
        
        # Load the same embeddings used during ingestion
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Connect to your local ChromaDB
        self.vectorstore = Chroma(
            persist_directory=self.db_dir, 
            embedding_function=self.embeddings
        )
        
        # Initialize Local LLM (Ollama)
        self.llm = Ollama(model="llama3.2", temperature=0)

    def run_analysis(self, scenario: MortgageScenario):
        """
        Takes a validated MortgageScenario and returns an AI analysis.
        """
        
        # Custom Underwriting Prompt
        template = """
        You are a Senior Mortgage Underwriter. Use the provided guideline context to evaluate the loan.
        
        CONTEXT FROM LENDERS:
        {context}
        
        BORROWER SCENARIO:
        - FICO: {fico}
        - LTV: {ltv}%
        - Income Type: {income_type}
        - Occupancy: {occupancy}
        - Loan Amount: ${loan_amt}
        
        YOUR TASK:
        Identify which lenders from the context are ELIGIBLE. 
        For each lender found in the text, list:
        1. **Lender Name**
        2. **Status** (Eligible/Ineligible)
        3. **Specific Reason** (e.g., "AD Mortgage allows 80% LTV at 660 FICO")
        4. **Required Docs** (e.g., "Provide 12 months personal bank statements")
        
        If no specific lender is found in the context, summarize the general rules found.
        """

        # Create the search query for the database based on the scenario
        # We search specifically for the Income Type (e.g., "Bank Statements")
        search_query = f"{scenario.income_type} guidelines {scenario.ltv} LTV {scenario.fico} FICO"

        # Setup the Retrieval Chain
        prompt = PromptTemplate(
            template=template, 
            input_variables=["context"],
            partial_variables={
                "fico": scenario.fico,
                "ltv": scenario.ltv,
                "income_type": scenario.income_type,
                "occupancy": scenario.occupancy,
                "loan_amt": scenario.loan_amount
            }
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 6}),
            chain_type_kwargs={"prompt": prompt}
        )

        # Run the AI
        response = qa_chain.invoke(search_query)
        return response["result"]

# This allows you to test the engine standalone without the App
if __name__ == "__main__":
    engine = GuidelineEngine()
    test_case = MortgageScenario(
        fico=700,
        ltv=80.0,
        loan_amount=500000,
        occupancy="Primary",
        income_type="Bank Statements"
    )
    print(engine.run_analysis(test_case))