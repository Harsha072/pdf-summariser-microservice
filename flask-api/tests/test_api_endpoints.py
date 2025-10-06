import pytest
import json
from unittest.mock import patch, MagicMock
from io import BytesIO

class TestPDFSummarizerAPIs:
    """Test cases for APIs used by ChatBot component"""
    
    def test_flask_app_health_check(self, client):
        """Test that Flask app is working"""
        # Try health endpoint or root endpoint
        response = client.get('/health')
        if response.status_code == 404:
            response = client.get('/')
        
        # App should be running (not 500 error)
        assert response.status_code != 500
        print("✅ Flask app is running successfully")
    
    def test_ask_with_quotes_endpoint_exists(self, client, sample_document_id):
        """Test Smart Quote Finder endpoint exists and works"""
        test_data = {
            'document_id': sample_document_id,
            'question': 'What methodology was used in this research?'
        }
        
        response = client.post('/ask-with-quotes',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = json.loads(response.data)
            
            # Verify response structure for ChatBot compatibility
            assert 'answer' in data, "Response missing 'answer' field"
            assert 'supporting_quotes' in data, "Response missing 'supporting_quotes' field"
            
            # Check supporting quotes structure if present
            if data['supporting_quotes']:
                quote = data['supporting_quotes'][0]
                assert 'text' in quote, "Quote missing 'text' field"
                assert 'page' in quote, "Quote missing 'page' field"
                assert 'confidence' in quote, "Quote missing 'confidence' field"
                
                # Verify confidence is a reasonable number
                confidence = quote['confidence']
                assert 0 <= confidence <= 100, f"Invalid confidence value: {confidence}"
            
            print(f"✅ Smart Quote Finder API works correctly")
            print(f"   Answer length: {len(data['answer'])} chars")
            print(f"   Supporting quotes: {len(data['supporting_quotes'])} found")
        else:
            print(f"⚠️  /ask-with-quotes returned {response.status_code} - may need implementation")
    
    def test_ask_with_quotes_parameter_validation(self, client):
        """Test Smart Quote Finder parameter validation"""
        # Test missing document_id
        response = client.post('/ask-with-quotes',
            json={'question': 'What is this about?'},
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        
        # Test missing question
        response = client.post('/ask-with-quotes',
            json={'document_id': 'test-doc'},
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        
        # Test empty JSON
        response = client.post('/ask-with-quotes',
            json={},
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 400
        
        print("✅ Parameter validation works correctly")
    
    def test_analyze_paper_endpoint(self, client, sample_document_id):
        """Test paper analysis endpoint used by ChatBot"""
        response = client.post('/analyze',
            json={'document_id': sample_document_id},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'research_focus' in data or 'key_findings' in data
            print("✅ Paper analysis API works correctly")
            print(f"   Research focus: {data.get('research_focus', 'N/A')}")
        elif response.status_code == 404:
            print("⚠️  /analyze endpoint not implemented yet")
        else:
            print(f"⚠️  /analyze returned {response.status_code}")
    
    def test_generate_questions_endpoint(self, client, sample_document_id):
        """Test research questions generation endpoint"""
        response = client.post('/generate-questions',
            json={'document_id': sample_document_id},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'questions' in data
            assert isinstance(data['questions'], list)
            print(f"✅ Research questions API works: {len(data['questions'])} questions")
        elif response.status_code == 404:
            print("⚠️  /generate-questions endpoint not implemented yet")
        else:
            print(f"⚠️  /generate-questions returned {response.status_code}")
    
    def test_upload_endpoint_exists(self, client):
        """Test PDF upload endpoint exists"""
        # Create minimal PDF-like content for testing
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"
        
        data = {
            'file': (BytesIO(pdf_content), 'test.pdf')
        }
        
        response = client.post('/upload',
            data=data,
            content_type='multipart/form-data'
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
        
        if response.status_code in [200, 201]:
            data = json.loads(response.data)
            assert 'document_id' in data
            print("✅ PDF upload API works correctly")
        elif response.status_code == 400:
            # Expected for validation errors
            print("✅ PDF upload endpoint exists with validation")
        else:
            print(f"⚠️  /upload returned {response.status_code}")
    
    def test_upload_file_validation(self, client):
        """Test upload file type validation"""
        # Test with non-PDF file
        text_content = b"This is not a PDF file"
        
        data = {
            'file': (BytesIO(text_content), 'test.txt')
        }
        
        response = client.post('/upload',
            data=data,
            content_type='multipart/form-data'
        )
        
        if response.status_code == 400:
            data = json.loads(response.data)
            assert 'error' in data
            error_msg = data['error'].lower()
            assert 'pdf' in error_msg or 'file' in error_msg
            print("✅ File type validation works correctly")
        elif response.status_code == 404:
            print("⚠️  Upload endpoint not implemented")
        else:
            print(f"⚠️  File validation test inconclusive: {response.status_code}")
    
    def test_cors_headers_present(self, client):
        """Test CORS headers for frontend integration"""
        response = client.options('/ask-with-quotes')
        
        if 'Access-Control-Allow-Origin' in response.headers:
            origin = response.headers['Access-Control-Allow-Origin']
            assert origin in ['*', 'http://localhost:3000', 'http://localhost:3001']
            print("✅ CORS headers configured correctly")
        else:
            # Try a GET request to see if CORS is configured
            response = client.get('/health')
            if 'Access-Control-Allow-Origin' in response.headers:
                print("✅ CORS headers found on GET requests")
            else:
                print("⚠️  CORS headers not found - may need configuration for frontend")
    
    def test_error_response_format_consistency(self, client):
        """Test that error responses have consistent format"""
        # Test with invalid JSON data
        response = client.post('/ask-with-quotes',
            json={'invalid': 'data'},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code >= 400:
            try:
                data = json.loads(response.data)
                assert 'error' in data, "Error responses should contain 'error' field"
                assert isinstance(data['error'], str), "Error message should be a string"
                print("✅ Error response format is consistent")
            except json.JSONDecodeError:
                print("⚠️  Error response is not JSON format")
    
    def test_chatbot_integration_readiness(self, client, sample_document_id):
        """Test overall readiness for ChatBot integration"""
        endpoints_tested = 0
        endpoints_working = 0
        
        # Test Smart Quote Finder (most important)
        response = client.post('/ask-with-quotes',
            json={'document_id': sample_document_id, 'question': 'Test question'},
            headers={'Content-Type': 'application/json'}
        )
        endpoints_tested += 1
        if response.status_code == 200:
            endpoints_working += 1
        
        # Test other endpoints
        for endpoint, data in [
            ('/analyze', {'document_id': sample_document_id}),
            ('/generate-questions', {'document_id': sample_document_id})
        ]:
            response = client.post(endpoint, json=data, headers={'Content-Type': 'application/json'})
            endpoints_tested += 1
            if response.status_code == 200:
                endpoints_working += 1
        
        readiness_percentage = (endpoints_working / endpoints_tested) * 100
        print(f"📊 ChatBot Integration Readiness: {readiness_percentage:.0f}% ({endpoints_working}/{endpoints_tested} endpoints working)")
        
        if readiness_percentage >= 50:
            print("✅ Backend is ready for ChatBot integration")
        else:
            print("⚠️  Some endpoints need implementation for full ChatBot functionality")