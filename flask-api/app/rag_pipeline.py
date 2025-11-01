"""
RAG Pipeline Module for Personalized Paper Recommendations
Handles context generation, LLM integration, and enhanced paper insights
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RAGPipelineManager:
    """Enhanced RAG pipeline for personalized academic paper recommendations"""
    
    def __init__(self, openai_client, vector_db):
        """
        Initialize RAG Pipeline Manager
        
        Args:
            openai_client: OpenAI client instance for LLM calls
            vector_db: VectorDatabase instance for retrieval
        """
        self.openai_client = openai_client
        self.vector_db = vector_db
        self.logger = logger
        
        # Configuration
        self.max_context_papers = 8  # Limit context size for LLM
        self.max_context_tokens = 4000  # Approximate token limit for context
        
        logger.info("RAG Pipeline Manager initialized successfully")
    
    def get_rag_recommendations(self, user_query: str, user_context: Optional[Dict[str, Any]] = None, 
                              max_papers: int = 5) -> Dict[str, Any]:
        """
        Generate RAG-powered personalized paper recommendations
        
        Args:
            user_query: User's research question
            user_context: User's research profile and preferences
            max_papers: Maximum number of papers to recommend
            
        Returns:
            Dictionary with RAG recommendations and insights
        """
        try:
            logger.info(f"Starting RAG recommendation for query: '{user_query[:50]}...'")
            
            # Step 1: Retrieve relevant papers from vector database
            retrieved_papers = self.vector_db.search(
                query=user_query, 
                k=max_papers * 3,  # Get more papers for better context
                hybrid_weight=0.7,  # Favor semantic over keyword search
                min_similarity=0.1
            )
            
            if not retrieved_papers:
                return {
                    "success": False, 
                    "error": "No relevant papers found in database",
                    "recommendations": []
                }
            
            logger.info(f"Retrieved {len(retrieved_papers)} papers from vector database")
            
            # Step 2: Create rich context from retrieved papers
            context = self._create_enhanced_context(retrieved_papers[:self.max_context_papers])
            
            # Step 3: Generate personalized insights using RAG
            rag_response = self._generate_rag_insights(user_query, context, user_context)
            
            # Step 4: Score and enhance papers with RAG insights
            enhanced_papers = self._enhance_papers_with_insights(
                retrieved_papers[:max_papers], 
                rag_response
            )
            
            # Step 5: Generate research recommendations
            research_recommendations = self._generate_research_recommendations(
                user_query, 
                enhanced_papers, 
                rag_response
            )
            
            result = {
                "success": True,
                "recommendations": enhanced_papers,
                "rag_insights": rag_response,
                "research_recommendations": research_recommendations,
                "retrieval_stats": {
                    "papers_retrieved": len(retrieved_papers),
                    "papers_recommended": len(enhanced_papers),
                    "context_papers": len(retrieved_papers[:self.max_context_papers])
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"RAG pipeline completed successfully with {len(enhanced_papers)} recommendations")
            return result
            
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "recommendations": []
            }
    
    def _create_enhanced_context(self, papers: List[Dict[str, Any]]) -> str:
        """
        Create rich context string from retrieved papers for LLM processing
        
        Args:
            papers: List of retrieved papers
            
        Returns:
            Formatted context string for LLM
        """
        try:
            context_parts = ["RETRIEVED ACADEMIC PAPERS CONTEXT:"]
            
            for i, paper in enumerate(papers, 1):
                # Extract key information
                title = paper.get('title', 'Unknown Title')
                authors = paper.get('authors', [])
                author_str = ', '.join(authors[:3]) + (' et al.' if len(authors) > 3 else '')
                summary = paper.get('summary', 'No summary available')
                citations = paper.get('citation_count', 0)
                year = paper.get('published_year', 'Unknown')
                source = paper.get('source', 'Unknown')
                
                # Truncate summary to manage token usage
                truncated_summary = summary[:300] + "..." if len(summary) > 300 else summary
                
                # Include similarity scores if available
                semantic_score = paper.get('semantic_score', 0)
                final_score = paper.get('final_score', 0)
                
                paper_context = f"""
