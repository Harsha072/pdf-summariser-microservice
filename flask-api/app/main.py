

import os
import re
import json
import uuid
import time
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Flask and web framework imports
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# AI and OpenAI imports
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Web scraping imports
import requests
from bs4 import BeautifulSoup
import urllib.parse

# PDF processing imports
import fitz  # PyMuPDF

# Text similarity and processing
from fuzzywuzzy import fuzz

# ArXiv API import
try:
    import arxiv
except ImportError:
    print("Warning: arxiv library not installed. Install with: pip install arxiv")
    arxiv = None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*", methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Content-Type'])

# Configuration
class Config:
    TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
    MAX_WORKERS = 4
    DEFAULT_MAX_RESULTS = 10
    MAX_ALLOWED_RESULTS = 20
    DUPLICATE_THRESHOLD = 0.85
    REQUEST_TIMEOUT = 30
    
    # Create temp directory
    os.makedirs(TEMP_DIR, exist_ok=True)

config = Config()

# Initialize OpenAI client
openai_client = None
try:
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key and api_key.strip():
        openai_client = ChatOpenAI(
            api_key=api_key,
            model_name="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=1000
        )
        logger.info("OpenAI client initialized successfully")
    else:
        logger.warning("OpenAI API key not found. AI features will use fallback methods.")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    openai_client = None

# Global processing status tracking
processing_status = {}
status_lock = threading.Lock()


