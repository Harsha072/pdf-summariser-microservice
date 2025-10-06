import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChatBot from './ChatBot';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';
import { askWithQuotes, analyzePaper, generateResearchQuestions } from '../../services/api';

// Mock the contexts and API
jest.mock('../../context/DocumentContext');
jest.mock('../../context/NotificationContext');
jest.mock('../../services/api');

describe('ChatBot Component', () => {
  const mockDocument = {
    id: 'test-doc-123',
    fileName: 'test-document.pdf',
    status: 'ready'
  };
  
  const mockShowNotification = jest.fn();
  const mockUpdateQa = jest.fn();
  
  beforeEach(() => {
    useDocument.mockReturnValue({
      document: mockDocument,
      qa: {},
      updateQa: mockUpdateQa
    });
    
    useNotification.mockReturnValue({
      showNotification: mockShowNotification
    });
    
    // Mock window.dispatchEvent for PDF highlighting
    window.dispatchEvent = jest.fn();
    
    jest.clearAllMocks();
  });
  
  test('renders welcome message when document is ready', () => {
    render(<ChatBot />);
    
    expect(screen.getByText(/Hi! I'm your AI assistant/)).toBeInTheDocument();
    expect(screen.getByText(/test-document.pdf/)).toBeInTheDocument();
  });
  
  test('shows suggestion chips when document is ready', () => {
    render(<ChatBot />);
    
    expect(screen.getByText('📋 Generate Summary')).toBeInTheDocument();
    expect(screen.getByText('🤔 Research Questions')).toBeInTheDocument();
    expect(screen.getByText('💡 Explain Key Concepts')).toBeInTheDocument();
  });
  
  test('disables input when document is not ready', () => {
    useDocument.mockReturnValue({
      document: { ...mockDocument, status: 'processing' },
      qa: {},
      updateQa: mockUpdateQa
    });
    
    render(<ChatBot />);
    
    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeDisabled();
  });
  
  test('sends message and shows Smart Quote response', async () => {
    const mockResponse = {
      answer: 'The methodology is quantitative analysis.',
      supporting_quotes: [
        {
          text: 'We employed quantitative methods',
          page: 5,
          section: 'Methodology',
          confidence: 85
        }
      ],
      confidence: 85
    };
    
    askWithQuotes.mockResolvedValue(mockResponse);
    
    render(<ChatBot />);
    
    const textarea = screen.getByRole('textbox');
    const sendButton = screen.getByTitle('Send message');
    
    // Type and send message
    fireEvent.change(textarea, { target: { value: 'What methodology was used?' } });
    fireEvent.click(sendButton);
    
    // Check user message appears
    expect(screen.getByText('What methodology was used?')).toBeInTheDocument();
    
    // Wait for AI response
    await waitFor(() => {
      expect(screen.getByText(/quantitative analysis/)).toBeInTheDocument();
    });
    
    // Check supporting quotes appear
    await waitFor(() => {
      expect(screen.getByText('📍 Supporting Quotes')).toBeInTheDocument();
      expect(screen.getByText(/We employed quantitative methods/)).toBeInTheDocument();
    });
  });
  
  test('handles API error gracefully', async () => {
    askWithQuotes.mockRejectedValue(new Error('API Error'));
    
    render(<ChatBot />);
    
    const textarea = screen.getByRole('textbox');
    const sendButton = screen.getByTitle('Send message');
    
    fireEvent.change(textarea, { target: { value: 'Test question' } });
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText(/Sorry, I encountered an error/)).toBeInTheDocument();
    });
  });
  
  test('quote click triggers PDF highlight event', async () => {
    const mockResponse = {
      answer: 'Test answer',
      supporting_quotes: [
        {
          text: 'Test quote',
          page: 5,
          section: 'Test Section',
          confidence: 85
        }
      ]
    };
    
    askWithQuotes.mockResolvedValue(mockResponse);
    
    render(<ChatBot />);
    
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'Test question' } });
    fireEvent.click(screen.getByTitle('Send message'));
    
    await waitFor(() => {
      const quoteCard = screen.getByText(/Test quote/);
      fireEvent.click(quoteCard.closest('.quote-card'));
    });
    
    expect(window.dispatchEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'highlightInPDF',
        detail: expect.objectContaining({
          page: 5,
          searchTerm: 'Test quote'
        })
      })
    );
  });
  
  test('suggestion chip clicks work correctly', async () => {
    render(<ChatBot />);
    
    const summaryButton = screen.getByText('📋 Generate Summary');
    fireEvent.click(summaryButton);
    
    expect(screen.getByText('📋 Generate document summary')).toBeInTheDocument();
  });
  
  test('handles empty message submission', () => {
    render(<ChatBot />);
    
    const sendButton = screen.getByTitle('Send message');
    fireEvent.click(sendButton);
    
    // Should not send empty message
    expect(askWithQuotes).not.toHaveBeenCalled();
  });
  
  test('handles enter key press to send message', async () => {
    const mockResponse = {
      answer: 'Test answer',
      supporting_quotes: [],
      confidence: 85
    };
    
    askWithQuotes.mockResolvedValue(mockResponse);
    
    render(<ChatBot />);
    
    const textarea = screen.getByRole('textbox');
    
    fireEvent.change(textarea, { target: { value: 'Test question' } });
    fireEvent.keyPress(textarea, { key: 'Enter', code: 'Enter', charCode: 13 });
    
    await waitFor(() => {
      expect(askWithQuotes).toHaveBeenCalledWith('test-doc-123', 'Test question');
    });
  });
  
  test('prevents enter key from sending when shift is pressed', () => {
    render(<ChatBot />);
    
    const textarea = screen.getByRole('textbox');
    
    fireEvent.change(textarea, { target: { value: 'Test question' } });
    fireEvent.keyPress(textarea, { 
      key: 'Enter', 
      code: 'Enter', 
      charCode: 13, 
      shiftKey: true 
    });
    
    // Should not send message when Shift+Enter
    expect(askWithQuotes).not.toHaveBeenCalled();
  });
  
  test('shows typing indicator while processing', async () => {
    // Mock a delayed response
    askWithQuotes.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        answer: 'Test answer',
        supporting_quotes: [],
        confidence: 85
      }), 100))
    );
    
    render(<ChatBot />);
    
    const textarea = screen.getByRole('textbox');
    const sendButton = screen.getByTitle('Send message');
    
    fireEvent.change(textarea, { target: { value: 'Test question' } });
    fireEvent.click(sendButton);
    
    // Should show typing indicator
    expect(screen.getByText('AI is thinking...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText('Test answer')).toBeInTheDocument();
    });
  });
  
  test('analyze paper functionality works', async () => {
    const mockAnalysisResponse = {
      research_focus: 'Machine Learning',
      key_findings: ['Finding 1', 'Finding 2'],
      methodology: 'Experimental'
    };
    
    analyzePaper.mockResolvedValue(mockAnalysisResponse);
    
    render(<ChatBot />);
    
    const analyzeButton = screen.getByText('🔬 Analyze Paper');
    fireEvent.click(analyzeButton);
    
    await waitFor(() => {
      expect(analyzePaper).toHaveBeenCalledWith('test-doc-123');
    });
    
    await waitFor(() => {
      expect(screen.getByText(/Machine Learning/)).toBeInTheDocument();
    });
  });
  
  test('generates research questions correctly', async () => {
    const mockQuestionsResponse = [
      'What is the main research question?',
      'What methodology was used?',
      'What are the key findings?'
    ];
    
    generateResearchQuestions.mockResolvedValue(mockQuestionsResponse);
    
    render(<ChatBot />);
    
    const questionsButton = screen.getByText('🤔 Research Questions');
    fireEvent.click(questionsButton);
    
    await waitFor(() => {
      expect(generateResearchQuestions).toHaveBeenCalledWith('test-doc-123');
    });
    
    await waitFor(() => {
      expect(screen.getByText(/What is the main research question/)).toBeInTheDocument();
    });
  });
});