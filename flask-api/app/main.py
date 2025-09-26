from datetime import datetime
import time
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
import uuid
import os
from queue import Queue
import json
from queue import Queue
import json
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

# Global variables for async processing
processing_status = {}  # Store processing status by doc_id
status_lock = threading.Lock()

def update_processing_status(doc_id, status, progress=0, message=""):
    """Thread-safe status update"""
    with status_lock:
        processing_status[doc_id] = {
            "status": status,  # "processing", "completed", "failed"
            "progress": progress,  # 0-100
            "message": message,
            "timestamp": time.time()
        }

def process_pdf_async(pdf_path, doc_id, filename):
    """Background PDF processing function"""
    try:
        update_processing_status(doc_id, "processing", 10, "Loading PDF...")
        
        # Load PDF
        loader = PyPDFLoader(pdf_path)
        docs = loader.load_and_split()
        
        update_processing_status(doc_id, "processing", 30, "Chunking document...")
        
        # Process in chunks with progress updates
        total_chunks = len(range(0, len(docs), CHUNK_SIZE))
        processed_chunks = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for chunk_idx, i in enumerate(range(0, len(docs), CHUNK_SIZE)):
                future = executor.submit(
                    process_chunk,
                    docs_chunk=docs[i:i + CHUNK_SIZE],
                    doc_id=doc_id,
                    filename=filename,
                    start_idx=i
                )
                futures.append(future)
            
            # Process results with progress updates
            for future in as_completed(futures):
                future.result()  # This will raise exception if processing failed
                processed_chunks += 1
                progress = 30 + int((processed_chunks / total_chunks) * 60)  # 30-90%
                update_processing_status(doc_id, "processing", progress, 
                                       f"Processing chunk {processed_chunks}/{total_chunks}...")
        
        update_processing_status(doc_id, "completed", 100, "Document ready!")
        logger.info(f"Successfully processed document {doc_id}")
        
    except Exception as e:
        update_processing_status(doc_id, "failed", 0, f"Processing failed: {str(e)}")
        logger.error(f"Failed to process document {doc_id}: {str(e)}", exc_info=True)
    finally:
        # Clean up temp file
        if os.path.exists(pdf_path):
            os.remove(pdf_path) 

