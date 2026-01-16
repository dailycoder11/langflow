from mcp.server.fastmcp import FastMCP
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# ---------------- CONFIG ----------------
CHROMA_PATH = "/tmp/rag_folder_langchian_db"
COLLECTION_NAME = "pdf_documents"  # 🔴 MUST MATCH INGESTION
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 3
# ----------------------------------------

# Create MCP server
mcp = FastMCP("local-chroma-mcp")

# Load embedding + vector store ONCE
print("Loading embeddings...")
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

print("Loading Chroma DB...")
db = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embeddings,
    collection_name=COLLECTION_NAME
)

print(f"Chroma collection '{COLLECTION_NAME}' loaded")

@mcp.tool()
def document_search(query: str) -> dict:
    """
    Search internal documents for relevant information.

    Returns:
    {
      "max_score": float,
      "chunks": [str, ...]
    }
    """
    if not query or not query.strip():
        return {"max_score": 1.0, "chunks": []}

    results = db.similarity_search_with_score(query, k=TOP_K)

    if not results:
        return {"max_score": 1.0, "chunks": []}

    chunks = []
    scores = []

    for doc, score in results:
        chunks.append(doc.page_content)
        scores.append(score)

    return {
        "max_score": min(scores),   # lower = better
        "chunks": chunks
    }

if __name__ == "__main__":
    print("Starting MCP server with SSE transport")
    mcp.run(transport="sse")
