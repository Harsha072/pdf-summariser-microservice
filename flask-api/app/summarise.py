from langchain_community.document_loaders import PyPDFLoader
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import OpenAI
from dotenv import load_dotenv
from retriever import DocumentRetriever
import os

load_dotenv()

retriever = DocumentRetriever()

def summarize_pdf(doc_id=None, custom_prompt=""):
    """
    Generate a summary of a document using its doc_id from ChromaDB.
    Args:
        doc_id (str): The document ID to summarize
        custom_prompt (str): Optional custom prompt for summarization
    """
    try:
        # Initialize LLM
        llm = OpenAI(
            model_name="gpt-3.5-turbo-instruct",
            temperature=0.3,
            max_tokens=1000,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # Get document chunks from ChromaDB using doc_id
        filter_criteria = {"doc_id": doc_id} if doc_id else None
        relevant_docs = retriever.query(
            question="Summarize this document in detail",
            filter_criteria=filter_criteria,
            top_k=5
        )

        if not relevant_docs:
            raise ValueError("No document found with the provided ID")

        # Generate summary using map_reduce chain
        chain = load_summarize_chain(llm, chain_type="map_reduce")
        summary = chain.run(relevant_docs)

        # Get metadata from first chunk for additional context
        metadata = relevant_docs[0].metadata
        
        return {
            "summary": summary,
            "source": metadata.get("source", "Unknown"),
            "page_count": len(set(doc.metadata.get("page") for doc in relevant_docs)),
            "upload_time": metadata.get("upload_time")
        }

    except Exception as e:
        raise Exception(f"Summarization failed: {str(e)}")