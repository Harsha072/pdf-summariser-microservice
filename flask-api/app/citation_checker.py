"""
Citation Checker Module
Simple and effective citation validation for academic papers
"""

import logging
import re
import os
from typing import List, Dict, Any
import pdfplumber

logger = logging.getLogger(__name__)


class CitationChecker:
    """
    Simple citation checker for academic papers
    Validates citation completeness and formatting
    """
    
    def __init__(self):
        self.logger = logger
        self.logger.info("CitationChecker initialized")
    
    def check_paper_citations(self, pdf_file_path: str) -> Dict[str, Any]:
        """
        Check citations in uploaded paper - simple and effective approach
        
        Args:
            pdf_file_path: Path to uploaded PDF paper
            
        Returns:
            Citation analysis with issues and recommendations
        """
        try:
            self.logger.info(f"Starting citation check for: {pdf_file_path}")
            
            # Step 1: Extract text from PDF
            text = self._extract_pdf_text(pdf_file_path)
            if not text:
                return {"success": False, "error": "Could not extract text from PDF"}
            
            self.logger.info(f"Extracted {len(text)} characters from PDF")
            
            # Step 2: Find in-text citations
            in_text_citations = self._find_citations_in_text(text)
            self.logger.info(f"Found {len(in_text_citations)} in-text citations")
            
            # Step 3: Find references section
            references = self._find_references_section(text)
            self.logger.info(f"Found {len(references)} reference entries")
            
            # Step 4: Check for citation issues
            issues = self._check_citation_issues(in_text_citations, references, text)
            
            # Step 5: Generate recommendations
            recommendations = self._generate_recommendations(issues, in_text_citations, references)
            
            # Step 6: Calculate score
            score = self._calculate_citation_score(issues, in_text_citations, references)
            
            # Step 7: Analyze citation formats
            citation_analysis = self._analyze_citation_formats(in_text_citations)
            
            result = {
                "success": True,
                "analysis": {
                    "overall_score": score,
                    "in_text_citations_found": len(in_text_citations),
                    "references_found": len(references),
                    "issues_detected": len(issues),
                    "citation_format": citation_analysis["detected_format"],
                    "format_consistency": citation_analysis["is_consistent"]
                },
                "detailed_results": {
                    "issues": issues,
                    "recommendations": recommendations,
                    "citation_format_analysis": citation_analysis,
                    "sample_citations": in_text_citations[:5],
                    "sample_references": [ref[:100] + "..." for ref in references[:3]]
                },
                "quality_indicators": {
                    "has_references_section": len(references) > 0,
                    "sufficient_citations": len(in_text_citations) >= 5,
                    "citation_reference_balance": abs(len(in_text_citations) - len(references)) <= 5,
                    "format_consistency": citation_analysis["is_consistent"]
                }
            }
            
            self.logger.info(f"Citation check complete. Score: {score}/100, Issues: {len(issues)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Citation checking failed: {e}")
            return {"success": False, "error": f"Citation analysis failed: {str(e)}"}
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            return text
            
        except Exception as e:
            self.logger.error(f"PDF text extraction failed: {e}")
            return ""
    
    def _find_citations_in_text(self, text: str) -> List[str]:
        """Find citations using regex patterns - covers most common formats"""
        citations = []
        
        # Pattern 1: (Author, Year) or (Author et al., Year)
        pattern1 = r'\([A-Za-z][A-Za-z\s&.,]+(?:\s+et\s+al\.)?[,\s]*\d{4}[a-z]?\)'
        matches1 = re.findall(pattern1, text, re.IGNORECASE)
        citations.extend(matches1)
        
        # Pattern 2: [Number] format
        pattern2 = r'\[\d+\]'
        matches2 = re.findall(pattern2, text)
        citations.extend(matches2)
        
        # Pattern 3: Author (Year) format
        pattern3 = r'[A-Z][a-z]+(?:\s+et\s+al\.)?(?:\s+\([0-9]{4}[a-z]?\))'
        matches3 = re.findall(pattern3, text)
        citations.extend(matches3)
        
        # Remove duplicates and filter out false positives
        unique_citations = []
        seen = set()
        
        for citation in citations:
            citation_clean = citation.strip()
            if (len(citation_clean) > 3 and 
                citation_clean not in seen and
                not citation_clean.startswith('(')):  # Avoid fragments
                seen.add(citation_clean)
                unique_citations.append(citation_clean)
        
        return unique_citations
    
    def _find_references_section(self, text: str) -> List[str]:
        """Find and extract references section"""
        try:
            # Find where references section starts
            ref_patterns = [
                r'\breferences\s*\n',
                r'\bbibliography\s*\n',
                r'\bworks\s+cited\s*\n',
                r'\bliterature\s+cited\s*\n'
            ]
            
            ref_start = None
            for pattern in ref_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    ref_start = match.end()
                    break
            
            if ref_start is None:
                # Try to find numbered references like [1] Author...
                numbered_ref_match = re.search(r'\[\d+\]\s+[A-Z]', text)
                if numbered_ref_match:
                    ref_start = numbered_ref_match.start()
            
            if ref_start is None:
                return []
            
            # Extract references section
            ref_text = text[ref_start:]
            
            # Split into individual references
            references = []
            
            # Method 1: Split by numbered references [1], [2], etc.
            if re.search(r'\[\d+\]', ref_text):
                ref_entries = re.split(r'\n\s*(?=\[\d+\])', ref_text)
                for entry in ref_entries:
                    if len(entry.strip()) > 30 and re.search(r'\d{4}', entry):
                        references.append(entry.strip())
            
            # Method 2: Split by author names (lines starting with capital letter)
            else:
                lines = ref_text.split('\n')
                current_ref = ""
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if line starts a new reference
                    if (re.match(r'^[A-Z][a-z]+,?\s+[A-Z]', line) and 
                        len(current_ref) > 20):
                        if re.search(r'\d{4}', current_ref):
                            references.append(current_ref)
                        current_ref = line
                    else:
                        current_ref += " " + line
                
                # Add the last reference
                if len(current_ref) > 20 and re.search(r'\d{4}', current_ref):
                    references.append(current_ref)
            
            # Clean up and limit references
            cleaned_refs = []
            for ref in references[:50]:  # Limit to 50 references
                ref = ref.strip()
                if len(ref) > 20 and re.search(r'\d{4}', ref):
                    cleaned_refs.append(ref)
            
            return cleaned_refs
            
        except Exception as e:
            self.logger.error(f"Reference extraction failed: {e}")
            return []
    
    def _check_citation_issues(self, citations: List[str], references: List[str], text: str) -> List[Dict[str, str]]:
        """Check for common citation issues"""
        issues = []
        
        # Issue 1: No references section found
        if len(references) == 0:
            issues.append({
                "type": "missing_references",
                "severity": "high",
                "description": "No references section found",
                "suggestion": "Add a References section at the end of your paper"
            })
        
        # Issue 2: Very few citations for a research paper
        if len(citations) < 3:
            issues.append({
                "type": "insufficient_citations",
                "severity": "medium",
                "description": f"Only {len(citations)} citations found - may be too few for academic work",
                "suggestion": "Consider adding more citations to support your claims"
            })
        
        # Issue 3: Significant mismatch between citations and references
        if len(references) > 0 and abs(len(citations) - len(references)) > 10:
            issues.append({
                "type": "citation_reference_mismatch",
                "severity": "medium", 
                "description": f"Found {len(citations)} citations but {len(references)} references",
                "suggestion": "Ensure all in-text citations have corresponding references"
            })
        
        # Issue 4: Mixed citation formats
        numbered_citations = [c for c in citations if re.match(r'\[\d+\]', c)]
        author_year_citations = [c for c in citations if '(' in c and re.search(r'\d{4}', c)]
        
        if len(numbered_citations) > 0 and len(author_year_citations) > 0:
            issues.append({
                "type": "mixed_citation_formats",
                "severity": "low",
                "description": "Mixed citation formats detected (both numbered and author-year)",
                "suggestion": "Use consistent citation format throughout the paper"
            })
        
        # Issue 5: Very long paper with few citations
        word_count = len(text.split())
        if word_count > 3000 and len(citations) < 10:
            issues.append({
                "type": "low_citation_density",
                "severity": "medium",
                "description": f"Long paper ({word_count} words) with relatively few citations",
                "suggestion": "Consider adding more citations to adequately support your arguments"
            })
        
        return issues
    
    def _analyze_citation_formats(self, citations: List[str]) -> Dict[str, Any]:
        """Analyze citation format consistency"""
        if not citations:
            return {"detected_format": "none", "is_consistent": False, "format_breakdown": {}}
        
        format_counts = {
            "numbered": 0,
            "author_year": 0,
            "other": 0
        }
        
        for citation in citations:
            if re.match(r'\[\d+\]', citation):
                format_counts["numbered"] += 1
            elif '(' in citation and re.search(r'\d{4}', citation):
                format_counts["author_year"] += 1
            else:
                format_counts["other"] += 1
        
        # Determine dominant format
        dominant_format = max(format_counts, key=format_counts.get)
        total_citations = len(citations)
        
        # Check consistency (80% threshold)
        is_consistent = (format_counts[dominant_format] / total_citations) >= 0.8
        
        return {
            "detected_format": dominant_format,
            "is_consistent": is_consistent,
            "format_breakdown": format_counts,
            "consistency_percentage": (format_counts[dominant_format] / total_citations) * 100
        }
    
    def _generate_recommendations(self, issues: List[Dict], citations: List[str], references: List[str]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Add recommendations based on issues
        for issue in issues:
            recommendations.append(f"⚠️ {issue['suggestion']}")
        
        # General recommendations
        if len(issues) == 0:
            recommendations.append("✅ No major citation issues detected - good work!")
        
        # Format-specific recommendations
        if len(citations) > 0 and len(references) > 0:
            recommendations.append("🔍 Double-check that all in-text citations have corresponding reference entries")
        
        # Style recommendations
        if any("mixed" in issue["type"] for issue in issues):
            recommendations.append("📝 Choose either numbered citations [1] or author-year citations (Smith, 2023) and use consistently")
        
        # Quality recommendations
        if len(references) > 0:
            recommendations.append("🔗 Include DOIs in references where available")
            recommendations.append("📚 Ensure reference entries are complete (author, title, year, venue)")
        
        return recommendations[:6]  # Limit to most important recommendations
    
    def _calculate_citation_score(self, issues: List[Dict], citations: List[str], references: List[str]) -> int:
        """Calculate overall citation quality score (0-100)"""
        score = 100
        
        # Deduct points for issues
        for issue in issues:
            if issue["severity"] == "high":
                score -= 25
            elif issue["severity"] == "medium":
                score -= 15
            elif issue["severity"] == "low":
                score -= 5
        
        # Bonus points for good practices
        if len(citations) >= 10:
            score += 5  # Good number of citations
        
        if len(references) > 0:
            score += 10  # Has references section
        
        if abs(len(citations) - len(references)) <= 3:
            score += 5  # Good balance
        
        return max(0, min(100, score))