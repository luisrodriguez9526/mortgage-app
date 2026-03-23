import streamlit as st
import os
from pydantic import BaseModel, Field
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# ==========================================
# 1. THE MATCHING ENGINE (DATA MODEL)
# ==========================================
# This defines the "Bouncer" that was causing your error.
# We added 'income_type' here so Pydantic is satisfied.
class MortgageScenario(BaseModel):
    fico: int
    ltv: float
    loan_amount: float
    occupancy: str
    income_type: str  # <--- THE FIX: Required field for the engine
    foreign_national: bool = False

# ==========================================
# 2. APP CONFIGURATION & DATABASE LOAD
# ==========================================
st.set_page_config(page_title="Non-QM Underwriting Engine", layout="wide")
st.title("🛡️ Local Mortgage Eligibility Engine")

@st.cache_resource
def load_vectorstore():
    # Ensure this path matches your local folder
    persist_dir = r"c:/Users/luisr/OneDrive/Desktop/Mortgage_Project/local_db"
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return Chroma(persist_directory=persist_dir, embedding_function=embeddings)

# Initialize Database
vectorstore = load_vectorstore()

# ==========================================
# 3. SIDEBAR: SCENARIO INPUTS
# ==========================================
st.sidebar.header("Loan Scenario")
fico_input = st.sidebar.number_input("Borrower FICO Score", value=700, min_value=300, max_value=850)
ltv_input = st.sidebar.number_input("LTV %", value=80.0, step=0.1)
loan_amt_input = st.sidebar.number_input("Loan Amount ($)", value=500000, step=25000)
occupancy_input = st.sidebar.selectbox("Occupancy", ["Primary Residence", "Second Home", "Investment"])

# This selection will be passed as 'income_type' to the engine
doc_type_input = st.sidebar.selectbox("Income Type", 
    ["Bank Statements", "DSCR", "1099", "Full Doc", "P&L Only", "Asset Depletion"]
)

fn_toggle = st.sidebar.toggle("Foreign National", value=False)

# ==========================================
# 4. EXECUTION LOGIC (THE "BRAIN")
# ==========================================
if st.button("Run Eligibility Analysis"):
    try:
        # STEP A: Create and Validate the Scenario object
        # This resolves the 'income_type' missing error
        scenario = MortgageScenario(
            fico=fico_input,
            ltv=ltv_input,
            loan_amount=loan_amt_input,
            occupancy=occupancy_input,
            income_type=doc_type_input,
            foreign_national=fn_toggle
        )

        # STEP B: Initialize Local LLM (Ollama)
        # Ensure you ran 'ollama pull llama3.2' in your terminal
        llm = Ollama(model="llama3.2", temperature=0)

        # STEP C: Define the Underwriting Prompt
        template = """
        You are a Senior Mortgage Underwriter. Use the guideline context below to evaluate eligibility.
        
        CONTEXT FROM LENDERS:
        {context}
        
        BORROWER SCENARIO:
        - FICO: {fico}
        - LTV: {ltv}%
        - Income Type: {income_type}
        - Occupancy: {occupancy}
        - Loan Amount: ${loan_amt}
        
        YOUR TASK:
        Analyze which lenders are ELIGIBLE based on the text. For each lender found:
        1. **Lender Name**
        2. **Status** (Eligible / Ineligible / Exception Needed)
        3. **Reasoning** (Cite specific FICO/LTV/Income rules from the context)
        4. **Required Documents** (List what is needed for {income_type})
        
        If information for a specific lender isn't in the context, do not make it up.
        """

        # Search the database specifically for the income type and LTV
        search_query = f"{scenario.income_type} guidelines for {scenario.ltv} LTV and {scenario.fico} FICO"

        # Setup the AI Retrieval Chain
        prompt = PromptTemplate(
            template=template, 
            input_variables=["context"],
            partial_variables={
                "fico": scenario.fico,
                "ltv": scenario.ltv,
                "income_type": scenario.income_type,
                "occupancy": scenario.occupancy,
                "loan_amt": f"{scenario.loan_amount:,}"
            }
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 7}),
            chain_type_kwargs={"prompt": prompt}
        )

        with st.spinner("Llama 3.2 is scanning 2,000+ guideline segments..."):
            response = qa_chain.invoke(search_query)
            st.success("Analysis Complete")
            st.markdown("## Underwriting Eligibility Report")
            st.markdown(response["result"])

    except Exception as e:
        st.error(f"Error: {e}")

# ==========================================
# 5. SOURCE TRACKING (FOR VERIFICATION)
# ==========================================
with st.expander("View Referenced Guideline Chunks"):
    # Re-run search to show the raw text sources
    raw_docs = vectorstore.similarity_search(doc_type_input, k=3)
    for d in raw_docs:
        st.info(f"Source: {os.path.basename(d.metadata.get('source', 'Unknown'))}")
        st.text(d.page_content)