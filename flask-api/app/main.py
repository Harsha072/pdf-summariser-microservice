from datetime import  time
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from flask_cors import CORS
from summarise import summarize_pdf
from werkzeug.utils import secure_filename
from retriever import DocumentRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from logger_config import setup_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from langchain_community.document_loaders import PyPDFLoader
import threading
import tempfile
import os
import time

import uuid
# from tasks import process_pdf
from celery.result import AsyncResult

# Load environment variables
load_dotenv()
logger = setup_logger(__name__)
logger.info("Starting PDF Summarizer microservice")
app = Flask(__name__)

# Enable CORS for all routes
CORS(app, origins="*", methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Content-Type'])

api = Api(app)
retriever = DocumentRetriever()

# Create custom temp directory
TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

CHUNK_SIZE = 10  # Optimal for CPU-bound tasks
MAX_WORKERS = min(32, os.cpu_count() + 4)  # Dynamic worker count
chroma_lock = threading.Lock() 

@app.route('/summarize', methods=['POST'])
def summarize():
    
    doc_id = request.json.get("doc_id")  # Optional: Filter by specific upload
    print(doc_id)
    if not doc_id:
        return jsonify({"error": "Question is required"}), 400

    try:
        # Filter by doc_id if provided, else search all documents
        filter_criteria = doc_id if doc_id else None
        
        # Get top 3 most relevant chunks (filtered if doc_id exists)
        docs = summarize_pdf(doc_id)
        
        if not docs:
            return jsonify({"error": "No matching content found"}), 404
        
        print(docs['summary'])

        

        return jsonify({
            "answer": docs['summary']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# @app.route('/save', methods=['POST'])
# def save_summary():
#     doc_id = request.json.get("doc_id")
#     summary = request.json.get("summary")  # Expect a single summary string
#     if not doc_id or not summary:
#         return jsonify({"error": "Document ID and summary are required"}), 400

#     try:
#         # Save the edited summary back to the database or storage
#         retriever.save_summary(doc_id, summary)
#         return jsonify({"status": "success", "message": "Summary saved successfully"})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

def extract_section_heading(text):
    """Extract potential section heading from text"""
    lines = text.strip().split('\n')
    for line in lines[:3]:  # Check first 3 lines
        line = line.strip()
        # Look for common section patterns
        if (len(line) < 100 and 
            (line.isupper() or 
             any(keyword in line.lower() for keyword in [
                 'introduction', 'method', 'result', 'conclusion', 'discussion',
                 'abstract', 'summary', 'background', 'literature', 'analysis',
                 'findings', 'recommendation', 'overview', 'chapter', 'section'
             ]) or
             (len(line.split()) <= 5 and line.endswith('.') == False))):
            return line
    return None

def process_chunk(docs_chunk, doc_id, filename, start_idx):
    """Enhanced chunk processor with section heading extraction"""
    texts = []
    metadatas = []
    ids = []
    
    for i, doc in enumerate(docs_chunk, start=start_idx):
        # Extract section heading from content
        section_heading = extract_section_heading(doc.page_content)
        
        texts.append(doc.page_content)
        metadatas.append({
            "doc_id": doc_id,
            "source": secure_filename(filename),
            "page": doc.metadata.get("page", i+1),  # Use actual page from PDF
            "section": section_heading or "Content",  # Add section heading
            "chunk": i,
            "upload_time": time.time(),
            "text_length": len(doc.page_content)  # Track chunk size
        })
        ids.append(f"{doc_id}-{i}")
    
    # Thread-safe batch insert
    with chroma_lock:
        retriever.index_document(
            texts=texts,
            metadatas=metadatas,
            ids=ids
        )
    
    return len(texts)

@app.route('/upload', methods=['POST'])
def upload_file():
    start_time = time.time()
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    pdf_file = request.files['file']
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400

    try:
        # Use custom temp directory
        temp_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.pdf")
        pdf_file.save(temp_path)
        
        try:
            # Load PDF with optimized settings
            loader = PyPDFLoader(temp_path)
            docs = loader.load_and_split()
            
            # 2. Parallel processing with progress tracking
            total_pages = 0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                doc_id = str(uuid.uuid4())
                
                for chunk_idx, i in enumerate(range(0, len(docs), CHUNK_SIZE)):
                    future = executor.submit(
                        process_chunk,
                        docs_chunk=docs[i:i + CHUNK_SIZE],
                        doc_id=doc_id,
                        filename=pdf_file.filename,
                        start_idx=i
                    )
                    futures.append(future)
                
                # Get results as they complete
                for future in as_completed(futures):
                    total_pages += future.result()
            
            return jsonify({
                "status": "success",
                "doc_id": doc_id,
                "pages_processed": total_pages,
                "processing_time": f"{time.time() - start_time:.2f}s"
            })
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
    except Exception as e:
        logger.exception("Upload failed")  # Auto logs stack trace
        return jsonify({"error": "Processing failed"}), 500

@app.route('/')
def get_status():
    """Check the status of a PDF processing task"""
    response = {
        "connectionStatus": "'Connected'"
    }
    
    return jsonify(response)

@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.json.get("question")
    doc_id = request.json.get("doc_id")  # Optional: Filter by specific upload

    if not question:
        return jsonify({"error": "Question is required"}), 400

    try:
        # Create filter criteria for doc_id if provided
        filter_criteria = None
        if doc_id:
            filter_criteria = {"doc_id": doc_id}
        
        # Use the enhanced query method for source attribution
        query_result = retriever.query_with_sources(question, filter_criteria=filter_criteria, top_k=5)
        print("********** ", query_result)

        if not query_result['sources']:
            return jsonify({"error": "No matching content found"}), 404

        # Format context for AI prompt with enhanced source details
        context_parts = []
        sources_for_response = []

        for i, source in enumerate(query_result['sources'], 1):
            # Build source information string
            source_info = f"[Source {i}] {source['filename']}"
            
            # Add page information if available
            if source.get('page') and source['page'] != "Unknown":
                source_info += f" (Page {source['page']})"
            
            # Add section heading if available and not "Unknown"
            if source.get('section_heading') and source['section_heading'] not in ["Unknown", None]:
                source_info += f" - Section: {source['section_heading']}"
            
            # Create formatted context entry
            context_entry = f"{source_info}\nContent: {source['text']}"
            context_parts.append(context_entry)
            
            # Prepare source for response (with snippet for display)
            source_snippet = source['text'][:200] + "..." if len(source['text']) > 200 else source['text']
            
            sources_for_response.append({
                "source_id": i,
                "filename": source['filename'],
                "page": source['page'] if source['page'] != "Unknown" else None,
                "section_heading": source['section_heading'] if source['section_heading'] != "Unknown" else None,
                "snippet": source_snippet,
                "doc_id": source['doc_id'],
                "chunk_id": source.get('chunk_id', 'Unknown')
            })

        context = "\n\n".join(context_parts)

        # Enhanced AI prompt that encourages source referencing
        prompt = f"""Answer the question using ONLY the following context from the uploaded documents.
        If the answer cannot be found in the context, please say so.
        When providing your answer, reference the specific sources (e.g., "According to Source 1..." or "As shown in Source 2...").

        Context:
        {context}

        Question: {question}

        Please provide a comprehensive answer and clearly indicate which sources support your statements."""

        # Generate answer with enhanced context
        answer = ChatOpenAI(model="gpt-3.5-turbo").invoke(prompt).content

        logger.info(f"Generated answer with {len(query_result['sources'])} sources")

        return jsonify({
            "answer": answer,
            "sources": sources_for_response,  # Use cleaned up sources
            "metadata": {
                "total_sources": len(query_result['sources']),
                "query_time": query_result.get('query_time', 0)
            }
        })

    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)