Paper {i}:
- Title: {title}
- Authors: {author_str}
- Year: {year}
- Citations: {citations}
- Source: {source}
- Relevance Score: {final_score:.3f} (Semantic: {semantic_score:.3f})
- Summary: {truncated_summary}
"""
                context_parts.append(paper_context)
                
                # Limit context size to prevent token overflow
                if len('\n'.join(context_parts)) > self.max_context_tokens:
                    logger.debug(f"Context truncated at {i} papers to prevent token overflow")
                    break
            
            full_context = '\n'.join(context_parts)
            logger.debug(f"Created context with {len(papers)} papers (~{len(full_context)} characters)")
            
            return full_context
            
        except Exception as e:
            logger.error(f"Failed to create context: {e}")
            return "Context creation failed - using fallback mode"
    
    def _generate_rag_insights(self, query: str, context: str, 
                              user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate RAG insights using OpenAI with retrieved context
        
        Args:
            query: User's research query
            context: Retrieved papers context
            user_context: User's research profile
            
        Returns:
            Dictionary with RAG insights and analysis
        """
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available, using fallback insights")
                return self._generate_fallback_insights(query, context)
            
            # Build user context string
            user_context_str = self._format_user_context(user_context) if user_context else ""
            
            # Create comprehensive RAG prompt
            prompt = self._build_rag_prompt(query, context, user_context_str)
            
            # Generate insights using OpenAI
            response = self.openai_client.invoke(prompt)
            
            # Extract content from response
            if hasattr(response, 'content'):
                content = str(response.content).strip()
            else:
                content = str(response).strip()
            
            # Parse JSON response
            try:
                insights = json.loads(content)
                logger.info("Successfully generated RAG insights using OpenAI")
                return insights
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse OpenAI JSON response: {e}")
                return self._generate_fallback_insights(query, context)
            
        except Exception as e:
            logger.error(f"RAG insights generation failed: {e}")
            return self._generate_fallback_insights(query, context)
    
    def _build_rag_prompt(self, query: str, context: str, user_context_str: str) -> str:
        """
        Build comprehensive RAG prompt for OpenAI
        
        Args:
            query: User's research query
            context: Retrieved papers context
            user_context_str: Formatted user context
            
        Returns:
            Complete prompt string
        """
        prompt = f"""You are an expert academic research assistant with access to a comprehensive database of research papers. 
Your task is to provide personalized, actionable recommendations that will save researchers significant time.

USER'S RESEARCH QUERY: "{query}"

{user_context_str}

{context}

Based on the retrieved papers above, provide a comprehensive analysis in this EXACT JSON format:

{{
    "query_analysis": {{
        "main_research_area": "Primary field/domain of the query",
        "research_intent": "What the user is trying to accomplish",
        "complexity_level": "beginner|intermediate|advanced",
        "key_concepts": ["concept1", "concept2", "concept3"]
    }},
    "paper_recommendations": [
        {{
            "paper_number": 1,
            "relevance_score": 95,
            "why_relevant": "Detailed explanation of why this paper is essential for the user's research",
            "key_insights": "Specific insights the user will gain from this paper",
            "reading_priority": "High",
            "methodology_focus": "What research methods or approaches this paper offers",
            "practical_applications": "How this research can be applied to the user's work"
        }}
    ],
    "research_synthesis": {{
        "key_themes": ["theme1", "theme2", "theme3"],
        "consensus_findings": "What the papers agree on",
        "conflicting_viewpoints": "Areas where papers disagree or show different approaches",
        "evolution_of_field": "How this research area has evolved based on paper dates"
    }},
    "research_gaps_and_opportunities": {{
        "identified_gaps": ["gap1", "gap2"],
        "emerging_trends": ["trend1", "trend2"],
        "underexplored_areas": ["area1", "area2"],
        "future_research_directions": ["direction1", "direction2"]
    }},
    "actionable_next_steps": {{
        "immediate_actions": ["Read paper X for methodology", "Review paper Y for recent findings"],
        "medium_term_goals": ["Explore specific subtopic", "Look into related research area"],
        "research_strategy": "Recommended approach for tackling this research question"
    }},
    "personalized_insights": "Specific recommendations based on the user's context and research level"
}}

IMPORTANT GUIDELINES:
- Provide specific, actionable insights that save the researcher time
- Focus on practical value and real research impact
- Be precise about why each paper is recommended
- Consider the research level and context provided
- Highlight methodological contributions and practical applications"""

        return prompt
    
    def _format_user_context(self, user_context: Dict[str, Any]) -> str:
        """Format user context for inclusion in prompt"""
        if not user_context:
            return ""
        
        context_parts = ["USER RESEARCH PROFILE:"]
        
        if user_context.get('level'):
            context_parts.append(f"- Research Level: {user_context['level']}")
        if user_context.get('field'):
            context_parts.append(f"- Field of Study: {user_context['field']}")
        if user_context.get('interests'):
            interests = ', '.join(user_context['interests'][:5])
            context_parts.append(f"- Research Interests: {interests}")
        if user_context.get('recent_queries'):
            recent = ', '.join(user_context['recent_queries'][:3])
            context_parts.append(f"- Recent Research Topics: {recent}")
        
        return '\n'.join(context_parts) + "\n"
    
    def _generate_fallback_insights(self, query: str, context: str) -> Dict[str, Any]:
        """Generate fallback insights when OpenAI is unavailable"""
        return {
            "query_analysis": {
                "main_research_area": "Academic Research",
                "research_intent": f"Research related to: {query}",
                "complexity_level": "intermediate",
                "key_concepts": query.split()[:5]
            },
            "paper_recommendations": [
                {
                    "paper_number": i + 1,
                    "relevance_score": 85 - (i * 5),
                    "why_relevant": "High semantic similarity to your research query",
                    "key_insights": "Provides relevant research methodology and findings",
                    "reading_priority": "High" if i < 2 else "Medium",
                    "methodology_focus": "Research methodology and approach",
                    "practical_applications": "Applicable to your research domain"
                }
                for i in range(min(3, len(context.split('Paper ')) - 1))
            ],
            "research_synthesis": {
                "key_themes": ["methodology", "findings", "applications"],
                "consensus_findings": "Multiple approaches to the research problem",
                "conflicting_viewpoints": "Different methodological approaches observed",
                "evolution_of_field": "Progressive development in research methods"
            },
            "research_gaps_and_opportunities": {
                "identified_gaps": ["Further research needed in specific areas"],
                "emerging_trends": ["Modern approaches to traditional problems"],
                "underexplored_areas": ["Interdisciplinary applications"],
                "future_research_directions": ["Integration with emerging technologies"]
            },
            "actionable_next_steps": {
                "immediate_actions": ["Review the top-ranked papers", "Identify key methodologies"],
                "medium_term_goals": ["Explore related research areas", "Consider interdisciplinary approaches"],
                "research_strategy": "Start with highly relevant papers and expand to related work"
            },
            "personalized_insights": "Papers have been ranked by relevance to your query using semantic similarity"
        }
    
    def _enhance_papers_with_insights(self, papers: List[Dict[str, Any]], 
                                    rag_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Enhance papers with RAG-generated insights and scoring
        
        Args:
            papers: List of papers to enhance
            rag_response: RAG insights from LLM
            
        Returns:
            List of enhanced papers with RAG insights
        """
        enhanced_papers = []
        recommendations = rag_response.get('paper_recommendations', [])
        
        for i, paper in enumerate(papers):
            enhanced_paper = paper.copy()
            
            # Add RAG insights if available
            if i < len(recommendations):
                rec = recommendations[i]
                enhanced_paper.update({
                    'rag_relevance_score': rec.get('relevance_score', 85),
                    'rag_why_relevant': rec.get('why_relevant', 'Semantically relevant to your query'),
                    'rag_key_insights': rec.get('key_insights', 'Provides valuable research insights'),
                    'rag_reading_priority': rec.get('reading_priority', 'Medium'),
                    'rag_methodology_focus': rec.get('methodology_focus', 'Research methodology'),
                    'rag_practical_applications': rec.get('practical_applications', 'Academic applications'),
                    'rag_enhanced': True
                })
            else:
                # Fallback RAG insights for papers beyond LLM recommendations
                enhanced_paper.update({
                    'rag_relevance_score': max(70, int(enhanced_paper.get('final_score', 0.7) * 100)),
                    'rag_why_relevant': 'Retrieved based on semantic and keyword similarity',
                    'rag_key_insights': 'Contributes to understanding of the research area',
                    'rag_reading_priority': 'Medium',
                    'rag_methodology_focus': 'Supporting research',
                    'rag_practical_applications': 'Relevant to research domain',
                    'rag_enhanced': False
                })
            
            enhanced_papers.append(enhanced_paper)
        
        return enhanced_papers
    
    def _generate_research_recommendations(self, query: str, enhanced_papers: List[Dict[str, Any]], 
                                        rag_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate high-level research recommendations based on RAG analysis
        
        Args:
            query: Original user query
            enhanced_papers: Papers with RAG insights
            rag_response: RAG insights from LLM
            
        Returns:
            Dictionary with research recommendations
        """
        try:
            recommendations = {
                "reading_order": [],
                "research_strategy": rag_response.get('actionable_next_steps', {}).get('research_strategy', 
                                   "Start with the highest-relevance papers and explore related work"),
                "key_insights_summary": [],
                "next_steps": rag_response.get('actionable_next_steps', {}).get('immediate_actions', []),
                "research_gaps": rag_response.get('research_gaps_and_opportunities', {}).get('identified_gaps', [])
            }
            
            # Generate reading order based on RAG priorities
            high_priority = [p for p in enhanced_papers if p.get('rag_reading_priority') == 'High']
            medium_priority = [p for p in enhanced_papers if p.get('rag_reading_priority') == 'Medium']
            
            recommendations["reading_order"] = [
                {"title": p.get('title', 'Unknown'), "priority": "High", "reason": p.get('rag_why_relevant', '')}
                for p in high_priority[:2]
            ] + [
                {"title": p.get('title', 'Unknown'), "priority": "Medium", "reason": p.get('rag_why_relevant', '')}
                for p in medium_priority[:3]
            ]
            
            # Extract key insights
            recommendations["key_insights_summary"] = [
                p.get('rag_key_insights', '') for p in enhanced_papers[:3] 
                if p.get('rag_key_insights')
            ]
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate research recommendations: {e}")
            return {
                "reading_order": [{"title": "Review retrieved papers", "priority": "High", "reason": "Most relevant to query"}],
                "research_strategy": "Start with the top-ranked papers",
                "key_insights_summary": ["Papers provide relevant insights for your research"],
                "next_steps": ["Review the recommended papers"],
                "research_gaps": ["Further analysis needed"]
            }
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get RAG pipeline statistics"""
        return {
            "vector_db_stats": self.vector_db.get_stats(),
            "openai_available": self.openai_client is not None,
            "max_context_papers": self.max_context_papers,
            "max_context_tokens": self.max_context_tokens
        }