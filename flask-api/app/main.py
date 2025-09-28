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
# Enhanced PDF processing imports
import pymupdf  # PyMuPDF for better structure extraction
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
# Remove PyPDFLoader, use PyMuPDF instead
import threading
import uuid
import os
from queue import Queue
import json
import tempfile
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

# Enhanced PDF Processor for structure-aware extraction
class StructureAwarePDFProcessor:
    def __init__(self):
        self.logger = logger
        
    def extract_structured_content(self, pdf_path):
        """Extract PDF content with structure preservation"""
        try:
            doc = pymupdf.open(pdf_path)
            structured_content = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_content = self.extract_page_structure(page, page_num + 1)
                structured_content.extend(page_content)
            
            doc.close()
            return structured_content
            
        except Exception as e:
            self.logger.error(f"PDF extraction failed: {str(e)}")
            return []
    
    def extract_page_structure(self, page, page_num):
        """Extract structured content from a single page"""
        page_content = []
        
        # Get text blocks with position information
        text_dict = page.get_text("dict")
        
        current_section = None
        paragraph_count = 0
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                # Process text blocks
                block_text = ""
                block_bbox = block["bbox"]
                
                for line in block["lines"]:
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    block_text += line_text + "\n"
                
                block_text = block_text.strip()
                if not block_text:
                    continue
                
                # Classify content type and extract structure
                content_info = self.classify_content(block_text, block_bbox)
                
                if content_info["type"] == "heading":
                    current_section = block_text
                elif content_info["type"] == "paragraph":
                    paragraph_count += 1
                    
                    # Create structured content entry
                    page_content.append({
                        "text": block_text,
                        "page": page_num,
                        "section": current_section or "Content",
                        "paragraph_id": paragraph_count,
                        "content_type": content_info["type"],
                        "bbox": list(block_bbox),  # [x0, y0, x1, y1]
                        "start_char": len("\n".join([c["text"] for c in page_content])),
                        "end_char": len("\n".join([c["text"] for c in page_content])) + len(block_text),
                        "font_size": content_info["font_size"],
                        "is_bold": content_info["is_bold"]
                    })
        
        return page_content
    
    def classify_content(self, text, bbox):
        """Classify content type based on text and formatting"""
        # Simple heuristics for content classification
        lines = text.split('\n')
        first_line = lines[0].strip() if lines else ""
        
        # Check for headings
        if (len(first_line) < 100 and 
            (first_line.isupper() or 
             any(keyword in first_line.lower() for keyword in [
                 'introduction', 'method', 'result', 'conclusion', 'discussion',
                 'abstract', 'summary', 'background', 'literature', 'analysis',
                 'findings', 'recommendation', 'overview', 'chapter', 'section'
             ]) or
             len(first_line.split()) <= 6)):
            return {
                "type": "heading",
                "font_size": 12,  # Default, could be extracted from spans
                "is_bold": True
            }
        
        return {
            "type": "paragraph",
            "font_size": 10,
            "is_bold": False
        }

# Initialize the PDF processor
pdf_processor = StructureAwarePDFProcessor()

def filter_metadata_for_chromadb(metadata):
    """Filter metadata to only include types ChromaDB accepts: str, int, float, bool"""
    filtered = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            filtered[key] = value
        elif isinstance(value, list):
            # Convert lists to strings for ChromaDB compatibility
            filtered[f"{key}_string"] = ",".join(map(str, value))
        else:
            # Convert other types to string
            filtered[key] = str(value)
    return filtered

