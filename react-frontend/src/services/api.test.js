import { askWithQuotes, analyzePaper, generateResearchQuestions, uploadFile } from './api';

// Mock fetch globally
global.fetch = jest.fn();

describe('API Service', () => {
  beforeEach(() => {
    fetch.mockClear();
  });
  
  describe('askWithQuotes', () => {
    test('makes correct API call and returns response', async () => {
      const mockResponse = {
        answer: 'Test answer',
        supporting_quotes: [
          { text: 'Test quote', page: 1, confidence: 85 }
        ]
      };
      
      fetch.mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });
      
      const result = await askWithQuotes('doc-123', 'What is this about?');
      
      expect(fetch).toHaveBeenCalledWith('http://localhost:5000/ask-with-quotes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: 'doc-123',
          question: 'What is this about?'
        })
      });
      
      expect(result).toEqual(mockResponse);
    });
    
    test('handles API errors', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Server error' })
      });
      
      await expect(askWithQuotes('doc-123', 'test question')).rejects.toThrow();
    });
    
    test('handles network errors', async () => {
      fetch.mockRejectedValue(new Error('Network error'));
      
      await expect(askWithQuotes('doc-123', 'test question')).rejects.toThrow('Network error');
    });
    
    test('validates required parameters', async () => {
      await expect(askWithQuotes('', 'question')).rejects.toThrow();
      await expect(askWithQuotes('doc-123', '')).rejects.toThrow();
    });
  });
  
  describe('analyzePaper', () => {
    test('makes correct API call and returns response', async () => {
      const mockResponse = {
        research_focus: 'AI Research',
        key_findings: ['Finding 1', 'Finding 2'],
        methodology: 'Experimental'
      };
      
      fetch.mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });
      
      const result = await analyzePaper('doc-123');
      
      expect(fetch).toHaveBeenCalledWith('http://localhost:5000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: 'doc-123' })
      });
      
      expect(result).toEqual(mockResponse);
    });
    
    test('handles missing document ID', async () => {
      await expect(analyzePaper('')).rejects.toThrow();
    });
    
    test('handles API errors', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: 'Document not found' })
      });
      
      await expect(analyzePaper('nonexistent-doc')).rejects.toThrow();
    });
  });
  
  describe('generateResearchQuestions', () => {
    test('makes correct API call and returns questions', async () => {
      const mockQuestions = [
        'What is the main research question?',
        'What methodology was used?',
        'What are the key findings?'
      ];
      
      fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ questions: mockQuestions })
      });
      
      const result = await generateResearchQuestions('doc-123');
      
      expect(fetch).toHaveBeenCalledWith('http://localhost:5000/generate-questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: 'doc-123' })
      });
      
      expect(result).toEqual(mockQuestions);
    });
    
    test('handles empty questions response', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ questions: [] })
      });
      
      const result = await generateResearchQuestions('doc-123');
      expect(result).toEqual([]);
    });
  });
  
  describe('uploadFile', () => {
    test('uploads file correctly', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      const mockResponse = {
        document_id: 'doc-123',
        status: 'processing'
      };
      
      fetch.mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      });
      
      const result = await uploadFile(mockFile);
      
      expect(fetch).toHaveBeenCalledWith('http://localhost:5000/upload', {
        method: 'POST',
        body: expect.any(FormData)
      });
      
      expect(result).toEqual(mockResponse);
    });
    
    test('handles file upload errors', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      
      fetch.mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Invalid file format' })
      });
      
      await expect(uploadFile(mockFile)).rejects.toThrow();
    });
    
    test('validates file parameter', async () => {
      await expect(uploadFile(null)).rejects.toThrow();
      await expect(uploadFile(undefined)).rejects.toThrow();
    });
  });
  
  describe('API error handling', () => {
    test('handles malformed JSON responses', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => { throw new Error('Invalid JSON'); }
      });
      
      await expect(askWithQuotes('doc-123', 'question')).rejects.toThrow();
    });
    
    test('handles timeout errors', async () => {
      fetch.mockImplementation(() => 
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Timeout')), 100)
        )
      );
      
      await expect(askWithQuotes('doc-123', 'question')).rejects.toThrow('Timeout');
    });
    
    test('handles different HTTP error codes', async () => {
      const testCases = [
        { status: 400, error: 'Bad Request' },
        { status: 401, error: 'Unauthorized' },
        { status: 403, error: 'Forbidden' },
        { status: 404, error: 'Not Found' },
        { status: 500, error: 'Internal Server Error' }
      ];
      
      for (const testCase of testCases) {
        fetch.mockResolvedValue({
          ok: false,
          status: testCase.status,
          json: async () => ({ error: testCase.error })
        });
        
        await expect(askWithQuotes('doc-123', 'question')).rejects.toThrow();
      }
    });
  });
});