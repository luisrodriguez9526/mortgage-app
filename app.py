import streamlit as st
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field

# 1. DEFINE THE DATA MODEL (This prevents the ValidationError)
class MortgageScenario(BaseModel):
    fico: int
    ltv: float
    loan_amount: float
    occupancy: str
    income_type: str  # The missing field from your error
    foreign_national: bool = False

# 2. PAGE CONFIG
st.set_page_config(page_title="Mortgage Underwriting Engine", layout="wide")
st.title("🛡️ Local Underwriting Engine")

# 3. LOAD LOCAL DATABASE
@st.cache_resource
def load_db():
    persist_dir = r"c:/Users/luisr/OneDrive/Desktop/Mortgage_Project/local_db"
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return Chroma(persist_directory=persist_dir, embedding_function=embeddings)

vectorstore = load_db()

# 4. SIDEBAR INPUTS
st.sidebar.header("Scenario Details")
fico = st.sidebar.number_input("FICO Score", value=667)
ltv = st.sidebar.number_input("LTV %", value=80.0)
loan_amt = st.sidebar.number_input("Loan Amount", value=500000)
occupancy = st.sidebar.selectbox("Occupancy", ["Primary", "Second Home", "Investment"])
doc_type = st.sidebar.selectbox("Income Type", ["Bank Statements", "DSCR", "Full Doc", "1099"])
foreign_national = st.sidebar.checkbox("Foreign National", value=False)

# 5. RUN ANALYSIS
if st.button("Check Eligibility"):
    try:
        # VALIDATION STEP: Create the scenario object correctly
        scenario = MortgageScenario(
            fico=fico,
            ltv=ltv,
            loan_amount=loan_amt,
            occupancy=occupancy,
            income_type=doc_type,
            foreign_national=foreign_national
        )

        # Connect to Local LLM (Ollama)
        llm = Ollama(model="llama3.2")

        # Custom Underwriter Prompt
        template = """
        You are a Mortgage Underwriter. Based on the guidelines below, determine eligibility.
        Context: {context}
        Scenario: {question}
        
        Provide:
        - Eligibility Status
        - Specific LTV/FICO limits found in the text
        - Required Documents for {income_type}
        """
        
        # Format the query for the database
        query_text = f"FICO {scenario.fico}, LTV {scenario.ltv}, {scenario.income_type} guidelines"
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
        )

        with st.spinner("Analyzing guidelines..."):
            response = qa_chain.invoke(query_text)
            st.markdown("### Underwriting Analysis")
            st.write(response["result"])

    except Exception as e:
        st.error(f"Error: {e}")

# 6. SOURCE VIEW
with st.expander("View Raw Guidelines"):
    docs = vectorstore.similarity_search(doc_type, k=3)
    for doc in docs:
        st.caption(f"Source: {doc.metadata.get('source')}")
        st.text(doc.page_content)