"""
Vector Database Module for Semantic Paper Search
Handles FAISS vector operations, embeddings, and hybrid search functionality
"""

import faiss
import numpy as np
import json
import logging
import os
import pickle
import threading
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


class VectorDatabase:
    """Vector database for semantic paper search using FAISS with file persistence"""
    
    def __init__(self, embedding_model: str = 'all-MiniLM-L6-v2', data_dir: str = 'data'):
        """
        Initialize Vector Database with persistent storage
        
        Args:
            embedding_model: HuggingFace model name for sentence embeddings
            data_dir: Directory for storing persistent data
        """
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            self.dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {embedding_model} (dim: {self.dimension})")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
        
        # File paths for persistence
        self.data_dir = data_dir
        self.index_file = os.path.join(data_dir, 'faiss_index.bin')
        self.metadata_file = os.path.join(data_dir, 'papers_metadata.pkl')
        self.tfidf_file = os.path.join(data_dir, 'tfidf_vectorizer.pkl')
        self.tfidf_matrix_file = os.path.join(data_dir, 'tfidf_matrix.pkl')
        
        # Thread lock for safe concurrent access
        self._lock = threading.Lock()
        
        # Storage for paper metadata
        self.papers_metadata = {}  # {vector_id: paper_data}
        self.paper_counter = 0
        
        # Hybrid search components
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000, 
            stop_words='english',
            ngram_range=(1, 2),  # Include bigrams for better matching
            max_df=0.8,  # Ignore terms in >80% of documents
            min_df=2     # Ignore terms in <2 documents
        )
        self.tfidf_matrix = None
        
        # Load or create persistent storage
        self._initialize_persistent_storage()
        self.indexed_texts = []
        
        logger.info("Vector database initialized successfully")
    
    def _initialize_persistent_storage(self):
        """Initialize persistent storage, loading existing data if available"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Check if persistent data exists
            files_exist = all(os.path.exists(f) for f in [
                self.index_file, 
                self.metadata_file
            ])
            
            if files_exist:
                self._load_from_disk()
            else:
                self._create_new_index()
                
        except Exception as e:
            logger.error(f"Failed to initialize persistent storage: {e}")
            self._create_new_index()
    
    def _load_from_disk(self):
        """Load existing vector database from disk"""
        try:
            logger.info("📚 Loading existing vector database from disk...")
            
            # Load FAISS index
            self.index = faiss.read_index(self.index_file)
            
            # Load metadata
            with open(self.metadata_file, 'rb') as f:
                self.papers_metadata = pickle.load(f)
            
            self.paper_counter = len(self.papers_metadata)
            
            # Load TF-IDF components if they exist
            if os.path.exists(self.tfidf_file) and os.path.exists(self.tfidf_matrix_file):
                with open(self.tfidf_file, 'rb') as f:
                    self.tfidf_vectorizer = pickle.load(f)
                with open(self.tfidf_matrix_file, 'rb') as f:
                    self.tfidf_matrix = pickle.load(f)
                # Rebuild indexed_texts from metadata
                self.indexed_texts = [self._create_paper_text(paper) for paper in self.papers_metadata.values()]
                logger.info(f"✅ Loaded TF-IDF components with {self.tfidf_matrix.shape[0]} documents")
            
            logger.info(f"✅ Successfully loaded {self.paper_counter} papers from persistent storage")
            
        except Exception as e:
            logger.error(f"Failed to load from disk, creating new index: {e}")
            self._create_new_index()
    
    def _create_new_index(self):
        """Create new empty vector database"""
        logger.info("🆕 Creating new vector database")
        self.index = faiss.IndexFlatIP(self.dimension)
        self.papers_metadata = {}
        self.paper_counter = 0
        self.tfidf_matrix = None
    
    def _save_to_disk(self):
        """Save current vector database state to disk"""
        try:
            with self._lock:
                # Create directory if it doesn't exist
                os.makedirs(self.data_dir, exist_ok=True)
                
                # Save FAISS index
                faiss.write_index(self.index, self.index_file)
                
                # Save metadata
                with open(self.metadata_file, 'wb') as f:
                    pickle.dump(self.papers_metadata, f)
                
                # Save TF-IDF components if they exist
                if self.tfidf_matrix is not None:
                    with open(self.tfidf_file, 'wb') as f:
                        pickle.dump(self.tfidf_vectorizer, f)
                    with open(self.tfidf_matrix_file, 'wb') as f:
                        pickle.dump(self.tfidf_matrix, f)
                
                logger.info(f"💾 Successfully saved {self.paper_counter} papers to disk")
                
        except Exception as e:
            logger.error(f"Failed to save vector database to disk: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        return {
            'total_papers': self.paper_counter,
            'vector_dimension': self.dimension,
            'index_size': self.index.ntotal,
            'has_tfidf': self.tfidf_matrix is not None,
            'tfidf_documents': self.tfidf_matrix.shape[0] if self.tfidf_matrix is not None else 0,
            'data_directory': self.data_dir,
            'files_exist': {
                'index': os.path.exists(self.index_file),
                'metadata': os.path.exists(self.metadata_file),
                'tfidf': os.path.exists(self.tfidf_file),
                'tfidf_matrix': os.path.exists(self.tfidf_matrix_file)
            }
        }

    def add_papers(self, papers: List[Dict[str, Any]]) -> int:
        """
        Add papers to vector database with embeddings
        
        Args:
            papers: List of paper dictionaries
            
        Returns:
            Number of papers successfully added
        """
        if not papers:
            logger.warning("No papers provided to add to vector database")
            return 0
        
        logger.info(f"Adding {len(papers)} papers to vector database...")
        
        added_count = 0
        embeddings = []
        texts = []
        
        for paper in papers:
            try:
                # Create rich text representation for embedding
                paper_text = self._create_paper_text(paper)
                
                # Generate embedding
                embedding = self.embedding_model.encode([paper_text])[0]
                embeddings.append(embedding)
                texts.append(paper_text)
                
                # Store metadata with unique vector ID
                paper_id = self.paper_counter
                self.papers_metadata[paper_id] = {
                    **paper,
                    'indexed_text': paper_text,
                    'vector_id': paper_id,
                    'embedding_generated': True
                }
                
                self.paper_counter += 1
                added_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to process paper '{paper.get('title', 'Unknown')}': {e}")
                continue
        
        # Add embeddings to FAISS index
        if embeddings:
            try:
                embeddings_array = np.array(embeddings).astype('float32')
                faiss.normalize_L2(embeddings_array)  # Normalize for cosine similarity
                self.index.add(embeddings_array)
                
                # Update TF-IDF matrix for hybrid search
                self.indexed_texts.extend(texts)
                self._update_tfidf_matrix()
                
                logger.info(f"Successfully added {added_count} papers to vector database")
                
                # 💾 Auto-save to disk after successful addition
                if added_count > 0:
                    self._save_to_disk()
                
            except Exception as e:
                logger.error(f"Failed to add embeddings to FAISS index: {e}")
                return 0
        
        return added_count
    
    def search(self, query: str, k: int = 10, hybrid_weight: float = 0.7, 
               min_similarity: float = 0.1) -> List[Dict[str, Any]]:
        """
        Search for similar papers using hybrid semantic + keyword search
        
        Args:
            query: Search query string
            k: Number of results to return
            hybrid_weight: Weight for semantic vs keyword search (0.0-1.0)
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of paper dictionaries with similarity scores
        """
        if self.index.ntotal == 0:
            logger.warning("Vector database is empty - no papers to search")
            return []
        
        try:
            logger.info(f"Searching vector database for: '{query[:50]}...'")
            
            # Perform semantic search
            semantic_results = self._semantic_search(query, k * 2)  # Get more for reranking
            
            # Perform keyword search if TF-IDF is available
            keyword_results = []
            if self.tfidf_matrix is not None:
                keyword_results = self._keyword_search(query, k * 2)
            
            # Combine results with hybrid scoring
            if keyword_results:
                combined_results = self._hybrid_combine(semantic_results, keyword_results, hybrid_weight)
            else:
                combined_results = semantic_results
                logger.info("Using semantic search only (TF-IDF not available)")
            
            # Filter by minimum similarity and limit results
            filtered_results = [
                result for result in combined_results 
                if result.get('final_score', 0) >= min_similarity
            ]
            
            final_results = filtered_results[:k]
            logger.info(f"Returning {len(final_results)} results from vector search")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _create_paper_text(self, paper: Dict[str, Any]) -> str:
        """
        Create rich text representation of paper for embedding
        
        Args:
            paper: Paper dictionary
            
        Returns:
            Combined text string for embedding
        """
        # Extract key fields
        title = paper.get('title', '')
        summary = paper.get('summary', '')
        authors = ' '.join(paper.get('authors', [])[:5])  # Limit authors
        concepts = ' '.join(paper.get('concepts', [])[:10])  # Limit concepts
        journal = paper.get('journal', '')
        keywords = ' '.join(paper.get('keywords', []))
        
        # Create weighted text (title and concepts are more important)
        weighted_text = f"{title} {title} {summary} {authors} {concepts} {concepts} {journal} {keywords}"
        
        return weighted_text.strip()
    
    def _semantic_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """
        Perform semantic search using embeddings
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of papers with semantic similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]
            query_embedding = np.array([query_embedding]).astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Search FAISS index
            similarities, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
            
            results = []
            for sim, idx in zip(similarities[0], indices[0]):
                if idx != -1 and idx in self.papers_metadata:  # -1 indicates no result found
                    result = self.papers_metadata[idx].copy()
                    result['semantic_score'] = float(sim)
                    result['search_type'] = 'semantic'
                    results.append(result)
            
            logger.debug(f"Semantic search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _keyword_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search using TF-IDF
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of papers with keyword similarity scores
        """
        if self.tfidf_matrix is None:
            return []
        
        try:
            # Transform query to TF-IDF vector
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Calculate similarities
            similarities = (self.tfidf_matrix * query_vector.T).toarray().flatten()
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[-k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0 and idx < len(self.papers_metadata):
                    # Find paper by index in stored texts
                    paper_found = False
                    for vector_id, paper_data in self.papers_metadata.items():
                        if idx < len(self.indexed_texts) and paper_data.get('indexed_text') == self.indexed_texts[idx]:
                            result = paper_data.copy()
                            result['keyword_score'] = float(similarities[idx])
                            result['search_type'] = 'keyword'
                            results.append(result)
                            paper_found = True
                            break
                    
                    if not paper_found:
                        logger.debug(f"Could not find paper for TF-IDF index {idx}")
            
            logger.debug(f"Keyword search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []
    
    def _hybrid_combine(self, semantic_results: List[Dict], keyword_results: List[Dict], 
                       semantic_weight: float) -> List[Dict[str, Any]]:
        """
        Combine semantic and keyword search results with hybrid scoring
        
        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search
            semantic_weight: Weight for semantic vs keyword (0.0-1.0)
            
        Returns:
            Combined and ranked results
        """
        try:
            # Create combined scoring dictionary
            paper_scores = {}
            
            # Normalize scores to 0-1 range
            max_semantic = max([r.get('semantic_score', 0) for r in semantic_results], default=1.0)
            max_keyword = max([r.get('keyword_score', 0) for r in keyword_results], default=1.0)
            
            # Add semantic scores
            for result in semantic_results:
                paper_id = result.get('vector_id')
                if paper_id is not None:
                    normalized_semantic = result.get('semantic_score', 0) / max_semantic if max_semantic > 0 else 0
                    paper_scores[paper_id] = {
                        'paper': result,
                        'semantic_score': normalized_semantic,
                        'keyword_score': 0
                    }
            
            # Add keyword scores
            for result in keyword_results:
                paper_id = result.get('vector_id')
                if paper_id is not None:
                    normalized_keyword = result.get('keyword_score', 0) / max_keyword if max_keyword > 0 else 0
                    
                    if paper_id in paper_scores:
                        paper_scores[paper_id]['keyword_score'] = normalized_keyword
                    else:
                        paper_scores[paper_id] = {
                            'paper': result,
                            'semantic_score': 0,
                            'keyword_score': normalized_keyword
                        }
            
            # Calculate hybrid scores
            for paper_id, scores in paper_scores.items():
                hybrid_score = (semantic_weight * scores['semantic_score'] + 
                              (1 - semantic_weight) * scores['keyword_score'])
                scores['paper']['final_score'] = hybrid_score
                scores['paper']['search_method'] = 'hybrid'
            
            # Sort by hybrid score
            sorted_papers = sorted(paper_scores.values(), 
                                 key=lambda x: x['paper']['final_score'], 
                                 reverse=True)
            
            result_papers = [item['paper'] for item in sorted_papers]
            logger.debug(f"Hybrid search combined {len(result_papers)} unique papers")
            
            return result_papers
            
        except Exception as e:
            logger.error(f"Hybrid combination failed: {e}")
            return semantic_results  # Fallback to semantic results
    
    def _update_tfidf_matrix(self):
        """Update TF-IDF matrix with current indexed texts"""
        try:
            if self.indexed_texts:
                self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.indexed_texts)
                logger.debug(f"Updated TF-IDF matrix with {len(self.indexed_texts)} documents")
        except Exception as e:
            logger.warning(f"Failed to update TF-IDF matrix: {e}")
            self.tfidf_matrix = None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector database statistics
        
        Returns:
            Dictionary with database statistics
        """
        return {
            "total_papers": self.index.ntotal,
            "dimension": self.dimension,
            "embedding_model": str(self.embedding_model),
            "has_tfidf": self.tfidf_matrix is not None,
            "tfidf_vocabulary_size": len(self.tfidf_vectorizer.vocabulary_) if hasattr(self.tfidf_vectorizer, 'vocabulary_') else 0,
            "memory_usage_mb": self.index.ntotal * self.dimension * 4 / (1024 * 1024)  # Approximate
        }
    
    def clear_database(self):
        """Clear all data from the vector database"""
        try:
            self.index.reset()
            self.papers_metadata.clear()
            self.indexed_texts.clear()
            self.tfidf_matrix = None
            self.paper_counter = 0
            logger.info("Vector database cleared successfully")
            
            # Also clear persistent storage
            self._clear_persistent_files()
            
        except Exception as e:
            logger.error(f"Failed to clear vector database: {e}")
    
    def _clear_persistent_files(self):
        """Remove all persistent storage files"""
        try:
            files_to_remove = [
                self.index_file,
                self.metadata_file, 
                self.tfidf_file,
                self.tfidf_matrix_file
            ]
            
            for file_path in files_to_remove:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Removed persistent file: {file_path}")
                    
        except Exception as e:
            logger.error(f"Failed to clear persistent files: {e}")
    
    def manual_save(self):
        """Manually trigger save to disk"""
        self._save_to_disk()
        
    def get_persistent_storage_size(self) -> Dict[str, Any]:
        """Get information about persistent storage files"""
        try:
            files_info = {}
            total_size = 0
            
            for name, path in [
                ('index', self.index_file),
                ('metadata', self.metadata_file),
                ('tfidf', self.tfidf_file),
                ('tfidf_matrix', self.tfidf_matrix_file)
            ]:
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    files_info[name] = {
                        'exists': True,
                        'size_bytes': size,
                        'size_mb': round(size / (1024 * 1024), 2)
                    }
                    total_size += size
                else:
                    files_info[name] = {'exists': False, 'size_bytes': 0, 'size_mb': 0}
            
            return {
                'files': files_info,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'data_directory': self.data_dir
            }
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {'error': str(e)}