@app.route('/summary', methods=['POST'])
def generate_summary():
    doc_id = request.json.get("doc_id")
    
    if not doc_id:
        return jsonify({"error": "Document ID is required"}), 400

    try:
        # Use the summarize_pdf function
        summary_result = summarize_pdf(doc_id)
        
        if not summary_result:
            return jsonify({"error": "No content found for this document"}), 404
        
        return jsonify({
            "answer": summary_result.get('summary', 'No summary available')
        })

    except Exception as e:
        logger.error(f"Error in generate_summary: {str(e)}", exc_info=True)
        return jsonify({"error": f"Summarization failed: {str(e)}"}), 500
    
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
    """Upload file and start background processing"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    pdf_file = request.files['file']
    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400

    try:
        # Generate doc_id immediately
        doc_id = str(uuid.uuid4())
        
        # Save file to temp directory
        temp_path = os.path.join(TEMP_DIR, f"{doc_id}.pdf")
        pdf_file.save(temp_path)
        
        # Initialize processing status
        update_processing_status(doc_id, "processing", 5, "File uploaded, starting processing...")
        
        # Start background processing
        processing_thread = threading.Thread(
            target=process_pdf_async,
            args=(temp_path, doc_id, pdf_file.filename)
        )
        processing_thread.daemon = True
        processing_thread.start()
        
        # Return immediately with doc_id
        return jsonify({
            "status": "accepted",
            "doc_id": doc_id,
            "message": "File uploaded successfully. Processing started in background."
        }), 202  # HTTP 202: Accepted (processing started)
        
    except Exception as e:
        logger.exception("Upload failed")
        return jsonify({"error": "Upload failed"}), 500


@app.route('/status/<doc_id>', methods=['GET'])
def get_status(doc_id):
    """Get processing status for specific document"""
    with status_lock:
        if doc_id not in processing_status:
            return jsonify({"error": "Document not found"}), 404
        
        status_data = processing_status[doc_id].copy()
    
    return jsonify(status_data)


@app.route('/status', methods=['GET'])
def get_all_statuses():
    """Get status of all processing documents"""
    with status_lock:
        all_statuses = processing_status.copy()
    
    return jsonify(all_statuses)

@app.route('/')
def app_status():
    """Check the status of the application"""
    response = {
        "connectionStatus": "Connected",
        "status": "healthy"
    }
    return jsonify(response)

@app.route('/health')
def health_check():
    """Health check endpoint for React frontend"""
    try:
        # You could add more health checks here (database, etc.)
        return jsonify({
            "status": "healthy",
            "message": "Backend is running properly"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "error": str(e)
        }), 500

@app.route('/question', methods=['POST'])
def ask_question_endpoint():
    question = request.json.get("question")
    doc_id = request.json.get("doc_id")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    if not doc_id:
        return jsonify({"error": "Document ID is required"}), 400

    try:
        # Create filter criteria for doc_id
        filter_criteria = {"doc_id": doc_id}
        
        # Use the enhanced query method for source attribution
        query_result = retriever.query_with_sources(question, filter_criteria=filter_criteria, top_k=5)

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
            "sources": sources_for_response,
            "metadata": {
                "total_sources": len(query_result['sources']),
                "query_time": query_result.get('query_time', 0)
            }
        })

    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}", exc_info=True)
        return jsonify({"error": f"Question processing failed: {str(e)}"}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    # Keep the original /ask endpoint for backward compatibility
    return ask_question_endpoint()

@app.route('/analyze-paper/<doc_id>', methods=['POST'])
def analyze_paper(doc_id):
    """Academic paper structure analysis"""
    try:
        # Get all document chunks for analysis
        filter_criteria = {"doc_id": doc_id}
        all_chunks = retriever.query_with_sources("", filter_criteria=filter_criteria, top_k=50)
        
        if not all_chunks['sources']:
            return jsonify({"error": "Document not found or not processed"}), 404
        
        # Combine all text for analysis
        full_text = " ".join([chunk['text'] for chunk in all_chunks['sources'][:10]])  # First 10 chunks
        
        # AI analysis for paper structure
        analysis_prompt = f"""Analyze this academic paper and provide:
        1. Research Focus (one sentence)
        2. Paper Type (Empirical Study, Literature Review, Case Study, etc.)
        3. Main Research Question
        4. Key Findings (3-4 bullet points)
        5. Methodology Used
        6. Main Contributions to the field
        
        Text: {full_text[:3000]}
        
        Format as JSON with keys: research_focus, paper_type, research_question, key_findings, methodology, contributions"""
        
        analysis = ChatOpenAI(model="gpt-3.5-turbo").invoke(analysis_prompt).content
        
        # Try to parse as JSON, fallback to text
        try:
            import json
            analysis_data = json.loads(analysis)
        except:
            analysis_data = {"raw_analysis": analysis}
        
        # Add section information
        sections = {}
        for chunk in all_chunks['sources']:
            section = chunk.get('section_heading', 'Content')
            page = chunk.get('page', 'Unknown')
            if section not in sections:
                sections[section] = []
            if page not in sections[section]:
                sections[section].append(page)
        
        analysis_data['document_structure'] = {
            "sections": sections,
            "total_pages": len(set([c.get('page', 0) for c in all_chunks['sources']])),
            "total_chunks": len(all_chunks['sources'])
        }
        
        return jsonify(analysis_data)
        
    except Exception as e:
        logger.error(f"Paper analysis failed: {str(e)}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route('/research-questions/<doc_id>', methods=['POST'])
def generate_research_questions(doc_id):
    """Generate academic research questions"""
    try:
        # Get document overview
        filter_criteria = {"doc_id": doc_id}
        overview = retriever.query_with_sources("abstract introduction conclusion", filter_criteria=filter_criteria, top_k=5)
        
        if not overview['sources']:
            return jsonify({"error": "Document not found"}), 404
        
        context = " ".join([source['text'] for source in overview['sources']])
        
        questions_prompt = f"""Based on this academic paper, generate 8 research questions that would help a student/researcher understand:

        1. The main argument and thesis
        2. The methodology and approach  
        3. The key findings and results
        4. The implications and significance
        5. The limitations and criticisms
        6. The relationship to existing literature
        7. Future research directions
        8. Practical applications

        Context: {context[:2000]}

        Format as a numbered list with brief explanations of why each question is important."""
        
        questions = ChatOpenAI(model="gpt-3.5-turbo").invoke(questions_prompt).content
        
        return jsonify({
            "questions": questions,
            "doc_id": doc_id,
            "generated_at": int(time.time())
        })
        
    except Exception as e:
        return jsonify({"error": f"Question generation failed: {str(e)}"}), 500

@app.route('/explain-concept', methods=['POST'])
def explain_concept():
    """Explain academic concepts in context of the document"""
    try:
        data = request.json
        concept = data.get('concept')
        doc_id = data.get('doc_id')
        
        if not concept or not doc_id:
            return jsonify({"error": "Both concept and doc_id are required"}), 400
        
        # Search for concept in document
        filter_criteria = {"doc_id": doc_id}
        concept_results = retriever.query_with_sources(
            f"What is {concept}? How is {concept} defined? {concept} meaning explanation",
            filter_criteria=filter_criteria,
            top_k=3
        )
        
        if not concept_results['sources']:
            return jsonify({"error": f"Concept '{concept}' not found in document"}), 404
        
        context = "\n".join([source['text'] for source in concept_results['sources']])
        
        explanation_prompt = f"""Explain the concept "{concept}" based on how it's used in this academic paper.

        Context from paper: {context}

        Provide:
        1. Clear definition of {concept}
        2. How {concept} is used in this specific research
        3. Why {concept} is important to this study
        4. Any related concepts mentioned

        Make it accessible but academically rigorous."""
        
        explanation = ChatOpenAI(model="gpt-3.5-turbo").invoke(explanation_prompt).content
        
        return jsonify({
            "concept": concept,
            "explanation": explanation,
            "sources": [{
                "page": source.get('page'),
                "section": source.get('section_heading'),
                "snippet": source['text'][:200] + "..."
            } for source in concept_results['sources']]
        })
        
    except Exception as e:
        return jsonify({"error": f"Concept explanation failed: {str(e)}"}), 500

@app.route('/section-summary/<doc_id>', methods=['POST'])
def get_section_summary(doc_id):
    """Get summary of specific document sections"""
    try:
        data = request.json
        section_name = data.get('section', 'introduction')  # Default to introduction
        
        filter_criteria = {"doc_id": doc_id}
        
        # Search for specific section content
        section_query = f"{section_name} section content methodology results findings"
        section_results = retriever.query_with_sources(
            section_query,
            filter_criteria=filter_criteria,
            top_k=5
        )
        
        if not section_results['sources']:
            return jsonify({"error": f"Section '{section_name}' not found"}), 404
        
        # Filter results that actually match the section
        relevant_sources = []
        for source in section_results['sources']:
            section_heading = source.get('section_heading', '').lower()
            if section_name.lower() in section_heading or section_heading in section_name.lower():
                relevant_sources.append(source)
        
        if not relevant_sources:
            relevant_sources = section_results['sources'][:3]  # Fallback to top results
        
        context = "\n".join([source['text'] for source in relevant_sources])
        
        summary_prompt = f"""Summarize the {section_name} section of this academic paper.

        Content: {context}

        Provide:
        1. Main points covered in this section
        2. Key arguments or findings
        3. Important details or data
        4. How this section relates to the overall paper

        Keep it concise but comprehensive."""
        
        summary = ChatOpenAI(model="gpt-3.5-turbo").invoke(summary_prompt).content
        
        return jsonify({
            "section": section_name,
            "summary": summary,
            "sources": [{
                "page": source.get('page'),
                "section": source.get('section_heading'),
                "snippet": source['text'][:150] + "..."
            } for source in relevant_sources]
        })
        
    except Exception as e:
        return jsonify({"error": f"Section summary failed: {str(e)}"}), 500

@app.route('/academic-question', methods=['POST'])
def ask_academic_question():
    """Enhanced Q&A with academic context and deeper analysis"""
    try:
        data = request.json
        question = data.get("question")
        doc_id = data.get("doc_id")
        question_type = data.get("type", "general")  # general, methodology, findings, implications
        
        if not question or not doc_id:
            return jsonify({"error": "Question and document ID are required"}), 400
        
        filter_criteria = {"doc_id": doc_id}
        
        # Adjust search strategy based on question type
        if question_type == "methodology":
            enhanced_question = f"methodology method approach {question}"
            top_k = 3
        elif question_type == "findings":
            enhanced_question = f"results findings conclusions {question}"
            top_k = 4
        elif question_type == "implications":
            enhanced_question = f"implications significance impact applications {question}"
            top_k = 3
        else:
            enhanced_question = question
            top_k = 5
        
        query_result = retriever.query_with_sources(enhanced_question, filter_criteria=filter_criteria, top_k=top_k)
        
        if not query_result['sources']:
            return jsonify({"error": "No matching content found for this question"}), 404
        
        # Build enhanced context
        context_parts = []
        sources_for_response = []
        
        for i, source in enumerate(query_result['sources'], 1):
            source_info = f"[Source {i}] {source['filename']}"
            
            if source.get('page') and source['page'] != "Unknown":
                source_info += f" (Page {source['page']})"
            
            if source.get('section_heading') and source['section_heading'] not in ["Unknown", None]:
                source_info += f" - Section: {source['section_heading']}"
            
            context_parts.append(f"{source_info}\nContent: {source['text']}")
            
            sources_for_response.append({
                "source_id": i,
                "filename": source['filename'],
                "page": source['page'] if source['page'] != "Unknown" else None,
                "section_heading": source['section_heading'] if source['section_heading'] != "Unknown" else None,
                "snippet": source['text'][:250] + "...",
                "doc_id": source['doc_id'],
                "relevance_score": 0.8 + (0.1 * (5-i))  # Mock relevance scoring
            })
        
        context = "\n\n".join(context_parts)
        
        # Academic-focused prompt
        academic_prompt = f"""You are an academic research assistant. Answer this question about the research paper using ONLY the provided context.

        Context from academic paper:
        {context}

        Question: {question}
        Question Type: {question_type}

        Please provide:
        1. A comprehensive answer referencing specific sources
        2. Key evidence or data points that support the answer
        3. Any limitations or caveats mentioned in the source material
        4. How this relates to the broader research context

        Format your response with clear source citations (e.g., "According to Source 1...").
        If the answer cannot be found in the context, clearly state this."""
        
        answer = ChatOpenAI(model="gpt-3.5-turbo").invoke(academic_prompt).content
        
        return jsonify({
            "answer": answer,
            "sources": sources_for_response,
            "question_type": question_type,
            "confidence": "high" if len(query_result['sources']) >= 3 else "medium",
            "metadata": {
                "total_sources": len(query_result['sources']),
                "query_time": query_result.get('query_time', 0),
                "enhanced_query": enhanced_question
            }
        })
        
    except Exception as e:
        logger.error(f"Academic question failed: {str(e)}")
        return jsonify({"error": f"Question processing failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)