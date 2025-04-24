from datetime import datetime
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from logger_config import setup_logger
import chromadb

import os
logger = setup_logger(__name__)
class DocumentRetriever:
    def __init__(self,api_key=None):
       
        self.embeddings = OpenAIEmbeddings(openai_api_key=api_key or os.getenv("OPENAI_API_KEY"))
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./chroma_db")
        # Create or get collection
        self.vector_store = Chroma(
            client=self.client,
            collection_name="pdf_documents",
            embedding_function=self.embeddings
        )
        logger.info("Vector store initialized")
    def index_document(self, texts, metadatas=None,ids=None):
        """Indexes the full document into ChromaDB."""
        logger.info(f"Indexing {len(texts)} text chunks")
        try:
            self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas if metadatas else None,
                ids=ids if ids else None
            )
            logger.info("Successfully indexed document")
        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            raise

    def query(self, question, top_k=1, filter_criteria=None):
        return self.vector_store.similarity_search(
            query=question,
            k=top_k,
            filter=filter_criteria  # Filters by metadata
        )
    def save_summary(self, doc_id: str, summary: str) -> None:
        """Updates document summary in ChromaDB collection.
        
        Args:
            doc_id: Document ID to update
            summary: New summary text (max 10,000 chars)
            
        Raises:
            ValueError: For invalid inputs
            RuntimeError: If update fails
        """
        # Input validation
        if not isinstance(doc_id, str) or not doc_id.strip():
            raise ValueError("Invalid doc_id")
        
        summary = str(summary).strip()
        if not summary:
            raise ValueError("Summary cannot be empty")
        if len(summary) > 10000:
            raise ValueError("Summary exceeds maximum length (10,000 chars)")

        try:
            # In Chroma v0.4+, the collection is accessed directly
            # No need for get_collection() - self.vector_store IS the collection
            
            # 1. Find documents matching our doc_id
            results = self.vector_store.get(
                where={"doc_id": doc_id},
                include=["metadatas", "documents"] 
            )
            
            if not results["ids"]:
                raise RuntimeError(f"No document found with doc_id {doc_id}")
            
            # 2. Prepare updated metadata
            updated_metadatas = [
                {**meta, "summary": summary, "last_updated": datetime.utcnow().isoformat()}
                for meta in results["metadatas"]
            ]
            
            # 3. Chroma requires delete->re-add for updates
            self.vector_store.delete(ids=results["ids"])
            print(results["documents"])
            print(updated_metadatas)
            self.vector_store.add_texts(
                ids=results["ids"],
                texts=results["documents"],
                metadatas=updated_metadatas
            )
            
            logger.info(f"Updated summary for {len(results['ids'])} chunks (doc_id: {doc_id})")
            
        except Exception as e:
            logger.error(f"Update failed for doc_id {doc_id}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Summary update failed: {str(e)}") from e