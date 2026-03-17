import chromadb
import re
from datetime import datetime

# --- UI COLORS ---
CYAN, GREEN, RED, YELLOW = "\033[96m", "\033[92m", "\033[91m", "\033[93m"
BOLD, UNDERLINE, END = "\033[1m", "\033[4m", "\033[0m"

client = chromadb.PersistentClient(path="./mortgage_db")
collection = client.get_collection(name="lender_guidelines")

def clean_text(text):
    """Removes HTML tags and cleans whitespace for terminal display"""
    return re.sub(r'<[^>]+>', '', text).strip()

def run_engine():
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{BOLD}{'='*95}")
    print(f"🏠 PRO-STRATEGY ENGINE v6.6 | AUDIT & COMPLIANCE READY")
    print(f"RUN TIME: {run_time}")
    print(f"{'='*95}{END}")

    # 1. Inputs
    state = input(f"{BOLD}1. STATE (FL, TX, CA):{END} ").upper().strip() or "FL"
    purpose = input(f"{BOLD}2. PURPOSE (Purchase, Refi):{END} ").lower().strip() or "purchase"
    price = float(input(f"{BOLD}3. VALUE / PURCHASE PRICE ($):{END} ").replace(',', '') or 500000)
    loan = float(input(f"{BOLD}4. DESIRED LOAN AMOUNT ($):{END} ").replace(',', '') or 400000)
    fico = int(input(f"{BOLD}5. MIDDLE FICO SCORE:{END} ") or 700)
    doc = input(f"{BOLD}6. DOC TYPE (Full, 1099, Bank Stmt):{END} ").lower().strip() or "full"
    
    ltv = (loan / price) * 100
    print(f"\n📊 {BOLD}SCENARIO ANALYSIS:{END} {ltv:.2f}% LTV | {fico} FICO | {state}")

    # 2. Database Search
    query = f"{state} {doc} doc {fico} fico {ltv} ltv matrix overlays"
    results = collection.query(query_texts=[query], n_results=10)

    # 3. Processing & Audit Display
    print(f"\n{BOLD}🔎 AUDIT FINDINGS & SOURCE TRACE:{END}")
    seen = set()
    
    for i in range(len(results['documents'][0])):
        meta = results['metadatas'][0][i]
        bank = meta.get('bank', 'Unknown Bank')
        prog = meta.get('program', 'General')
        
        prog_key = f"{bank}{prog}"
        if prog_key in seen: continue
        
        # --- FLORIDA SPECIFIC STATUS CHECK ---
        status_color, status_text = GREEN, "✅ POTENTIAL MATCH"
        if state == "FL" and bank == "JMAC":
            if purpose == "purchase" and ltv > 85:
                status_color, status_text = RED, "🚫 DECLINED (FL PURCHASE LTV CAP)"
            elif "refi" in purpose and ltv > 80:
                status_color, status_text = RED, "🚫 DECLINED (FL REFI LTV CAP)"

        print(f"\n🏦 {BOLD}{bank} - {prog}{END} | {status_color}{BOLD}{status_text}{END}")
        
        # --- THE AUDIT TRACE BOX (Using .get() for Safety) ---
        print(f"   {CYAN}┌{'─'*85}┐")
        print(f"   │ {BOLD}SOURCE:{END} {meta.get('source', 'N/A')} | {BOLD}INDEXED:{END} {meta.get('date_indexed', 'Pre-v6.4 Data')}")
        print(f"   │ {BOLD}LOC:{END} Section: {meta.get('section', 'General')} | Page: {meta.get('page', '1')} | Para: {meta.get('paragraph', '1')}")
        print(f"   └{'─'*85}┘{END}")
        
        snippet = clean_text(results['documents'][0][i])
        print(f"   📑 {BOLD}GUIDELINE:{END} {snippet[:350]}...")
        print(f"{'-'*95}")
        
        seen.add(prog_key)

if __name__ == "__main__":
    run_engine()