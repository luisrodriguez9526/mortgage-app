import os
import chromadb
import hashlib
from datetime import datetime
from langchain_text_splitters import MarkdownHeaderTextSplitter

# --- CONFIGURATION ---
DB_PATH = "./mortgage_db"
GUIDELINES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Guidelines")

# Define the hierarchy we want to capture
HEADERS_TO_SPLIT_ON = [
    ("#", "Header_1"),
    ("##", "Header_2"),
    ("###", "Header_3"),
    ("####", "Header_4"),
]

def get_deterministic_id(content, filename, index):
    """Creates a unique, repeatable ID based on content hash."""
    hash_obj = hashlib.md5(f"{filename}_{index}_{content[:50]}".encode())
    return f"doc_{hash_obj.hexdigest()}"

def run_ingestion():
    # 1. Setup Chroma
    client = chromadb.PersistentClient(path=DB_PATH)
    
    # We use a fresh start for the collection or get existing
    collection = client.get_or_create_collection(name="lender_guidelines")
    
    # 2. Setup Splitter
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS_TO_SPLIT_ON)
    
    if not os.path.exists(GUIDELINES_DIR):
        print(f"❌ Folder not found: {GUIDELINES_DIR}")
        return

    index_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    files = [f for f in os.listdir(GUIDELINES_DIR) if f.endswith('.md')]
    
    print(f"--- Starting Ingestion of {len(files)} files ---")

    for filename in files:
        fn_upper = filename.upper()
        
        # Determine Bank/Program (Improved logic)
        bank = "JMAC" if "JMAC" in fn_upper else "ARC HOME" if "ARC" in fn_upper else "CHAMPIONS"
        program = "NEWPORT" if "NEWPORT" in fn_upper else "ZUMA" if "ZUMA" in fn_upper else "GENERAL"
        
        file_path = os.path.join(GUIDELINES_DIR, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        # 3. Perform Hierarchical Split
        # This keeps the headers associated with the text blocks
        sections = splitter.split_text(raw_text)
        
        ids, docs, metadatas = [], [], []

        for i, section in enumerate(sections):
            # Construct a "Breadcrumb" for the AI's context
            # e.g., "Credit > Bankruptcy > Chapter 7"
            headers = [val for key, val in section.metadata.items() if "Header" in key]
            breadcrumb = " > ".join(headers)
            
            # We inject the context directly into the text for better vector retrieval
            enhanced_content = f"LENDER: {bank} | PROGRAM: {program}\nPATH: {breadcrumb}\nRULE: {section.page_content}"
            
            doc_id = get_deterministic_id(enhanced_content, filename, i)
            
            ids.append(doc_id)
            docs.append(enhanced_content)
            metadatas.append({
                "bank": bank,
                "program": program,
                "breadcrumb": breadcrumb,
                "source": filename,
                "date_indexed": index_date,
                **section.metadata # Keeps individual headers as metadata tags
            })

        # 4. Batch Upsert into Chroma
        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metadatas)
            print(f"✅ Processed {filename}: {len(ids)} chunks indexed.")

    print(f"\n🚀 DATABASE REBUILT. Ready for matching at {index_date}")

if __name__ == "__main__":
    run_ingestion()