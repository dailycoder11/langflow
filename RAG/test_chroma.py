from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# ---------------- CONFIG ----------------
CHROMA_PATH = "/tmp/rag_folder_langchian_db"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "pdf_documents"   # 🔴 MUST MATCH
TOP_K = 3
# ----------------------------------------

def main():
    print("Loading embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    print("Loading Chroma DB...")
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME  # ✅ FIX
    )

    print("\nChroma DB loaded successfully.")
    print("-" * 60)

    while True:
        query = input("\nEnter a search query (or 'exit'): ")
        if query.lower() in ("exit", "quit"):
            break

        print("\nSearching...\n")

        results = db.similarity_search_with_score(query, k=TOP_K)

        if not results:
            print("❌ No results found.")
            continue

        for idx, (doc, score) in enumerate(results, start=1):
            print(f"\nResult {idx}")
            print(f"Score (lower is better): {score:.4f}")
            print("Source:", doc.metadata.get("filename"))
            print("-" * 60)
            print(doc.page_content[:500])
            print("-" * 60)

if __name__ == "__main__":
    main()
