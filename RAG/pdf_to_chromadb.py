import os
import glob
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ---------------- CONFIG ----------------
PDF_FOLDER = "/tmp/rag_folder_data"
CHROMA_DB_PATH = "/tmp/rag_folder_langchian_db"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 3
# --------------------------------------


def extract_text_from_pdfs(pdf_folder):
    documents = []
    pdf_files = glob.glob(os.path.join(pdf_folder, "**/*.pdf"), recursive=True)

    print(f"Found {len(pdf_files)} PDF file(s)")

    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path}")
        reader = PdfReader(pdf_path)

        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text_parts.append(page_text)
            else:
                print(f"⚠️ Empty text on page {i + 1}")

        full_text = "\n".join(text_parts)

        if not full_text.strip():
            print(f"❌ No extractable text in {pdf_path}")
            continue

        print(f"✅ Extracted {len(full_text)} characters")

        documents.append({
            "content": full_text,
            "source": pdf_path,
            "filename": os.path.basename(pdf_path)
        })

    return documents


def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    chunked_docs = []

    for doc in documents:
        chunks = splitter.split_text(doc["content"])
        print(f"📄 {doc['filename']} → {len(chunks)} chunks")

        for chunk in chunks:
            if chunk.strip():
                chunked_docs.append({
                    "content": chunk,
                    "source": doc["source"],
                    "filename": doc["filename"]
                })

    print(f"✅ Total chunks: {len(chunked_docs)}")
    return chunked_docs

def build_and_test_chroma(chunked_docs):
    if not chunked_docs:
        print("❌ No chunks to store")
        return

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"}
    )

    print("\nCreating Chroma DB...")
    db = Chroma.from_texts(
        texts=[d["content"] for d in chunked_docs],
        metadatas=[{
            "source": d["source"],
            "filename": d["filename"]
        } for d in chunked_docs],
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH,
        collection_name="pdf_documents"
    )

    print("✅ Chroma DB created")

    # --------------------------------------------------
    # 🔍 SELF-RETRIEVAL TEST (NO USER INPUT)
    # --------------------------------------------------

    print("\n🔍 Running self-retrieval test")

    # Pick a middle chunk (avoid headers/footers)
    test_chunk = chunked_docs[len(chunked_docs) // 2]
    test_text = test_chunk["content"]

    # Take a slice to simulate a real query
    query = test_text[:300]

    print("\nQuery text (from PDF itself):")
    print("-" * 60)
    print(query)
    print("-" * 60)

    results = db.similarity_search_with_score(query, k=3)

    if not results:
        print("❌ No results returned — indexing FAILED")
        return

    for i, (doc, score) in enumerate(results, 1):
        print(f"\nResult {i}")
        print(f"Score (lower = better): {score:.6f}")
        print(f"Source file: {doc.metadata.get('filename')}")
        print("-" * 60)
        print(doc.page_content[:500])
        print("-" * 60)

    # Sanity assertion
    best_score = results[0][1]
    if best_score < 0.2:
        print("\n✅ SELF-RETRIEVAL PASSED (excellent match)")
    elif best_score < 0.5:
        print("\n⚠️ SELF-RETRIEVAL PARTIAL (acceptable)")
    else:
        print("\n❌ SELF-RETRIEVAL FAILED (check embeddings / text quality)")


def main():
    print("=" * 60)
    print("PDF → Chroma → Immediate Search Test")
    print("=" * 60)

    documents = extract_text_from_pdfs(PDF_FOLDER)
    if not documents:
        print("❌ No valid documents found")
        return

    chunks = chunk_documents(documents)
    build_and_test_chroma(chunks)


if __name__ == "__main__":
    main()