class ResearchFocusExtractor:
    """Extract research focus and keywords from text using AI analysis"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.logger = logger
    
    def extract_research_focus(self, text: str) -> Dict[str, Any]:
        """Extract key research topics and keywords using AI"""
        try:
            # Validate input
            if not text or not isinstance(text, str):
                text = "research analysis"
            
            if not self.openai_client:
                return self._fallback_extraction(text)
            
            # Truncate text to avoid token limits
            text_sample = text[:2000] if len(text) > 2000 else text
            
            prompt = f"""
            Analyze this research text and extract key information for finding relevant academic papers.
            
            Text: {text_sample}
            
            Please provide a JSON response with exactly these keys:
            {{
                "topic": "Main research topic (one sentence)",
                "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
                "domain": "Research field/domain",
                "methodologies": ["method1", "method2"],
                "audience": "graduate"
            }}
            
            Respond only with valid JSON, no additional text.
            """
            
            response = self.openai_client.invoke(prompt)
            
            # Parse JSON response with better error handling
            try:
                if hasattr(response, 'content'):
                    content = str(response.content).strip()
                else:
                    content = str(response).strip()
                    
                result = json.loads(content)
                return self._validate_extraction_result(result)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse OpenAI JSON response: {e}, using fallback")
                return self._fallback_extraction(text)
                
        except Exception as e:
            self.logger.error(f"Research focus extraction failed: {e}")
            return self._fallback_extraction(text)
    
    def _validate_extraction_result(self, result: Dict) -> Dict[str, Any]:
        """Validate and clean extraction result"""
        return {
            "topic": str(result.get("topic", "Research Topic"))[:200],
            "keywords": [str(kw)[:50] for kw in result.get("keywords", [])[:10]],
            "domain": str(result.get("domain", "Computer Science"))[:100],
            "methodologies": [str(m)[:50] for m in result.get("methodologies", [])[:5]],
            "audience": str(result.get("audience", "graduate"))[:20]
        }
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback method when AI is not available"""
        # Extract potential keywords using simple heuristics
        keywords = self._extract_keywords_heuristic(text)
        topic = self._extract_topic_heuristic(text)
        
        return {
            "topic": topic,
            "keywords": keywords,
            "domain": "Computer Science",
            "methodologies": ["analysis", "research"],
            "audience": "graduate"
        }
    
    def _extract_keywords_heuristic(self, text: str) -> List[str]:
        """Extract keywords using simple heuristics"""
        common_academic_terms = [
            "machine learning", "artificial intelligence", "deep learning",
            "neural networks", "data analysis", "algorithm", "optimization",
            "classification", "regression", "clustering", "natural language processing",
            "computer vision", "statistics", "modeling", "prediction"
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for term in common_academic_terms:
            if term in text_lower:
                found_keywords.append(term)
        
        return found_keywords[:8] if found_keywords else ["artificial intelligence", "research"]
    
    def _extract_topic_heuristic(self, text: str) -> str:
        """Extract topic using simple patterns"""
        patterns = [
            r'research on (.+?)(?:\.|,|;|\n)',
            r'study of (.+?)(?:\.|,|;|\n)',
            r'analysis of (.+?)(?:\.|,|;|\n)',
            r'investigation into (.+?)(?:\.|,|;|\n)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:200]
        
        return "Academic Research Topic"


class ArxivSearcher:
    """Search arXiv for academic papers"""
    
    def __init__(self):
        self.logger = logger
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search arXiv for papers"""
        if not arxiv:
            self.logger.warning("arXiv library not available")
            return []
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            papers = []
            for result in search.results():
                paper = {
                    "id": result.entry_id.split('/')[-1],
                    "title": result.title,
                    "authors": [str(author) for author in result.authors],
                    "summary": result.summary,
                    "url": result.entry_id,
                    "pdf_url": result.pdf_url,
                    "published": result.published.strftime('%Y-%m-%d') if result.published else None,
                    "categories": result.categories,
                    "source": "arXiv"
                }
                papers.append(paper)
            
            self.logger.info(f"Found {len(papers)} papers from arXiv")
            return papers
            
        except Exception as e:
            self.logger.error(f"arXiv search failed: {e}")
            return []


class SemanticScholarSearcher:
    """Search Semantic Scholar for academic papers"""
    
    def __init__(self):
        self.logger = logger
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Semantic Scholar for papers"""
        try:
            params = {
                'query': query,
                'limit': min(max_results, 100),  # API limit
                'fields': 'title,authors,abstract,url,year,citationCount,publicationDate,journal'
            }
            
            response = requests.get(
                self.base_url, 
                params=params, 
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            papers = []
            
            for paper_data in data.get('data', []):
                paper = {
                    "id": paper_data.get('paperId', str(uuid.uuid4())),
                    "title": paper_data.get('title', 'Unknown Title'),
                    "authors": [author.get('name', 'Unknown') 
                              for author in paper_data.get('authors', [])],
                    "summary": paper_data.get('abstract', 'No abstract available'),
                    "url": paper_data.get('url', ''),
                    "pdf_url": paper_data.get('url', ''),
                    "published": paper_data.get('publicationDate', ''),
                    "citation_count": paper_data.get('citationCount', 0),
                    "journal": paper_data.get('journal', {}).get('name', 'Unknown Journal'),
                    "source": "Semantic Scholar"
                }
                papers.append(paper)
            
            self.logger.info(f"Found {len(papers)} papers from Semantic Scholar")
            return papers
            
        except Exception as e:
            self.logger.error(f"Semantic Scholar search failed: {e}")
            return []


class GoogleScholarSearcher:
    """Search Google Scholar using web scraping"""
    
    def __init__(self):
        self.logger = logger
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google Scholar with web scraping"""
        try:
            search_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(query)}&num={max_results}"
            
            response = requests.get(
                search_url, 
                headers=self.headers, 
                timeout=config.REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Google Scholar returned status {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            papers = []
            
            for result in soup.find_all('div', class_='gs_r gs_or gs_scl')[:max_results]:
                try:
                    paper = self._parse_scholar_result(result)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"Failed to parse Google Scholar result: {e}")
                    continue
            
            self.logger.info(f"Found {len(papers)} papers from Google Scholar")
            return papers
            
        except Exception as e:
            self.logger.error(f"Google Scholar search failed: {e}")
            return []
    
    def _parse_scholar_result(self, result) -> Optional[Dict[str, Any]]:
        """Parse individual Google Scholar search result"""
        title_elem = result.find('h3', class_='gs_rt')
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        
        # Extract authors and publication info
        authors_elem = result.find('div', class_='gs_a')
        authors_text = authors_elem.get_text() if authors_elem else ""
        authors = [author.strip() for author in authors_text.split('-')[0].split(',')[:5]]
        
        # Extract summary
        summary_elem = result.find('span', class_='gs_rs')
        summary = summary_elem.get_text(strip=True) if summary_elem else "No summary available"
        
        # Extract URL
        link_elem = title_elem.find('a')
        url = link_elem.get('href') if link_elem else ""
        
        return {
            "id": str(uuid.uuid4()),
            "title": title,
            "authors": [author for author in authors if author],
            "summary": summary,
            "url": url,
            "pdf_url": url,
            "published": "",
            "source": "Google Scholar"
        }


class RelevanceScorer:
    """Score paper relevance using AI analysis"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.logger = logger
    
    def calculate_relevance_score(self, paper: Dict[str, Any], research_focus: Dict[str, Any]) -> float:
        """Calculate relevance score using AI analysis"""
        try:
            # Validate inputs
            if not paper or not research_focus:
                return 25.0
            
            if not self.openai_client:
                return self._heuristic_scoring(paper, research_focus)
            
            # Safe string formatting with defaults
            topic = research_focus.get('topic', 'Unknown topic')
            keywords = research_focus.get('keywords', [])
            domain = research_focus.get('domain', 'Unknown domain')
            
            title = paper.get('title', 'Unknown title')
            summary = paper.get('summary', 'No summary available')
            authors = paper.get('authors', [])
            
            # Ensure all values are strings
            keywords_str = ', '.join([str(kw) for kw in keywords if kw])
            authors_str = ', '.join([str(auth) for auth in authors[:3] if auth])
            
            prompt = f"""
            Rate the relevance of this academic paper to the research focus on a scale of 0-100.
            
            Research Focus:
            - Topic: {topic}
            - Keywords: {keywords_str}
            - Domain: {domain}
            
            Paper:
            - Title: {title}
            - Summary: {str(summary)[:400]}
            - Authors: {authors_str}
            
            Consider:
            1. Topic alignment (40 points)
            2. Keyword matches (30 points)  
            3. Methodological relevance (20 points)
            4. Recency and impact (10 points)
            
            Respond with only a number between 0-100.
            """
            
            response = self.openai_client.invoke(prompt)
            
            # Extract score from response
            if hasattr(response, 'content'):
                score_text = str(response.content).strip()
            else:
                score_text = str(response).strip()
                
            try:
                score_match = re.search(r'\d+\.?\d*', score_text)
                if score_match:
                    score = float(score_match.group())
                    return min(100, max(0, score))
                else:
                    return self._heuristic_scoring(paper, research_focus)
            except:
                return self._heuristic_scoring(paper, research_focus)
                
        except Exception as e:
            self.logger.error(f"Relevance scoring failed: {e}")
            return self._heuristic_scoring(paper, research_focus)
    
    def _heuristic_scoring(self, paper: Dict[str, Any], research_focus: Dict[str, Any]) -> float:
        """Fallback heuristic scoring when AI is not available"""
        try:
            score = 50.0  # Base score
            
            # Safe string handling with None checks
            title = str(paper.get('title', '')).lower() if paper.get('title') else ''
            summary = str(paper.get('summary', '')).lower() if paper.get('summary') else ''
            
            # Safe keyword processing
            raw_keywords = research_focus.get('keywords', []) if research_focus else []
            keywords = [str(kw).lower() for kw in raw_keywords if kw is not None and str(kw).strip()]
            
            # Keyword matching in title (high weight)
            title_matches = sum(1 for kw in keywords if kw and kw in title)
            score += title_matches * 15
            
            # Keyword matching in summary (medium weight)
            summary_matches = sum(1 for kw in keywords if kw and kw in summary)
            score += summary_matches * 5
            
            # Citation count bonus (if available)
            try:
                citation_count = int(paper.get('citation_count', 0))
                if citation_count > 100:
                    score += 10
                elif citation_count > 50:
                    score += 5
            except (ValueError, TypeError):
                pass  # Ignore invalid citation counts
            
            return min(100, max(0, score))
            
        except Exception as e:
            self.logger.error(f"Heuristic scoring failed: {e}")
            return 50.0  # Safe fallback


class DuplicateRemover:
    """Remove duplicate papers based on title similarity"""
    
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.logger = logger
    
    def remove_duplicates(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate papers based on title similarity"""
        if not papers:
            return papers
        
        unique_papers = []
        seen_titles = []
        
        for paper in papers:
            if not paper or not isinstance(paper, dict):
                continue
                
            title = paper.get('title')
            if not title:
                continue
                
            title = str(title).lower().strip()
            if not title:
                continue
                
            is_duplicate = False
            
            for seen_title in seen_titles:
                try:
                    similarity = fuzz.ratio(title, seen_title) / 100.0
                    if similarity >= self.threshold:
                        is_duplicate = True
                        # Keep the one with higher citation count or more complete info
                        existing_index = seen_titles.index(seen_title)
                        if self._is_better_paper(paper, unique_papers[existing_index]):
                            unique_papers[existing_index] = paper
                        break
                except Exception as e:
                    self.logger.warning(f"Error comparing titles: {e}")
                    continue
            
            if not is_duplicate:
                unique_papers.append(paper)
                seen_titles.append(title)
        
        self.logger.info(f"Removed {len(papers) - len(unique_papers)} duplicate papers")
        return unique_papers
    
    def _is_better_paper(self, paper1: Dict, paper2: Dict) -> bool:
        """Determine which paper is better (more complete/authoritative)"""
        # Prefer papers with citation counts
        citations1 = paper1.get('citation_count', 0)
        citations2 = paper2.get('citation_count', 0)
        
        if citations1 != citations2:
            return citations1 > citations2
        
        # Prefer papers with more complete summaries
        summary1_len = len(paper1.get('summary', ''))
        summary2_len = len(paper2.get('summary', ''))
        
        return summary1_len > summary2_len


class PDFAnalyzer:
    """Analyze PDF files to extract research content"""
    
    def __init__(self, research_extractor: ResearchFocusExtractor):
        self.research_extractor = research_extractor
        self.logger = logger
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            # Extract text from all pages
            for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages
                page = doc.load_page(page_num)
                text += page.get_text()
            
            doc.close()
            return text
            
        except Exception as e:
            self.logger.error(f"PDF text extraction failed: {e}")
            return ""
    
    def analyze_research_paper(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze uploaded research paper"""
        try:
            text = self.extract_text_from_pdf(pdf_path)
            
            if not text or len(text) < 100:
                return {"success": False, "error": "Could not extract meaningful text from PDF"}
            
            # Extract research focus
            research_focus = self.research_extractor.extract_research_focus(text)
            
            return {
                "success": True,
                "research_focus": research_focus,
                "text_length": len(text),
                "extracted_sample": text[:500] + "..." if len(text) > 500 else text
            }
            
        except Exception as e:
            self.logger.error(f"PDF analysis failed: {e}")
            return {"success": False, "error": str(e)}


class AcademicPaperDiscoveryEngine:
    """Main engine for discovering academic papers"""
    
    def __init__(self):
        self.logger = logger
        
        # Initialize components
        self.research_extractor = ResearchFocusExtractor(openai_client)
        self.arxiv_searcher = ArxivSearcher()
        self.semantic_searcher = SemanticScholarSearcher()
        self.scholar_searcher = GoogleScholarSearcher()
        self.relevance_scorer = RelevanceScorer(openai_client)
        self.duplicate_remover = DuplicateRemover(config.DUPLICATE_THRESHOLD)
        self.pdf_analyzer = PDFAnalyzer(self.research_extractor)
        
        self.logger.info("Academic Paper Discovery Engine initialized")
    
    def discover_papers(self, research_input: str, sources: List[str] = None, 
                       max_results: int = 10) -> Dict[str, Any]:
        """Main method to discover relevant academic papers"""
        try:
            if sources is None:
                sources = ["arxiv", "semantic_scholar"]
            
            max_results = min(max_results, config.MAX_ALLOWED_RESULTS)
            
            self.logger.info(f"Starting paper discovery for query: {research_input[:100]}...")
            
            # Extract research focus
            research_focus = self.research_extractor.extract_research_focus(research_input)
            
            # Create search query
            query_parts = [research_focus['topic']]
            query_parts.extend(research_focus['keywords'][:5])
            search_query = ' '.join(query_parts)
            
            self.logger.info(f"Search query: {search_query}")
            
            # Search multiple sources concurrently
            all_papers = []
            with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
                futures = []
                
                if "arxiv" in sources:
                    futures.append(executor.submit(self.arxiv_searcher.search, search_query, max_results))
                
                if "semantic_scholar" in sources:
                    futures.append(executor.submit(self.semantic_searcher.search, search_query, max_results))
                
                if "google_scholar" in sources:
                    futures.append(executor.submit(self.scholar_searcher.search, search_query, max_results))
                
                # Collect results
                for future in as_completed(futures):
                    try:
                        papers = future.result()
                        all_papers.extend(papers)
                    except Exception as e:
                        self.logger.error(f"Search source failed: {e}")
            
            # Remove duplicates
            unique_papers = self.duplicate_remover.remove_duplicates(all_papers)
            
            # Calculate relevance scores with error handling
            for paper in unique_papers:
                try:
                    if paper and isinstance(paper, dict):
                        paper['relevance_score'] = self.relevance_scorer.calculate_relevance_score(
                            paper, research_focus
                        )
                    else:
                        paper['relevance_score'] = 25.0  # Default score
                except Exception as e:
                    self.logger.warning(f"Failed to score paper: {e}")
                    paper['relevance_score'] = 25.0  # Default score
            
            # Sort by relevance score safely
            try:
                unique_papers.sort(key=lambda x: float(x.get('relevance_score', 0)), reverse=True)
            except Exception as e:
                self.logger.warning(f"Failed to sort papers: {e}")
                # Keep original order if sorting fails
            
            # Limit final results
            final_papers = unique_papers[:max_results]
            
            result = {
                "success": True,
                "research_focus": research_focus,
                "papers": final_papers,
                "total_found": len(all_papers),
                "unique_papers": len(unique_papers),
                "final_count": len(final_papers),
                "sources_searched": sources,
                "search_query": search_query
            }
            
            self.logger.info(f"Discovery completed: {len(final_papers)} papers returned")
            return result
            
        except Exception as e:
            self.logger.error(f"Paper discovery failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "papers": []
            }
    
    def analyze_uploaded_paper(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze uploaded paper and find similar research"""
        return self.pdf_analyzer.analyze_research_paper(pdf_path)


# Initialize the discovery engine
discovery_engine = AcademicPaperDiscoveryEngine()


# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Academic Paper Discovery Engine",
        "timestamp": datetime.now().isoformat(),
        "openai_available": openai_client is not None,
        "arxiv_available": arxiv is not None
    })


@app.route('/api/discover-papers', methods=['POST'])
def discover_papers():
    """Discover relevant academic papers based on research query"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        research_query = data.get('query', '').strip()
        if not research_query:
            return jsonify({"success": False, "error": "Research query is required"}), 400
        
        sources = data.get('sources', ['arxiv', 'semantic_scholar'])
        max_results = min(data.get('max_results', config.DEFAULT_MAX_RESULTS), config.MAX_ALLOWED_RESULTS)
        
        # Validate sources
        valid_sources = ['arxiv', 'semantic_scholar', 'google_scholar']
        sources = [s for s in sources if s in valid_sources]
        
        if not sources:
            return jsonify({"success": False, "error": "No valid sources specified"}), 400
        
        # Discover papers
        result = discovery_engine.discover_papers(research_query, sources, max_results)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Paper discovery endpoint failed: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/api/upload-paper', methods=['POST'])
def upload_paper():
    """Upload and analyze a research paper to find similar papers"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"success": False, "error": "Only PDF files are supported"}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(config.TEMP_DIR, f"{uuid.uuid4()}_{filename}")
        file.save(filepath)
        
        try:
            # Analyze the uploaded paper
            analysis_result = discovery_engine.analyze_uploaded_paper(filepath)
            
            if not analysis_result.get('success'):
                return jsonify(analysis_result), 400
            
            # Create research query from analysis
            research_focus = analysis_result['research_focus']
            research_query = f"{research_focus['topic']} {' '.join(research_focus['keywords'][:5])}"
            
            # Get parameters from form data
            sources = request.form.get('sources', 'arxiv,semantic_scholar').split(',')
            max_results = min(int(request.form.get('max_results', config.DEFAULT_MAX_RESULTS)), 
                            config.MAX_ALLOWED_RESULTS)
            
            # Find similar papers
            discovery_result = discovery_engine.discover_papers(research_query, sources, max_results)
            
            # Combine results
            result = {
                "success": True,
                "uploaded_paper_analysis": analysis_result['research_focus'],
                "similar_papers": discovery_result
            }
            
            return jsonify(result)
            
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass  # Ignore cleanup errors
        
    except Exception as e:
        logger.error(f"Paper upload endpoint failed: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/api/download-paper', methods=['POST'])
def download_paper():
    """Download and analyze a paper from provided URL"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"success": False, "error": "Paper URL is required"}), 400
        
        paper_url = data['url']
        
        # Validate URL
        if not paper_url.startswith(('http://', 'https://')):
            return jsonify({"success": False, "error": "Invalid URL"}), 400
        
        # Download the paper
        response = requests.get(paper_url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Check if it's a PDF
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type and not paper_url.lower().endswith('.pdf'):
            return jsonify({"success": False, "error": "URL does not point to a PDF file"}), 400
        
        # Save to temp file
        temp_filename = f"{uuid.uuid4()}_downloaded_paper.pdf"
        temp_filepath = os.path.join(config.TEMP_DIR, temp_filename)
        
        with open(temp_filepath, 'wb') as f:
            f.write(response.content)
        
        try:
            # Analyze the downloaded paper
            analysis_result = discovery_engine.analyze_uploaded_paper(temp_filepath)
            
            return jsonify(analysis_result)
            
        finally:
            # Clean up downloaded file
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass  # Ignore cleanup errors
        
    except requests.RequestException as e:
        logger.error(f"Paper download failed: {e}")
        return jsonify({"success": False, "error": "Failed to download paper"}), 500
    except Exception as e:
        logger.error(f"Paper download endpoint failed: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/api/sources', methods=['GET'])
def get_available_sources():
    """Get list of available paper sources"""
    sources = [
        {
            "id": "arxiv", 
            "name": "arXiv", 
            "description": "Open access repository of scientific papers",
            "available": arxiv is not None
        },
        {
            "id": "semantic_scholar", 
            "name": "Semantic Scholar", 
            "description": "AI-powered research tool for academic papers",
            "available": True
        },
        {
            "id": "google_scholar", 
            "name": "Google Scholar", 
            "description": "Web search for scholarly literature",
            "available": True
        }
    ]
    
    return jsonify({"sources": sources})


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"success": False, "error": "Internal server error"}), 500


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"success": False, "error": "File too large"}), 413


if __name__ == '__main__':
    logger.info("🔬 Academic Paper Discovery Engine Starting...")
    logger.info("=" * 60)
    logger.info("Available endpoints:")
    logger.info("- POST /api/discover-papers - Discover papers by research query")
    logger.info("- POST /api/upload-paper - Upload paper to find similar research")
    logger.info("- POST /api/download-paper - Download and analyze paper from URL")
    logger.info("- GET /api/health - Health check")
    logger.info("- GET /api/sources - Available search sources")
    logger.info("=" * 60)
    logger.info("🚀 Starting Flask development server...")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