def reconstruct_bbox_from_metadata(metadata):
    """Reconstruct bbox coordinates from ChromaDB metadata"""
    try:
        if "bbox_string" in metadata:
            coords = metadata["bbox_string"].split(",")
            return [float(coord) for coord in coords]
        elif all(key in metadata for key in ["bbox_x0", "bbox_y0", "bbox_x1", "bbox_y1"]):
            return [
                metadata["bbox_x0"],
                metadata["bbox_y0"], 
                metadata["bbox_x1"],
                metadata["bbox_y1"]
            ]
        else:
            return None
    except (ValueError, KeyError):
        return None

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
    """Background PDF processing function with structure preservation"""
    try:
        update_processing_status(doc_id, "processing", 10, "Loading PDF...")
        
        # Extract structured content using PyMuPDF
        structured_content = pdf_processor.extract_structured_content(pdf_path)
        
        if not structured_content:
            update_processing_status(doc_id, "failed", 0, "No content extracted from PDF")
            return
        
        update_processing_status(doc_id, "processing", 30, "Processing structured content...")
        
        # Process in chunks with progress updates
        total_chunks = len(range(0, len(structured_content), CHUNK_SIZE))
        processed_chunks = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for chunk_idx, i in enumerate(range(0, len(structured_content), CHUNK_SIZE)):
                future = executor.submit(
                    process_structured_chunk,
                    content_chunk=structured_content[i:i + CHUNK_SIZE],
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

# Remove unused extract_section_heading function - now handled by StructureAwarePDFProcessor

def process_structured_chunk(content_chunk, doc_id, filename, start_idx):
    """Enhanced chunk processor with structure preservation and ChromaDB compatibility"""
    texts = []
    metadatas = []
    ids = []
    
    for i, content_item in enumerate(content_chunk, start=start_idx):
        # Use the structured content directly
        text = content_item["text"]
        
        # Convert bbox list to string for ChromaDB compatibility
        bbox_coords = content_item["bbox"]
        bbox_string = f"{bbox_coords[0]},{bbox_coords[1]},{bbox_coords[2]},{bbox_coords[3]}"
        
        texts.append(text)
        
        # Create metadata with only primitive types
        raw_metadata = {
            "doc_id": doc_id,
            "source": secure_filename(filename),
            "page": content_item["page"],
            "section": content_item["section"],
            "section_heading": content_item["section"],  # For backward compatibility
            "paragraph_id": content_item["paragraph_id"],
            "content_type": content_item["content_type"],
            "bbox_string": bbox_string,  # Convert list to string
            "bbox_x0": float(bbox_coords[0]),  # Individual bbox coordinates
            "bbox_y0": float(bbox_coords[1]),
            "bbox_x1": float(bbox_coords[2]),
            "bbox_y1": float(bbox_coords[3]),
            "start_char": content_item["start_char"],
            "end_char": content_item["end_char"],
            "chunk": i,
            "upload_time": time.time(),
            "text_length": len(text),
            "font_size": float(content_item["font_size"]),
            "is_bold": bool(content_item["is_bold"])
        }
        
        # Filter out any complex metadata that ChromaDB can't handle
        filtered_metadata = filter_metadata_for_chromadb(raw_metadata)
        metadatas.append(filtered_metadata)
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

@app.route('/status/<doc_id>', methods=['GET'])
def get_processing_status(doc_id):
    """Get processing status for a document"""
    try:
        with status_lock:
            if doc_id in processing_status:
                return jsonify(processing_status[doc_id])
            else:
                return jsonify({
                    "status": "not_found",
                    "progress": 0,
                    "message": "Document not found or not being processed",
                    "timestamp": time.time()
                }), 404
    except Exception as e:
        logger.error(f"Status check failed for {doc_id}: {str(e)}")
        return jsonify({"error": f"Status check failed: {str(e)}"}), 500

@app.route('/ask-with-quotes', methods=['POST'])
def ask_with_supporting_quotes():
    """Ask a question and get answer with supporting quotes from the document"""
    try:
        data = request.json
        question = data.get('question', '')
        doc_id = data.get('doc_id')
        
        if not question or not doc_id:
            return jsonify({"error": "Question and document ID required"}), 400
        
        logger.info(f"Ask with quotes: '{question}' in doc {doc_id}")
        
        # Get AI answer first
        filter_criteria = {"doc_id": doc_id}
        query_result = retriever.query_with_sources(question, filter_criteria=filter_criteria, top_k=5)
        
        if not query_result['sources']:
            return jsonify({
                "answer": "I couldn't find information to answer this question in the document.",
                "supporting_quotes": [],
                "confidence": 0
            })
        
        # Build context for AI
        context_parts = []
        all_sources = []
        
        for i, source in enumerate(query_result['sources'], 1):
            context_parts.append(f"[Source {i}] {source['text']}")
            all_sources.append(source)
        
        context = "\n\n".join(context_parts)
        
        # Get AI answer
        prompt = f"""Answer the question using ONLY the following context from the document.
        Be specific and factual. If the answer cannot be found, say so.
        
        Context:
        {context}
        
        Question: {question}
        
        Answer:"""
        
        ai_response = ChatOpenAI(model="gpt-3.5-turbo", temperature=0).invoke(prompt).content
        
        # Find supporting quotes by extracting key phrases from AI answer
        supporting_quotes = find_supporting_quotes_for_answer(ai_response, all_sources)
        
        # Calculate confidence based on number of supporting quotes
        confidence = min(len(supporting_quotes) * 25, 100)  # 25% per quote, max 100%
        
        response_data = {
            "question": question,
            "answer": ai_response,
            "supporting_quotes": supporting_quotes,
            "confidence": confidence,
            "total_sources_used": len(all_sources)
        }
        
        logger.info(f"Ask with quotes completed: {len(supporting_quotes)} quotes found")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Ask with quotes failed: {str(e)}", exc_info=True)
        return jsonify({"error": f"Request failed: {str(e)}"}), 500


def find_supporting_quotes_for_answer(ai_answer, sources):
    """Find the most relevant quotes from sources that support the AI answer"""
    import re
    from difflib import SequenceMatcher
    
    # Extract key phrases from AI answer (sentences or important phrases)
    sentences = re.split(r'[.!?]+', ai_answer.strip())
    key_phrases = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 10:  # Skip very short sentences
            # Extract meaningful phrases (remove common words)
            words = sentence.lower().split()
            meaningful_words = [w for w in words if len(w) > 3 and w not in 
                              ['this', 'that', 'these', 'those', 'with', 'from', 'they', 'were', 'been', 'have']]
            if len(meaningful_words) >= 2:
                key_phrases.extend(meaningful_words[:3])  # Take first 3 meaningful words
    
    supporting_quotes = []
    used_sources = set()  # Avoid duplicate sources
    
    # Find quotes that contain similar concepts
    for i, source in enumerate(sources):
        if i in used_sources or len(supporting_quotes) >= 3:  # Max 3 quotes
            continue
            
        source_text = source['text'].lower()
        match_score = 0
        
        # Calculate similarity score
        for phrase in key_phrases:
            if phrase.lower() in source_text:
                match_score += 1
        
        # If we have a good match, include this as a supporting quote
        if match_score >= 2:  # At least 2 matching concepts
            # Find the most relevant sentence in the source
            source_sentences = re.split(r'[.!?]+', source['text'])
            best_sentence = ""
            best_score = 0
            
            for sent in source_sentences:
                sent = sent.strip()
                if len(sent) > 20:  # Skip very short sentences
                    sent_lower = sent.lower()
                    score = sum(1 for phrase in key_phrases if phrase in sent_lower)
                    if score > best_score:
                        best_score = score
                        best_sentence = sent
            
            if best_sentence:
                # Reconstruct bbox from metadata if available
                bbox = None
                if all(key in source for key in ['bbox_x0', 'bbox_y0', 'bbox_x1', 'bbox_y1']):
                    bbox = {
                        "x0": source['bbox_x0'],
                        "y0": source['bbox_y0'], 
                        "x1": source['bbox_x1'],
                        "y1": source['bbox_y1']
                    }
                
                quote = {
                    "text": best_sentence,
                    "page": source.get('page', 'Unknown'),
                    "section": source.get('section_heading', 'Content'),
                    "confidence": min(match_score * 25, 100),  # Convert to percentage
                    "bbox": bbox,
                    "source_id": i
                }
                
                supporting_quotes.append(quote)
                used_sources.add(i)
    
    # Sort by confidence score
    supporting_quotes.sort(key=lambda x: x['confidence'], reverse=True)
    
    return supporting_quotes


def extract_search_terms_from_query(question):
    """Extract meaningful search terms from natural language question"""
    # Remove common question words
    stop_words = {
        'where', 'what', 'how', 'when', 'why', 'which', 'who', 'does', 'do', 'is', 'are',
        'the', 'author', 'mention', 'discuss', 'talk', 'about', 'section', 'paragraph',
        'paper', 'document', 'find', 'locate', 'show', 'me', 'in', 'and', 'or', 'of', 'to'
    }
    
    # Extract quoted terms first
    quoted_terms = re.findall(r'"([^"]*)"', question)
    
    # Extract remaining words
    words = re.findall(r'\b\w+\b', question.lower())
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Combine quoted terms and filtered words
    all_terms = quoted_terms + filtered_words
    
    # Remove duplicates while preserving order
    unique_terms = []
    seen = set()
    for term in all_terms:
        if term not in seen:
            unique_terms.append(term)
            seen.add(term)
    
    return unique_terms[:5]  # Limit to top 5 terms

def find_term_occurrences_in_text(text, search_terms):
    """Find occurrences of search terms in text with context"""
    occurrences = []
    text_lower = text.lower()
    
    for term in search_terms:
        term_lower = term.lower()
        start_pos = 0
        
        while True:
            pos = text_lower.find(term_lower, start_pos)
            if pos == -1:
                break
            
            # Get context around the found term
            context_start = max(0, pos - 50)
            context_end = min(len(text), pos + len(term) + 50)
            context = text[context_start:context_end]
            
            # Add ellipsis if context is truncated
            if context_start > 0:
                context = "..." + context
            if context_end < len(text):
                context = context + "..."
            
            # Highlight the found term in context
            highlighted_context = re.sub(
                f'({re.escape(term)})', 
                r'**\1**', 
                context, 
                flags=re.IGNORECASE
            )
            
            occurrences.append({
                "found_term": text[pos:pos + len(term)],  # Preserve original case
                "position": pos,
                "context": highlighted_context,
                "exact_match": True
            })
            
            start_pos = pos + 1
    
    return occurrences

# Clean endpoint - only essential APIs for structure-aware PDF processing remain

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)