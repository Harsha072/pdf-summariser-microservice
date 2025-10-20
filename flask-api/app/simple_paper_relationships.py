"""
Simple Paper Relationships Explorer
Easy to understand and explain - shows paper "family trees"
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict, Counter
import time

# Enhanced packages for better citation analysis
try:
    from scholarly import scholarly
    import networkx as nx
    ENHANCED_PACKAGES_AVAILABLE = True
    print("✅ Enhanced packages loaded: scholarly + networkx")
except ImportError as e:
    ENHANCED_PACKAGES_AVAILABLE = False
    print(f"⚠️ Enhanced packages not available: {e}")

logger = logging.getLogger(__name__)


class SimplePaperRelationships:
    """
    Simple paper relationship explorer - easy to understand and explain
    
    Core concept: When you find an interesting paper, see what it built upon
    and what newer papers have built upon it - like a family tree for research ideas.
    """
    
    def __init__(self, citation_extractor):
        self.citation_extractor = citation_extractor
        self.logger = logger
        
        # Setup enhanced scholarly if available
        self.enhanced_mode = ENHANCED_PACKAGES_AVAILABLE
        if self.enhanced_mode:
            try:
                self.logger.info("Setting up scholarly (Google Scholar access)...")
                self.scholarly_ready = True
            except Exception as e:
                self.logger.warning(f"Scholarly setup failed: {e}, using fallback mode")
                self.enhanced_mode = False
                self.scholarly_ready = False
        
        self.logger.info(f"SimplePaperRelationships initialized - Enhanced mode: {self.enhanced_mode}")
    
    def explore_paper_connections(self, paper_id: str, max_connections: int = 10) -> Dict[str, Any]:
        """
        Simple exploration of paper connections
        
        Args:
            paper_id: The paper to explore
            max_connections: Maximum connections to show in each direction
            
        Returns:
            Dictionary with foundation papers, building papers, and insights
        """
        try:
            self.logger.info(f"Exploring connections for paper: {paper_id}")
            
            # Step 1: What did this paper build upon? (References)
            self.logger.info("Fetching papers this built upon...")
            references = self.citation_extractor.get_paper_references(paper_id, source="auto")
            
            # Step 2: What built upon this paper? (Citations)  
            self.logger.info("Fetching papers that built upon this...")
            citations = self.citation_extractor.get_paper_citations(paper_id, source="auto")
            
            # Step 3: Get metadata for the main paper
            paper_metadata = self.citation_extractor.get_paper_metadata(paper_id, source="auto")
            
            # If metadata is missing, create a minimal fallback so downstream code can run
            if not paper_metadata:
                self.logger.warning(f"No metadata found for paper: {paper_id}")
                paper_metadata = {
                    'id': str(paper_id),
                    'title': 'Unknown Paper',
                    'publication_year': None,
                    'year': None,
                    'cited_by_count': 0,
                    'authors': [],
                    'venue': '',
                    'abstract': ''
                }

            # Step 4: Simple analysis
            analysis = self._analyze_connections(references, citations, paper_metadata)

            # Step 5: Enhanced network analysis (if available)
            network_analysis = None
            if self.enhanced_mode:
                network_analysis = self._create_network_graph(paper_metadata, references, citations)
            
            # Step 6: Find similar papers (enhanced if available)
            similar_papers = []
            if (paper_metadata and 
                paper_metadata.get('title') and 
                paper_metadata.get('title') != 'Unknown Paper' and
                paper_metadata.get('title').strip()):
                similar_papers = self._find_similar_papers(paper_metadata['title'], limit=3)
            
            # Step 7: Find interesting patterns
            patterns = self._find_interesting_patterns(references, citations)
            
            result = {
                "success": True,
                "paper_id": paper_id,
                "paper_info": self._format_paper_info(paper_metadata),
                "connections": {
                    "foundation_papers": self._get_most_important(references, max_connections//2),
                    "building_papers": self._get_most_recent(citations, max_connections//2),
                    "similar_papers": similar_papers,
                    "related_authors": self._find_related_authors(references, citations),
                    "research_timeline": self._create_simple_timeline(references, citations, paper_metadata)
                },
                "insights": analysis,
                "patterns": patterns,
                "network_analysis": network_analysis,
                "enhanced_features": {
                    "enabled": self.enhanced_mode,
                    "google_scholar_search": len(similar_papers) > 0,
                    "network_analysis": network_analysis is not None,
                    "data_sources": ["OpenAlex API"] + (["Google Scholar"] if self.enhanced_mode else [])
                },
                "visualization_data": self._prepare_simple_viz_data(references, citations, paper_metadata)
            }
            
            self.logger.info(f"Successfully explored connections: {len(references)} references, {len(citations)} citations, {len(similar_papers)} similar papers (enhanced: {self.enhanced_mode})")
            return result
            
        except Exception as e:
            self.logger.error(f"Paper connection exploration failed for {paper_id}: {e}")
            
            # More specific error messages
            if "NoneType" in str(e):
                error_msg = f"Paper '{paper_id}' not found in database. Please check the paper ID."
            else:
                error_msg = str(e)
            
            return {
                "success": False, 
                "error": error_msg,
                "paper_id": paper_id,
                "message": "Failed to retrieve paper data. This might be due to an invalid paper ID or the paper not being available in our database."
            }
    
    def explore_multiple_papers(self, paper_ids: List[str]) -> Dict[str, Any]:
        """
        Explore relationships between multiple papers
        
        Args:
            paper_ids: List of paper IDs to explore
            
        Returns:
            Family trees for multiple papers with cross-connections
        """
        try:
            if len(paper_ids) > 5:
                paper_ids = paper_ids[:5]  # Limit to keep it simple
            
            family_trees = []
            all_connections = {}
            
            for paper_id in paper_ids:
                connections = self.explore_paper_connections(paper_id)
                if connections.get('success'):
                    family_trees.append(connections)
                    all_connections[paper_id] = connections
            
            # Find cross-connections between the papers
            cross_connections = self._find_cross_connections(all_connections)
            
            return {
                "success": True,
                "family_trees": family_trees,
                "cross_connections": cross_connections,
                "summary": self._create_multi_paper_summary(family_trees),
                "explanation": "Shows what papers built upon each selected paper and what newer papers built upon them"
            }
            
        except Exception as e:
            self.logger.error(f"Multi-paper exploration failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_paper_info(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Format basic paper information"""
        if not metadata:
            return {"title": "Unknown Paper", "year": None, "authors": []}
        
        return {
            "title": metadata.get('title', 'Unknown Paper'),
            "year": metadata.get('publication_year') or metadata.get('year'),
            "authors": metadata.get('authors', [])[:3],  # First 3 authors
            "venue": metadata.get('venue', ''),
            "abstract": metadata.get('abstract', '')[:200] + '...' if metadata.get('abstract') else '',
            "citation_count": metadata.get('cited_by_count', 0),
            "doi": metadata.get('doi', ''),
            "url": metadata.get('url', '')
        }
    
    def _get_most_important(self, papers: List[Dict], limit: int) -> List[Dict]:
        """Get most cited/important papers"""
        if not papers:
            return []
        
        # Sort by citation count, then by year (newer first for ties)
        sorted_papers = sorted(
            papers, 
            key=lambda x: (x.get('cited_by_count', 0), x.get('publication_year', 0)), 
            reverse=True
        )
        
        return [self._simplify_paper_data(paper) for paper in sorted_papers[:limit]]
    
    def _get_most_recent(self, papers: List[Dict], limit: int) -> List[Dict]:
        """Get most recent papers"""
        if not papers:
            return []
        
        # Sort by year first, then by citation count
        sorted_papers = sorted(
            papers, 
            key=lambda x: (x.get('publication_year', 0), x.get('cited_by_count', 0)), 
            reverse=True
        )
        
        return [self._simplify_paper_data(paper) for paper in sorted_papers[:limit]]
    
    def _simplify_paper_data(self, paper: Dict) -> Dict:
        """Simplify paper data for easy display"""
        return {
            "id": paper.get('id', ''),
            "title": paper.get('title', 'Unknown Title')[:80] + ('...' if len(paper.get('title', '')) > 80 else ''),
            "year": paper.get('publication_year') or paper.get('year'),
            "authors": paper.get('authors', [])[:2],  # First 2 authors
            "citation_count": paper.get('cited_by_count', 0),
            "venue": paper.get('venue', ''),
            "url": paper.get('url', ''),
            "influence_score": min(100, (paper.get('cited_by_count', 0) / 10))  # Simple 0-100 score
        }
    
    def _find_related_authors(self, references: List[Dict], citations: List[Dict]) -> List[Dict]:
        """Find authors who appear in both references and citations"""
        ref_authors = {}
        cite_authors = {}
        
        # Collect reference authors
        for paper in references:
            for author in paper.get('authors', []):
                if isinstance(author, str):
                    author_name = author
                elif isinstance(author, dict):
                    author_name = author.get('name') or author.get('display_name', '')
                else:
                    continue
                
                if author_name:
                    ref_authors[author_name] = ref_authors.get(author_name, 0) + 1
        
        # Collect citation authors
        for paper in citations:
            for author in paper.get('authors', []):
                if isinstance(author, str):
                    author_name = author
                elif isinstance(author, dict):
                    author_name = author.get('name') or author.get('display_name', '')
                else:
                    continue
                
                if author_name:
                    cite_authors[author_name] = cite_authors.get(author_name, 0) + 1
        
        # Find authors who appear in both (potential collaborators or influential figures)
        related_authors = []
        for author in ref_authors:
            if author in cite_authors:
                related_authors.append({
                    "name": author,
                    "reference_papers": ref_authors[author],
                    "citing_papers": cite_authors[author],
                    "influence": ref_authors[author] + cite_authors[author]
                })
        
        # Sort by influence and return top 5
        related_authors.sort(key=lambda x: x['influence'], reverse=True)
        return related_authors[:5]
    
    def _create_simple_timeline(self, references: List[Dict], citations: List[Dict], 
                              paper_metadata: Optional[Dict] = None) -> Dict:
        """Create a simple timeline showing research evolution"""
        all_papers = references + citations
        
        # Add the main paper to timeline if we have its metadata
        if paper_metadata:
            all_papers.append(paper_metadata)
        
        # Group by year
        timeline = {}
        for paper in all_papers:
            year = paper.get('publication_year') or paper.get('year')
            if year:
                if year not in timeline:
                    timeline[year] = []
                
                title = paper.get('title', '')
                timeline[year].append({
                    'title': title[:50] + ('...' if len(title) > 50 else ''),
                    'authors': paper.get('authors', [])[:2],  # First 2 authors
                    'citations': paper.get('cited_by_count', 0),
                    'type': 'main' if paper == paper_metadata else ('reference' if paper in references else 'citation')
                })
        
        # Sort timeline by year
        sorted_timeline = dict(sorted(timeline.items()))
        
        # Add timeline insights
        years = list(sorted_timeline.keys())
        timeline_insights = []
        
        if len(years) > 1:
            span = max(years) - min(years)
            timeline_insights.append(f"📅 Research spans {span} years ({min(years)} - {max(years)})")
            
            # Find the most productive years
            year_counts = [(year, len(papers)) for year, papers in sorted_timeline.items()]
            year_counts.sort(key=lambda x: x[1], reverse=True)
            
            if year_counts:
                peak_year, peak_count = year_counts[0]
                timeline_insights.append(f"📈 Peak research year: {peak_year} ({peak_count} related papers)")
        
        return {
            "timeline": sorted_timeline,
            "insights": timeline_insights,
            "total_years": len(years),
            "year_range": f"{min(years)} - {max(years)}" if years else "Unknown"
        }
    
    def _analyze_connections(self, references: List[Dict], citations: List[Dict], 
                           paper_metadata: Optional[Dict] = None) -> Dict:
        """Simple analysis of paper connections that anyone can understand"""
        
        ref_count = len(references)
        cite_count = len(citations)
        
        # Calculate simple metrics
        paper_year = None
        if paper_metadata:
            paper_year = paper_metadata.get('publication_year') or paper_metadata.get('year')
        
        # Generate insights that are easy to understand
        insights = []
        
        # Research foundation analysis
        if ref_count > 30:
            insights.append(f"📚 Built on extensive research ({ref_count} references) - shows thorough literature review")
        elif ref_count > 15:
            insights.append(f"📖 Well-researched paper ({ref_count} references) - good foundation")
        elif ref_count < 10:
            insights.append(f"🆕 Few references ({ref_count}) - might be exploring new territory or survey paper")
        
        # Impact analysis
        if cite_count > 500:
            insights.append(f"🏆 Extremely influential paper ({cite_count} citations) - landmark work!")
        elif cite_count > 100:
            insights.append(f"🔥 Highly influential paper ({cite_count} citations) - significant impact")
        elif cite_count > 20:
            insights.append(f"📈 Good impact ({cite_count} citations) - recognized by peers")
        elif cite_count < 5:
            insights.append(f"🌱 Limited citations ({cite_count}) - either very new or niche topic")
        
        # Age vs impact analysis
        if paper_year and cite_count > 0:
            current_year = datetime.now().year
            age = current_year - paper_year
            
            if age < 2 and cite_count > 10:
                insights.append(f"⚡ Fast impact - {cite_count} citations in {age} years")
            elif age > 10 and cite_count > 100:
                insights.append(f"🏛️ Enduring influence - still being cited after {age} years")
        
        # Find the most cited paper it references
        if references:
            most_cited_ref = max(references, key=lambda x: x.get('cited_by_count', 0))
            ref_title = most_cited_ref.get('title', '')[:40]
            ref_citations = most_cited_ref.get('cited_by_count', 0)
            if ref_citations > 100:
                insights.append(f"🏛️ Built upon highly influential work: '{ref_title}...' ({ref_citations} cites)")
        
        return {
            "reference_count": ref_count,
            "citation_count": cite_count,
            "insights": insights,
            "influence_score": min(100, cite_count * 0.5),  # Simple 0-100 influence score
            "foundation_strength": min(100, ref_count * 2),  # How well-researched (0-100)
            "research_maturity": "high" if ref_count > 20 else "medium" if ref_count > 10 else "exploratory",
            "impact_level": "breakthrough" if cite_count > 500 else "high" if cite_count > 100 else "moderate" if cite_count > 20 else "emerging"
        }
    
    def _find_interesting_patterns(self, references: List[Dict], citations: List[Dict]) -> Dict:
        """Find interesting patterns in the paper relationships"""
        patterns = []
        
        # Author patterns
        if references and citations:
            ref_authors = set()
            for paper in references:
                for author in paper.get('authors', []):
                    if isinstance(author, str):
                        ref_authors.add(author)
                    elif isinstance(author, dict):
                        ref_authors.add(author.get('name') or author.get('display_name', ''))
            
            cite_authors = set()
            for paper in citations:
                for author in paper.get('authors', []):
                    if isinstance(author, str):
                        cite_authors.add(author)
                    elif isinstance(author, dict):
                        cite_authors.add(author.get('name') or author.get('display_name', ''))
            
            overlap = ref_authors.intersection(cite_authors)
            if len(overlap) > 0:
                patterns.append(f"🤝 {len(overlap)} authors appear in both references and citations - potential collaborators")
        
        # Venue patterns
        ref_venues = [paper.get('venue', '') for paper in references if paper.get('venue')]
        cite_venues = [paper.get('venue', '') for paper in citations if paper.get('venue')]
        
        if ref_venues and cite_venues:
            common_venues = set(ref_venues).intersection(set(cite_venues))
            if len(common_venues) > 0:
                patterns.append(f"📍 Research appears in {len(common_venues)} common venues - coherent research area")
        
        # Temporal patterns
        ref_years = [paper.get('publication_year') for paper in references if paper.get('publication_year')]
        cite_years = [paper.get('publication_year') for paper in citations if paper.get('publication_year')]
        
        if ref_years and cite_years:
            ref_span = max(ref_years) - min(ref_years) if len(ref_years) > 1 else 0
            cite_span = max(cite_years) - min(cite_years) if len(cite_years) > 1 else 0
            
            if ref_span > 10:
                patterns.append(f"📅 References span {ref_span} years - builds on long research tradition")
            
            if cite_span > 5:
                patterns.append(f"⏰ Citations span {cite_span} years - lasting influence")
        
        return {
            "patterns": patterns,
            "author_overlap": len(ref_authors.intersection(cite_authors)) if 'ref_authors' in locals() and 'cite_authors' in locals() else 0,
            "venue_overlap": len(set(ref_venues).intersection(set(cite_venues))) if ref_venues and cite_venues else 0,
            "temporal_span": {
                "references": ref_span if 'ref_span' in locals() else 0,
                "citations": cite_span if 'cite_span' in locals() else 0
            }
        }
    
    def _find_cross_connections(self, all_connections: Dict[str, Dict]) -> Dict:
        """Find connections between multiple papers being explored"""
        cross_connections = []
        paper_ids = list(all_connections.keys())
        
        for i, paper_id_1 in enumerate(paper_ids):
            for j, paper_id_2 in enumerate(paper_ids[i+1:], i+1):
                connections_1 = all_connections[paper_id_1]
                connections_2 = all_connections[paper_id_2]
                
                if not (connections_1.get('success') and connections_2.get('success')):
                    continue
                
                # Check if paper 1 references paper 2 or vice versa
                refs_1 = [p['id'] for p in connections_1['connections']['foundation_papers']]
                cites_1 = [p['id'] for p in connections_1['connections']['building_papers']]
                refs_2 = [p['id'] for p in connections_2['connections']['foundation_papers']]
                cites_2 = [p['id'] for p in connections_2['connections']['building_papers']]
                
                if paper_id_2 in refs_1:
                    cross_connections.append({
                        "type": "direct_reference",
                        "from": paper_id_1,
                        "to": paper_id_2,
                        "description": "Paper 1 references Paper 2"
                    })
                elif paper_id_1 in refs_2:
                    cross_connections.append({
                        "type": "direct_reference", 
                        "from": paper_id_2,
                        "to": paper_id_1,
                        "description": "Paper 2 references Paper 1"
                    })
                
                # Check for common references
                common_refs = set(refs_1).intersection(set(refs_2))
                if len(common_refs) > 0:
                    cross_connections.append({
                        "type": "common_references",
                        "papers": [paper_id_1, paper_id_2],
                        "count": len(common_refs),
                        "description": f"Share {len(common_refs)} common references"
                    })
        
        return {
            "connections": cross_connections,
            "total_connections": len(cross_connections)
        }
    
    def _create_multi_paper_summary(self, family_trees: List[Dict]) -> Dict:
        """Create a summary when exploring multiple papers"""
        total_papers = len(family_trees)
        successful_trees = [tree for tree in family_trees if tree.get('success')]
        
        if not successful_trees:
            return {"papers": 0, "summary": "No successful connections found"}
        
        total_references = sum(len(tree['connections']['foundation_papers']) for tree in successful_trees)
        total_citations = sum(len(tree['connections']['building_papers']) for tree in successful_trees)
        
        return {
            "papers_analyzed": len(successful_trees),
            "total_references": total_references,
            "total_citations": total_citations,
            "summary": f"Analyzed {len(successful_trees)} papers with {total_references} foundation papers and {total_citations} building papers"
        }
    
    def _prepare_simple_viz_data(self, references: List[Dict], citations: List[Dict], 
                                paper_metadata: Optional[Dict] = None) -> Dict:
        """Prepare data for a simple, easy-to-understand visualization"""
        
        nodes = []
        links = []
        
        # Center node (the main paper)
        center_title = "Selected Paper"
        if paper_metadata:
            center_title = paper_metadata.get('title', 'Selected Paper')[:40] + '...'
        
        center_node = {
            "id": "center",
            "title": center_title,
            "type": "center",
            "size": 25,
            "color": "#ff6b6b",
            "year": paper_metadata.get('publication_year') if paper_metadata else None,
            "citations": paper_metadata.get('cited_by_count', 0) if paper_metadata else 0
        }
        nodes.append(center_node)
        
        # Reference nodes (what it built upon) - limit to top 8
        top_references = self._get_most_important(references, 8)
        for i, ref in enumerate(top_references):
            node = {
                "id": f"ref_{i}",
                "title": ref['title'],
                "type": "reference",
                "year": ref['year'],
                "citations": ref['citation_count'],
                "size": 12 + min(ref['citation_count'] / 100, 8),  # Size based on citations
                "color": "#4ecdc4",
                "influence": ref['influence_score']
            }
            nodes.append(node)
            
            # Link from reference to center
            links.append({
                "source": f"ref_{i}",
                "target": "center",
                "type": "influences",
                "strength": min(ref['citation_count'] / 1000, 1)  # Link strength based on citations
            })
        
        # Citation nodes (what built upon it) - limit to top 8
        top_citations = self._get_most_recent(citations, 8)
        for i, cite in enumerate(top_citations):
            node = {
                "id": f"cite_{i}",
                "title": cite['title'],
                "type": "citation",
                "year": cite['year'],
                "citations": cite['citation_count'],
                "size": 10 + min(cite['citation_count'] / 50, 6),
                "color": "#45b7d1",
                "influence": cite['influence_score']
            }
            nodes.append(node)
            
            # Link from center to citation
            links.append({
                "source": "center",
                "target": f"cite_{i}",
                "type": "influenced",
                "strength": 0.5  # Citations generally have lighter connections
            })
        
        return {
            "nodes": nodes,
            "links": links,
            "layout": "radial",  # Simple radial layout around center
            "stats": {
                "total_nodes": len(nodes),
                "reference_nodes": len(top_references),
                "citation_nodes": len(top_citations),
                "max_year": max([n['year'] for n in nodes if n['year']], default=None),
                "min_year": min([n['year'] for n in nodes if n['year']], default=None)
            },
            "legend": {
                "center": {"color": "#ff6b6b", "label": "Selected Paper", "description": "The paper you're exploring"},
                "references": {"color": "#4ecdc4", "label": "Foundation Papers", "description": "What this paper built upon"},
                "citations": {"color": "#45b7d1", "label": "Building Papers", "description": "What built upon this paper"}
            },
            "explanation": {
                "concept": "Paper Family Tree",
                "description": "This shows how research ideas flow - from foundation papers (left) through your selected paper (center) to newer papers that built upon it (right)",
                "how_to_read": "Larger circles = more influential papers. Connections show the flow of ideas over time."
            }
        }

    def _find_similar_papers(self, title, limit=5):
        """Find papers related to the given paper title"""
        try:
            self.logger.info(f"Finding papers similar to: {title}")
            
            # Try enhanced mode first
            if self.enhanced_mode:
                papers = self._find_papers_with_scholarly(title, limit)
                if papers:
                    return papers
                else:
                    self.logger.info("Scholarly search failed, falling back to simple method")
            
            # Fallback to simple method
            return self._find_papers_simple(title, limit)
            
        except Exception as e:
            self.logger.error(f"Error finding similar papers: {e}")
            return []

    def _find_papers_with_scholarly(self, title, limit=5):
        """Enhanced paper search using Google Scholar via scholarly package"""
        try:
            if not self.scholarly_ready:
                return []
            
            self.logger.info(f"Searching Google Scholar for: {title}")
            papers = []
            
            # Search for the main paper first (fix method name)
            search_query = scholarly.search_pubs(title)
            
            # Get first few results
            for i, publication in enumerate(search_query):
                if i >= limit:
                    break
                
                try:
                    # Fill in more details about this publication
                    filled_pub = scholarly.fill(publication)
                    
                    # Extract paper information
                    paper_info = {
                        'id': f"scholar_{i}",
                        'title': filled_pub.get('bib', {}).get('title', 'Unknown Title'),
                        'authors': filled_pub.get('bib', {}).get('author', []),
                        'year': filled_pub.get('bib', {}).get('pub_year', 'Unknown'),
                        'citations_count': filled_pub.get('num_citations', 0),
                        'source': 'google_scholar',
                        'relationship': 'scholar_search_result',
                        'abstract': filled_pub.get('bib', {}).get('abstract', ''),
                        'url': filled_pub.get('pub_url', '')
                    }
                    
                    # Add citation information if available
                    if filled_pub.get('citedby_url'):
                        paper_info['citedby_url'] = filled_pub.get('citedby_url')
                    
                    papers.append(paper_info)
                    
                    # Small delay to be respectful to Google Scholar
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing publication {i}: {e}")
                    continue
            
            self.logger.info(f"Found {len(papers)} papers via Google Scholar")
            return papers
            
        except Exception as e:
            self.logger.error(f"Scholarly search failed: {e}")
            return []

    def _find_papers_simple(self, title, limit=5):
        """Simple paper search using existing citation extractor"""
        try:
            related_papers = []
            
            # Use citation extractor to find papers
            search_results = self.citation_extractor.search_papers_by_title(title, limit=limit*2)
            
            for result in search_results:
                paper_info = {
                    'id': result.get('id', f'paper_{len(related_papers)}'),
                    'title': result.get('title', 'Unknown Title'),
                    'authors': result.get('authors', []),
                    'year': result.get('year', 'Unknown'),
                    'citations_count': result.get('cited_by_count', 0),
                    'source': 'citation_extractor',
                    'relationship': 'similar_research'
                }
                related_papers.append(paper_info)
            
            return related_papers[:limit]
            
        except Exception as e:
            self.logger.error(f"Error in simple paper search: {e}")
            return []

    def _create_network_graph(self, center_paper, references, citations):
        """Create a network analysis using networkx (if available)"""
        try:
            if not self.enhanced_mode:
                return None
            
            self.logger.info("Creating enhanced network graph with networkx")
            
            # Create directed graph (papers cite other papers)
            G = nx.DiGraph()
            
            # Add center paper (defensively handle None or missing keys)
            if not center_paper:
                center_paper = {'id': 'center', 'title': 'Unknown', 'year': None, 'cited_by_count': 0}

            center_id = center_paper.get('id') or f"center_{int(time.time())}"
            G.add_node(center_id,
                      title=center_paper.get('title') or 'Unknown',
                      year=center_paper.get('publication_year') or center_paper.get('year'),
                      citations=center_paper.get('cited_by_count', 0) or 0,
                      type='center')
            
            # Add reference papers (papers this one cites)
            # Add reference papers (defensive: skip None entries)
            for ref in (references or [])[:10]:  # Limit for simplicity
                if not ref or not isinstance(ref, dict):
                    continue
                ref_id = ref.get('id') or f"ref_{len(list(G.nodes))}"
                G.add_node(ref_id,
                          title=(ref.get('title') or 'Unknown')[:200],
                          year=ref.get('publication_year') or ref.get('year'),
                          citations=ref.get('cited_by_count', 0) or 0,
                          type='reference')
                # Edge from center to reference (center cites reference)
                G.add_edge(center_id, ref_id, relationship='cites')
            
            # Add citation papers (papers that cite this one)
            # Add citation papers (defensive: skip None entries)
            for cit in (citations or [])[:10]:  # Limit for simplicity
                if not cit or not isinstance(cit, dict):
                    continue
                cit_id = cit.get('id') or f"cit_{len(list(G.nodes))}"
                G.add_node(cit_id,
                          title=(cit.get('title') or 'Unknown')[:200],
                          year=cit.get('publication_year') or cit.get('year'),
                          citations=cit.get('cited_by_count', 0) or 0,
                          type='citation')
                # Edge from citation to center (citation cites center)
                G.add_edge(cit_id, center_id, relationship='cites')
            
            # Simple network analysis
            network_stats = {
                'total_nodes': G.number_of_nodes(),
                'total_edges': G.number_of_edges(),
                'center_degree': G.degree(center_id) if center_id in G.nodes else 0,
                'center_in_degree': G.in_degree(center_id) if center_id in G.nodes else 0,  # How many cite it
                'center_out_degree': G.out_degree(center_id) if center_id in G.nodes else 0,  # How many it cites
            }
            
            # Find most connected papers (excluding center)
            degree_centrality = nx.degree_centrality(G)
            most_connected = sorted(
                [(node, centrality) for node, centrality in degree_centrality.items() 
                 if node != center_id],
                key=lambda x: x[1], reverse=True
            )[:3]

            most_connected_papers = []
            for node, centrality in most_connected:
                node_data = G.nodes.get(node, {})
                most_connected_papers.append({
                    'id': node,
                    'title': node_data.get('title', 'Unknown') if isinstance(node_data, dict) else 'Unknown',
                    'centrality_score': centrality
                })

            network_stats['most_connected_papers'] = most_connected_papers
            
            self.logger.info(f"Network analysis complete: {network_stats}")
            return network_stats
            
        except Exception as e:
            self.logger.error(f"Network analysis failed: {e}")
            return None

    def get_enhanced_features_demo(self):
        """Simple demo of enhanced features for hiring manager explanation"""
        demo_info = {
            "enhanced_mode_enabled": self.enhanced_mode,
            "features": {
                "google_scholar_integration": {
                    "description": "Search Google Scholar for related papers",
                    "enabled": self.enhanced_mode and hasattr(self, 'scholarly_ready'),
                    "benefit": "Access to Google's vast academic database"
                },
                "network_analysis": {
                    "description": "Analyze paper connection patterns using graph theory",
                    "enabled": self.enhanced_mode,
                    "benefit": "Find influential papers and research clusters"
                },
                "fallback_system": {
                    "description": "Always works even if enhanced features fail", 
                    "enabled": True,
                    "benefit": "Reliable service with OpenAlex API"
                }
            },
            "explanation": {
                "simple_version": "We can explore how research papers are connected - what they built upon and what built upon them",
                "enhanced_version": "Plus we can search Google Scholar and use network analysis to find patterns and influential papers",
                "hiring_manager_pitch": "This shows both technical depth (scholarly/networkx integration) and practical engineering (fallback systems)"
            }
        }
        
        return demo_info