"""
Citation Network Analyzer Module
Handles building and analyzing citation networks for academic papers
"""

import logging
import requests
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict, Counter
import json
import pickle
import os

logger = logging.getLogger(__name__)


class CitationDataExtractor:
    """Extracts citation data from various academic APIs"""
    
    def __init__(self, rate_limit_delay: float = 0.1):
        self.rate_limit_delay = rate_limit_delay
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Academic-Paper-Discovery-Engine/1.0 (mailto:research@example.com)'
        })
    
    def _format_openalex_id(self, paper_id: str) -> str:
        """Format paper ID for OpenAlex API requests - creates OpenAlex work ID from digit ID"""
        if not paper_id:
            return ""
        
        self.logger.info(f"Formatting OpenAlex ID for: {paper_id}")
        # Remove whitespace
        clean_id = paper_id.strip()
        
        # If already a full OpenAlex URL, return as-is
        if clean_id.startswith('https://openalex.org/W'):
            self.logger.info(f"Already formatted OpenAlex URL: {clean_id}")
            return clean_id
        
        # If already has W prefix, add the base URL
        if clean_id.startswith('W') and len(clean_id) > 1:
            formatted_id = f"https://openalex.org/{clean_id}"
            self.logger.info(f"Added base URL to W-prefixed ID: {formatted_id}")
            return formatted_id
        
        # For digit-only IDs, add W prefix and create OpenAlex URL
        if clean_id.isdigit() or clean_id.replace('-', '').isdigit():
            formatted_id = f"https://openalex.org/W{clean_id}"
            self.logger.info(f"Formatted digit ID to OpenAlex URL: {formatted_id}")
            return formatted_id
        
        # For DOI or other formats, try to use as-is
        self.logger.warning(f"Unknown ID format, using as-is: {clean_id}")
        return clean_id
        
        # Default: assume it's an OpenAlex work ID and add W prefix
        return f"https://openalex.org/W{clean_id}"
    
    def get_paper_citations(self, paper_id: str, source: str = "openalex") -> List[Dict[str, Any]]:
        """
        Get papers that cite the given paper
        
        Args:
            paper_id: Paper identifier (OpenAlex ID, DOI, etc.)
            source: Data source ('openalex', 'semantic_scholar', 'auto' for fallback)
            
        Returns:
            List of citing papers with metadata
        """
        try:
            if source == "openalex":
                return self._get_openalex_citations(paper_id)
            elif source == "semantic_scholar":
                return self._get_semantic_scholar_citations(paper_id)
            elif source == "auto":
                # Try OpenAlex first, fallback to Semantic Scholar
                citations = self._get_openalex_citations(paper_id)
                if not citations:
                    self.logger.info(f"No citations from OpenAlex, trying Semantic Scholar for {paper_id}")
                    citations = self._get_semantic_scholar_citations(paper_id)
                return citations
            else:
                self.logger.warning(f"Unknown citation source: {source}")
                return []
        except Exception as e:
            self.logger.error(f"Failed to get citations for {paper_id}: {e}")
            return []
    
    def get_paper_references(self, paper_id: str, source: str = "openalex") -> List[Dict[str, Any]]:
        """
        Get papers referenced by the given paper
        
        Args:
            paper_id: Paper identifier
            source: Data source ('openalex', 'semantic_scholar', 'auto' for fallback)
            
        Returns:
            List of referenced papers with metadata
        """
        try:
            if source == "openalex":
                return self._get_openalex_references(paper_id)
            elif source == "semantic_scholar":
                return self._get_semantic_scholar_references(paper_id)
            elif source == "auto":
                # Try OpenAlex first, fallback to Semantic Scholar
                references = self._get_openalex_references(paper_id)
                if not references:
                    self.logger.info(f"No references from OpenAlex, trying Semantic Scholar for {paper_id}")
                    references = self._get_semantic_scholar_references(paper_id)
                return references
            else:
                self.logger.warning(f"Unknown reference source: {source}")
                return []
        except Exception as e:
            self.logger.error(f"Failed to get references for {paper_id}: {e}")
            return []
    
    def _get_openalex_citations(self, paper_id: str, max_citations: int = 100) -> List[Dict[str, Any]]:
        """Get citing papers from OpenAlex API"""
        try:
            # Clean and format paper ID for OpenAlex
            openalex_url = self._format_openalex_id(paper_id)
            if not openalex_url:
                self.logger.warning(f"Could not format paper ID for OpenAlex: {paper_id}")
                return []
            
            # Extract work ID from the OpenAlex URL for API call
            if openalex_url.startswith('https://openalex.org/'):
                work_id = openalex_url.split('/')[-1]  # Extract W123456789
            else:
                work_id = openalex_url
            
            # OpenAlex API call for citing papers
            url = f"https://api.openalex.org/works?filter=cites:{work_id}"
            
            self.logger.info(f"Fetching citations from OpenAlex: {url}")
            time.sleep(self.rate_limit_delay)
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 404:
                self.logger.warning(f"Paper not found in OpenAlex: {paper_id} (formatted as {openalex_id})")
                return []
            elif response.status_code == 403:
                self.logger.warning(f"Access forbidden for OpenAlex request: {paper_id}")
                return []
            
            response.raise_for_status()
            
            data = response.json()
            citations = []
            
            for work in data.get('results', []):
                # Handle missing abstracts with fallback
                abstract = work.get('abstract')
                if not abstract or abstract.strip() == '':
                    concepts = [concept.get('display_name', '') for concept in work.get('concepts', [])[:3]]
                    abstract = f"[Abstract not available] Research about {', '.join(concepts) if concepts else 'scientific topics'}."
                
                citation = {
                    'id': work.get('id', ''),
                    'title': work.get('title', ''),
                    'publication_year': work.get('publication_year'),
                    'cited_by_count': work.get('cited_by_count', 0),
                    'authors': [
                        author.get('author', {}).get('display_name', '') 
                        for author in work.get('authorships', [])
                        if author.get('author', {}).get('display_name', '')
                    ],
                    'venue': work.get('primary_location', {}).get('source', {}).get('display_name', ''),
                    'doi': work.get('doi'),
                    'url': work.get('id', ''),
                    'abstract': abstract,
                    'concepts': [
                        concept.get('display_name', '') 
                        for concept in work.get('concepts', [])[:5]
                    ],
                    'open_access': work.get('open_access', {}).get('is_oa', False),
                    'type': work.get('type', 'article'),
                    'source': 'openalex'
                }
                citations.append(citation)
            
            self.logger.info(f"Retrieved {len(citations)} citations for {paper_id}")
            return citations
            
        except Exception as e:
            self.logger.error(f"OpenAlex citations fetch failed for {paper_id}: {e}")
            return []
    
    def _get_openalex_references(self, paper_id: str, max_references: int = 100) -> List[Dict[str, Any]]:
        """Get referenced papers from OpenAlex API"""
        try:
            # Format paper ID for OpenAlex
            openalex_id = self._format_openalex_id(paper_id)
            if not openalex_id:
                self.logger.warning(f"Could not format paper ID for OpenAlex: {paper_id}")
                return []
            
            # Extract the OpenAlex work ID from the URL for the API call
            if openalex_id.startswith('https://openalex.org/W'):
                work_id = openalex_id.split('/')[-1]
            elif openalex_id.startswith('W'):
                work_id = openalex_id
            else:
                # For DOI or arXiv URLs, use them directly
                work_id = openalex_id
            
            # Get paper details first
            url = f"https://api.openalex.org/works/{work_id}"
            self.logger.info(f"Fetching paper details from OpenAlex: {url}")
            time.sleep(self.rate_limit_delay)
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 404:
                self.logger.warning(f"Paper not found in OpenAlex: {paper_id} (formatted as {openalex_id})")
                return []
            elif response.status_code == 403:
                self.logger.warning(f"Access forbidden for OpenAlex request: {paper_id}")
                return []
            
            response.raise_for_status()
            
            paper_data = response.json()
            
            # Check if paper_data is valid
            if not paper_data or not isinstance(paper_data, dict):
                self.logger.warning(f"Invalid or empty response from OpenAlex for {paper_id}")
                return []
            
            referenced_works = paper_data.get('referenced_works', [])
            
            if not referenced_works:
                self.logger.info(f"No references found for {paper_id}")
                return []
            
            # Get details for referenced works (batch request)
            # Take first N references to avoid huge requests
            referenced_works = referenced_works[:max_references]
            references_ids = [ref.split('/')[-1] for ref in referenced_works]
            
            # Batch API call for referenced papers
            url = f"https://api.openalex.org/works?filter=openalex_id:{'|'.join(references_ids[:50])}"
            time.sleep(self.rate_limit_delay)
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            # print("getting data ",data)
            references = []
            
            for work in data.get('results', []):
                # Handle missing abstract
                abstract = work.get('abstract')
                if not abstract or abstract.strip() == '':
                    concepts = [concept.get('display_name', '') for concept in work.get('concepts', [])[:3]]
                    abstract = f"[Abstract not available] Research about {', '.join(concepts) if concepts else 'scientific topics'}."
                
                reference = {
                    'id': work.get('id', ''),
                    'title': work.get('title', ''),
                    'publication_year': work.get('publication_year'),
                    'cited_by_count': work.get('cited_by_count', 0),
                    'authors': [
                        author.get('author', {}).get('display_name', '') 
                        for author in work.get('authorships', [])
                        if author.get('author', {}).get('display_name', '')
                    ],
                    'venue': work.get('primary_location', {}).get('source', {}).get('display_name', ''),
                    'doi': work.get('doi'),
                    'url': work.get('id', ''),
                    'abstract': abstract,
                    'concepts': [
                        concept.get('display_name', '') 
                        for concept in work.get('concepts', [])[:5]
                    ],
                    'open_access': work.get('open_access', {}).get('is_oa', False),
                    'type': work.get('type', 'article'),
                    'source': 'openalex'
                }
                references.append(reference)
            
            self.logger.info(f"Retrieved {len(references)} references for {paper_id}")
            return references
            
        except Exception as e:
            self.logger.error(f"OpenAlex references fetch failed for {paper_id}: {e}")
            return []
    
    def _get_semantic_scholar_citations(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get citing papers from Semantic Scholar API"""
        try:
            # Semantic Scholar API endpoint
            url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations"
            params = {
                'fields': 'title,year,authors,venue,citationCount,openAccessPdf,abstract',
                'limit': 100
            }
            
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                citations = []
                
                for citation in data.get('data', []):
                    citing_paper = citation.get('citingPaper', {})
                    citation_data = {
                        'id': citing_paper.get('paperId', ''),
                        'title': citing_paper.get('title', ''),
                        'publication_year': citing_paper.get('year'),
                        'cited_by_count': citing_paper.get('citationCount', 0),
                        'authors': [
                            author.get('name', '') 
                            for author in citing_paper.get('authors', [])
                        ],
                        'venue': citing_paper.get('venue', ''),
                        'abstract': citing_paper.get('abstract'),
                        'open_access': bool(citing_paper.get('openAccessPdf')),
                        'source': 'semantic_scholar'
                    }
                    citations.append(citation_data)
                
                return citations
            else:
                self.logger.warning(f"Semantic Scholar API error: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Semantic Scholar citations fetch failed: {e}")
            return []
    
    def _get_semantic_scholar_references(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get referenced papers from Semantic Scholar API"""
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/references"
            params = {
                'fields': 'title,year,authors,venue,citationCount,openAccessPdf,abstract',
                'limit': 100
            }
            
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                references = []
                
                for reference in data.get('data', []):
                    cited_paper = reference.get('citedPaper', {})
                    reference_data = {
                        'id': cited_paper.get('paperId', ''),
                        'title': cited_paper.get('title', ''),
                        'publication_year': cited_paper.get('year'),
                        'cited_by_count': cited_paper.get('citationCount', 0),
                        'authors': [
                            author.get('name', '') 
                            for author in cited_paper.get('authors', [])
                        ],
                        'venue': cited_paper.get('venue', ''),
                        'abstract': cited_paper.get('abstract'),
                        'open_access': bool(cited_paper.get('openAccessPdf')),
                        'source': 'semantic_scholar'
                    }
                    references.append(reference_data)
                
                return references
            else:
                self.logger.warning(f"Semantic Scholar API error: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Semantic Scholar references fetch failed: {e}")
            return []
    
    def get_paper_metadata(self, paper_id: str, source: str = "openalex") -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a single paper"""
        try:
            if source == "openalex":
                return self._get_openalex_metadata(paper_id)
            elif source == "semantic_scholar":
                return self._get_semantic_scholar_metadata(paper_id)
            elif source == "auto":
                # Try OpenAlex first, fallback to Semantic Scholar
                metadata = self._get_openalex_metadata(paper_id)
                if not metadata:
                    self.logger.info(f"No metadata from OpenAlex, trying Semantic Scholar for {paper_id}")
                    metadata = self._get_semantic_scholar_metadata(paper_id)
                return metadata
            else:
                self.logger.warning(f"Unknown metadata source: {source}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get metadata for {paper_id}: {e}")
            return None
    
    def _get_openalex_metadata(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get paper metadata from OpenAlex"""
        try:
            # Format paper ID for OpenAlex
            openalex_url = self._format_openalex_id(paper_id)
            if not openalex_url:
                self.logger.warning(f"Could not format paper ID for OpenAlex: {paper_id}")
                return None
            
            # Extract work ID from the OpenAlex URL for API call
            if openalex_url.startswith('https://openalex.org/'):
                work_id = openalex_url.split('/')[-1]  # Extract W123456789
            else:
                work_id = openalex_url
            
            url = f"https://api.openalex.org/works/{work_id}"
            
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            work = response.json()
            
            # Handle missing abstracts with fallback
            abstract = work.get('abstract')
            if not abstract or abstract.strip() == '':
                concepts = [concept.get('display_name', '') for concept in work.get('concepts', [])[:3]]
                abstract = f"[Abstract not available] Research about {', '.join(concepts) if concepts else 'scientific topics'}."
            
            metadata = {
                'id': work.get('id', ''),
                'title': work.get('title', ''),
                'publication_year': work.get('publication_year'),
                'cited_by_count': work.get('cited_by_count', 0),
                'authors': [
                    author.get('author', {}).get('display_name', '') 
                    for author in work.get('authorships', [])
                    if author.get('author', {}).get('display_name', '')
                ],
                'venue': work.get('primary_location', {}).get('source', {}).get('display_name', ''),
                'doi': work.get('doi'),
                'url': work.get('id', ''),
                'abstract': abstract,
                'concepts': [
                    {
                        'name': concept.get('display_name', ''),
                        'score': concept.get('score', 0),
                        'level': concept.get('level', 0)
                    }
                    for concept in work.get('concepts', [])
                ],
                'open_access': work.get('open_access', {}).get('is_oa', False),
                'type': work.get('type', 'article'),
                'language': work.get('language'),
                'source': 'openalex'
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"OpenAlex metadata fetch failed: {e}")
            return None
    
    def search_papers_by_title(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for papers by title using OpenAlex API"""
        try:
            if not title or title.strip() == "Unknown Paper":
                self.logger.warning("Cannot search for papers with empty or unknown title")
                return []
                
            # Clean the title for search
            clean_title = title.strip()
            
            # OpenAlex search API
            url = "https://api.openalex.org/works"
            params = {
                'search': clean_title,
                'per-page': limit,
                'sort': 'cited_by_count:desc'  # Sort by citation count
            }
            
            self.logger.info(f"Searching OpenAlex for papers with title: {clean_title}")
            time.sleep(self.rate_limit_delay)
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            papers = []
            
            for work in data.get('results', []):
                # Handle missing abstracts with fallback
                abstract = work.get('abstract')
                if not abstract or abstract.strip() == '':
                    concepts = [concept.get('display_name', '') for concept in work.get('concepts', [])[:3]]
                    abstract = f"[Abstract not available] Research about {', '.join(concepts) if concepts else 'scientific topics'}."
                
                paper = {
                    'id': work.get('id', ''),
                    'title': work.get('title', ''),
                    'publication_year': work.get('publication_year'),
                    'year': work.get('publication_year'),  # Alias for compatibility
                    'cited_by_count': work.get('cited_by_count', 0),
                    'authors': [
                        author.get('author', {}).get('display_name', '') 
                        for author in work.get('authorships', [])
                    ],
                    'venue': work.get('primary_location', {}).get('source', {}).get('display_name', ''),
                    'doi': work.get('doi'),
                    'url': work.get('id', ''),
                    'abstract': abstract,
                    'concepts': [
                        concept.get('display_name', '') 
                        for concept in work.get('concepts', [])[:3]
                    ],
                    'open_access': work.get('open_access', {}).get('is_oa', False),
                    'type': work.get('type', 'article'),
                    'source': 'openalex'
                }
                papers.append(paper)
            
            self.logger.info(f"Found {len(papers)} papers for title search: {clean_title}")
            return papers
            
        except Exception as e:
            self.logger.error(f"Title search failed for '{title}': {e}")
            return []