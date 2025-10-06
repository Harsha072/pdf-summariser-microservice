#!/usr/bin/env python3
"""
Test script for citation extraction functionality
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'flask-api', 'app'))

from main import extract_academic_citations, format_citations

def test_citation_extraction():
    """Test the citation extraction functions"""
    
    # Sample academic text with citations
    sample_text = """
    According to Smith, J. (2023), machine learning has transformed data analysis.
    Recent work by Johnson, A. & Brown, B. (2022) shows significant improvements.
    The methodology follows Davis, C. (2021). "Advanced Statistical Methods". 
    Journal of Data Science, 15(3), pp. 45-67.
    
    Another important reference is available at https://example.com/research
    with DOI: 10.1234/example.2023.01
    
    Multiple authors like Anderson, K., Wilson, M. and Taylor, R. (2020) 
    have contributed to this field.
    """
    
    # Mock sources for testing
    mock_sources = [
        {
            'text': sample_text,
            'page': 1,
            'section_heading': 'References'
        }
    ]
    
    print("Testing Citation Extraction...")
    print("=" * 50)
    
    try:
        # Test citation extraction
        citations = extract_academic_citations(sample_text, mock_sources)
        
        print(f"Found {len(citations)} citations:")
        for i, citation in enumerate(citations, 1):
            print(f"\n{i}. {citation.get('format_detected', 'Unknown')} Citation:")
            print(f"   Authors: {citation.get('authors', 'N/A')}")
            print(f"   Year: {citation.get('year', 'N/A')}")
            print(f"   Title: {citation.get('title', 'N/A')}")
            print(f"   Raw: {citation.get('raw_text', 'N/A')[:50]}...")
        
        # Test citation formatting
        if citations:
            print("\n" + "=" * 50)
            print("Testing Citation Formatting...")
            
            # Test APA format
            apa_formatted = format_citations(citations[:2], 'apa')
            print(f"\nAPA Format ({len(apa_formatted)} citations):")
            for citation in apa_formatted:
                print(f"  • {citation}")
            
            # Test BibTeX format
            bibtex_formatted = format_citations(citations[:1], 'bibtex')
            print(f"\nBibTeX Format ({len(bibtex_formatted)} citations):")
            for citation in bibtex_formatted:
                print(f"  {citation}")
        
        print("\n" + "=" * 50)
        print("✅ Citation extraction test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_citation_extraction()
    sys.exit(0 if success else 1)