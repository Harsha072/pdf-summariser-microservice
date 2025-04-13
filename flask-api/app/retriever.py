from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb
import os

class DocumentRetriever:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./chroma_db")
        # Create or get collection
        self.vector_store = Chroma(
            client=self.client,
            collection_name="pdf_documents",
            embedding_function=self.embeddings
        )

    def index_document(self, text, metadata=None):
        """Indexes the full document into ChromaDB."""
        if metadata is None:
            metadata = {}
        self.vector_store.add_texts(
            texts=[text],
            metadatas=[metadata]
        )

    def query(self, question, top_k=1, filter_criteria=None):
        return self.vector_store.similarity_search(
            query=question,
            k=top_k,
            filter=filter_criteria  # Filters by metadata
        )