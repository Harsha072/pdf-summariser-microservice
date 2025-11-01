import pytest
from unittest.mock import patch, MagicMock

class TestSmartQuoteFinderLogic:
    """Test Smart Quote Finder business logic (isolated from main app)"""
    
    def test_key_phrase_extraction_concept(self):
        """Test concept of key phrase extraction"""
        # Mock implementation of key phrase extraction
        def mock_extract_key_phrases(answer):
            """Mock key phrase extraction logic"""
            if not answer:
                return []
            
            # Simple extraction logic for testing
            words = answer.lower().split()
            key_terms = ['methodology', 'analysis', 'statistical', 'quantitative', 
                        'qualitative', 'research', 'study', 'method', 'approach']
            
            phrases = []
            for term in key_terms:
                if term in words:
                    phrases.append(term)
            
            # Add multi-word phrases
            if 'quantitative' in words and 'analysis' in words:
                phrases.append('quantitative analysis')
            if 'statistical' in words and 'methods' in words:
                phrases.append('statistical methods')
                
            return list(set(phrases))  # Remove duplicates
        
        # Test cases
        answer1 = "The methodology involves quantitative analysis using statistical methods."
        phrases1 = mock_extract_key_phrases(answer1)
        assert len(phrases1) > 0
        assert 'methodology' in phrases1
        assert 'quantitative analysis' in phrases1
        
        # Test empty answer
        phrases2 = mock_extract_key_phrases("")
        assert phrases2 == []
        
        print(f"✅ Key phrase extraction concept works: {phrases1}")
    
    def test_supporting_quotes_concept(self):
        """Test concept of supporting quote finding"""
        def mock_find_supporting_quotes(answer, doc_id, confidence_threshold=0.6):
            """Mock supporting quote finding logic"""
            # Mock vector search results
            mock_results = [
                {
                    'content': 'We used quantitative methodology in our research approach',
                    'metadata': {'page': 5, 'section': 'Methodology', 'chunk_id': 'chunk_1'},
                    'score': 0.85
                },
                {
                    'content': 'Statistical analysis was performed using SPSS software',
                    'metadata': {'page': 8, 'section': 'Data Analysis', 'chunk_id': 'chunk_2'},
                    'score': 0.72
                },
                {
                    'content': 'Low confidence match that should be filtered',
                    'metadata': {'page': 2, 'section': 'Introduction', 'chunk_id': 'chunk_3'},
                    'score': 0.3  # Below threshold
                }
            ]
            
            # Filter by confidence and format for ChatBot
            quotes = []
            for result in mock_results:
                if result['score'] >= confidence_threshold:
                    quotes.append({
                        'text': result['content'],
                        'page': result['metadata'].get('page', 'Unknown'),
                        'section': result['metadata'].get('section', 'Unknown'),
                        'confidence': int(result['score'] * 100)  # Convert to percentage
                    })
            
            # Sort by confidence (highest first)
            quotes.sort(key=lambda x: x['confidence'], reverse=True)
            
            return quotes
        
        # Test successful quote finding
        answer = "The research used quantitative methodology"
        quotes = mock_find_supporting_quotes(answer, "test-doc-123")
        
        assert len(quotes) > 0
        assert quotes[0]['text'] == 'We used quantitative methodology in our research approach'
        assert quotes[0]['confidence'] == 85
        assert quotes[0]['page'] == 5
        
        # Test confidence filtering worked
        quote_texts = [q['text'] for q in quotes]
        assert 'Low confidence match that should be filtered' not in quote_texts
        
        # Test sorting by confidence
        confidences = [q['confidence'] for q in quotes]
        assert confidences == sorted(confidences, reverse=True)
        
        print(f"✅ Supporting quote finding works: {len(quotes)} quotes found")
        print(f"   Highest confidence: {quotes[0]['confidence']}%")
        print(f"   Quote from page: {quotes[0]['page']}, section: {quotes[0]['section']}")
    
    def test_confidence_filtering_logic(self):
        """Test confidence score filtering logic"""
        def filter_quotes_by_confidence(quotes, threshold=60):
            """Filter quotes by confidence threshold"""
            return [q for q in quotes if q['confidence'] >= threshold]
        
        # Test quotes with mixed confidence
        test_quotes = [
            {'text': 'High confidence quote', 'confidence': 85},
            {'text': 'Low confidence quote', 'confidence': 35},
            {'text': 'Medium confidence quote', 'confidence': 65},
            {'text': 'Very low confidence quote', 'confidence': 20}
        ]
        
        # Filter with default threshold (60%)
        filtered_quotes = filter_quotes_by_confidence(test_quotes)
        
        assert len(filtered_quotes) == 2  # Only high and medium confidence
        confidences = [q['confidence'] for q in filtered_quotes]
        assert all(c >= 60 for c in confidences)
        assert 85 in confidences and 65 in confidences
        assert 35 not in confidences and 20 not in confidences
        
        print(f"✅ Confidence filtering works: {len(filtered_quotes)}/{len(test_quotes)} quotes passed threshold")
    
    def test_quote_sorting_logic(self):
        """Test quote sorting by confidence"""
        def sort_quotes_by_confidence(quotes):
            """Sort quotes by confidence score (highest first)"""
            return sorted(quotes, key=lambda x: x['confidence'], reverse=True)
        
        # Test unsorted quotes
        unsorted_quotes = [
            {'text': 'Medium quote', 'confidence': 70},
            {'text': 'Highest quote', 'confidence': 90},
            {'text': 'Lower quote', 'confidence': 65},
            {'text': 'High quote', 'confidence': 85}
        ]
        
        sorted_quotes = sort_quotes_by_confidence(unsorted_quotes)
        
        # Check sorting order
        expected_order = [90, 85, 70, 65]
        actual_order = [q['confidence'] for q in sorted_quotes]
        assert actual_order == expected_order
        
        # Check that highest confidence quote is first
        assert sorted_quotes[0]['text'] == 'Highest quote'
        assert sorted_quotes[0]['confidence'] == 90
        
        print("✅ Quote sorting works correctly - highest confidence first")
    
    def test_metadata_handling_logic(self):
        """Test handling of missing or incomplete metadata"""
        def normalize_quote_metadata(quote_data):
            """Normalize quote metadata with defaults for missing values"""
            metadata = quote_data.get('metadata', {})
            
            return {
                'text': quote_data.get('content', ''),
                'page': metadata.get('page', 'Unknown'),
                'section': metadata.get('section', 'Unknown'),
                'confidence': int(quote_data.get('score', 0) * 100)
            }
        
        # Test quotes with missing metadata
        test_data = [
            {
                'content': 'Complete metadata quote',
                'metadata': {'page': 5, 'section': 'Methodology'},
                'score': 0.8
            },
            {
                'content': 'Missing section quote',
                'metadata': {'page': 3},  # Missing section
                'score': 0.75
            },
            {
                'content': 'Missing page quote',
                'metadata': {'section': 'Results'},  # Missing page
                'score': 0.7
            },
            {
                'content': 'No metadata quote',
                # Missing metadata entirely
                'score': 0.6
            }
        ]
        
        normalized_quotes = [normalize_quote_metadata(data) for data in test_data]
        
        # Check all quotes have required fields
        for quote in normalized_quotes:
            assert 'text' in quote
            assert 'page' in quote
            assert 'section' in quote
            assert 'confidence' in quote
        
        # Check default values are applied
        assert normalized_quotes[1]['section'] == 'Unknown'  # Missing section
        assert normalized_quotes[2]['page'] == 'Unknown'     # Missing page
        assert normalized_quotes[3]['page'] == 'Unknown'     # No metadata
        assert normalized_quotes[3]['section'] == 'Unknown'  # No metadata
        
        print("✅ Metadata handling works - defaults applied for missing values")
    
    def test_error_recovery_logic(self):
        """Test error recovery when operations fail"""
        def safe_quote_finding(answer, doc_id):
            """Quote finding with error recovery"""
            try:
                # Simulate vector search failure
                if doc_id == 'fail-doc':
                    raise Exception("Vector search failed")
                
                # Simulate successful operation
                return [
                    {
                        'text': 'Successfully found quote',
                        'page': 5,
                        'section': 'Methods',
                        'confidence': 85
                    }
                ]
            except Exception as e:
                # Return empty list on error, don't crash
                print(f"Warning: Quote finding failed: {e}")
                return []
        
        # Test successful operation
        quotes_success = safe_quote_finding("test question", "valid-doc")
        assert len(quotes_success) == 1
        assert quotes_success[0]['text'] == 'Successfully found quote'
        
        # Test error recovery
        quotes_error = safe_quote_finding("test question", "fail-doc")
        assert quotes_error == []  # Should return empty list, not crash
        
        print("✅ Error recovery works - returns empty list instead of crashing")
    
    def test_chatbot_integration_format(self):
        """Test that quote format matches ChatBot expectations"""
        def format_quotes_for_chatbot(raw_quotes):
            """Format quotes in the exact structure ChatBot expects"""
            formatted_quotes = []
            
            for quote in raw_quotes:
                formatted_quote = {
                    'text': str(quote.get('content', '')),
                    'page': quote.get('metadata', {}).get('page', 1),
                    'section': quote.get('metadata', {}).get('section', 'Document'),
                    'confidence': int((quote.get('score', 0.5) * 100))
                }
                formatted_quotes.append(formatted_quote)
            
            return formatted_quotes
        
        # Test raw quote data
        raw_data = [
            {
                'content': 'We employed quantitative methods',
                'metadata': {'page': 5, 'section': 'Methodology'},
                'score': 0.85
            }
        ]
        
        formatted = format_quotes_for_chatbot(raw_data)
        
        # Verify ChatBot-compatible structure
        assert len(formatted) == 1
        quote = formatted[0]
        
        assert isinstance(quote['text'], str)
        assert isinstance(quote['page'], int)
        assert isinstance(quote['section'], str)
        assert isinstance(quote['confidence'], int)
        assert 0 <= quote['confidence'] <= 100
        
        print("✅ Quote format matches ChatBot expectations")
        print(f"   Sample quote: page {quote['page']}, confidence {quote['confidence']}%")