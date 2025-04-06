from langchain_community.document_loaders import PyPDFLoader
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

def summarize_pdf(pdf_file_path, custom_prompt=""):
    """
    Summarize a PDF file using LangChain with OpenAI API.
    
    Args:
        pdf_file_path (str): Path to the PDF file
        custom_prompt (str, optional): Custom prompt for summarization. Defaults to "".
    
    Returns:
        str: Generated summary
    """
    # Load OpenAI LLM with API key from environment
    llm = OpenAI(
        model_name="gpt-3.5-turbo-instruct",  # Replacement for text-davinci-003
        temperature=0.3,  # Slightly higher for better results
        max_tokens=1000,  # Increase if you need longer summaries
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Load and split the PDF
    loader = PyPDFLoader(pdf_file_path)
    docs = loader.load_and_split()
    
    # Load summarization chain
    chain = load_summarize_chain(
        llm,
        chain_type="map_reduce",
        verbose=True  # For debugging
    )
    
    # Run the chain and return the summary
    summary = chain.run(docs)
    
    return summary