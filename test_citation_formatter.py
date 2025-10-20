#!/usr/bin/env python3
"""
Simple test script to verify the OpenAlex ID formatting function
"""

import sys
import os

# Add the flask-api directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'flask-api'))

from app.citation_data_extractor import CitationDataExtractor

def test_format_openalex_id():
    """Test the _format_openalex_id function with various inputs"""
    
    extractor = CitationDataExtractor()
    
    test_cases = [
        # (input, expected_output)
        ('2312045123', 'https://openalex.org/W2312045123'),
        ('W2312045123', 'https://openalex.org/W2312045123'),
        ('https://openalex.org/W2312045123', 'https://openalex.org/W2312045123'),
        ('123456789', 'https://openalex.org/W123456789'),
        ('', ''),
        ('   2312045123   ', 'https://openalex.org/W2312045123'),  # with spaces
    ]
    
    print("Testing _format_openalex_id function:")
    print("=" * 60)
    
    for i, (input_id, expected) in enumerate(test_cases, 1):
        result = extractor._format_openalex_id(input_id)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        print(f"Test {i}: {status}")
        print(f"  Input:    '{input_id}'")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
        print()

if __name__ == "__main__":
    test_format_openalex_id()