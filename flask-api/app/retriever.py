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

    def split_text_into_chunks(self, text, chunk_size=500):
        """Splits text into smaller chunks of a specified size."""
        words = text.split()
        chunks = [
            " ".join(words[i:i + chunk_size])
            for i in range(0, len(words), chunk_size)
        ]
        return chunks
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

    # def query(self, question, top_k=1, filter_criteria=None):
    #     return self.vector_store.similarity_search(
    #         query=question,
    #         k=top_k,
    #         filter=filter_criteria  # Filters by metadata
    #     )

    def query_with_sources(self, question, filter_criteria=None, top_k=5):
        """
        Query documents and return results with source attribution.
        Returns documents with page numbers, sections, and text snippets.
        """
        import time
        start_time = time.time()

        # Handle filter criteria properly - ChromaDB doesn't accept empty dicts
        filter_dict = None
        if filter_criteria and isinstance(filter_criteria, dict) and filter_criteria:
            filter_dict = filter_criteria

        results = self.vector_store.similarity_search(
            query=question,
            k=top_k,
            filter=filter_dict  # Pass None if no valid filter
        )

        # Format results with source information
        formatted_results = []
        for doc in results:
            formatted_result = {
                "text": doc.page_content,
                "filename": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "Unknown"),
                "section_heading": doc.metadata.get("section", "Unknown"),
                "doc_id": doc.metadata.get("doc_id", "Unknown"),
                "chunk_id": doc.metadata.get("chunk", "Unknown")
            }
            formatted_results.append(formatted_result)

        # Return in the format expected by /ask endpoint
        return {
            "sources": formatted_results,
            "query_time": time.time() - start_time
        }

    def save_summary(self, doc_id: str, summary: str) -> None:
        """Updates document summary in ChromaDB collection and re-indexes it."""
        try:
            # 1. Retrieve existing documents with the given doc_id
            results = self.vector_store.get(
                where={"doc_id": doc_id},
                include=["metadatas", "documents"]
            )

            if not results["ids"]:
                raise RuntimeError(f"No document found with doc_id {doc_id}")

            # 2. Prepare updated metadata for existing chunks
            updated_metadatas = [
                {**meta, "summary": summary, "last_updated": datetime.utcnow().isoformat()}
                for meta in results["metadatas"]
            ]

            # 3. Delete existing documents
            self.vector_store.delete(ids=results["ids"])

            # 4. Re-index existing chunks
            self.vector_store.add_texts(
                texts=results["documents"],
                metadatas=updated_metadatas,
                ids=results["ids"]
            )

            # 5. Split the updated summary into chunks
            summary_chunks = self.split_text_into_chunks(summary)

            # 6. Prepare metadata for summary chunks
            summary_metadatas = [
                {
                    "doc_id": doc_id,
                    "source": "Editable Summary",
                    "chunk": i,
                    "upload_time": datetime.utcnow().isoformat()
                }
                for i in range(len(summary_chunks))
            ]
            summary_ids = [f"{doc_id}-summary-{i}" for i in range(len(summary_chunks))]

            # 7. Index the summary chunks
            self.vector_store.add_texts(
                texts=summary_chunks,
                metadatas=summary_metadatas,
                ids=summary_ids
            )

            logger.info(f"Summary for doc_id {doc_id} saved and re-indexed successfully")

        except Exception as e:
            logger.error(f"Error saving summary for doc_id {doc_id}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Summary update failed: {str(e)}") from e