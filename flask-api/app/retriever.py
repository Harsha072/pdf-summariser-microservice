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