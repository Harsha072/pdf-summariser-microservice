import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../App';
import { DocumentProvider } from '../context/DocumentContext';
import { NotificationProvider } from '../context/NotificationContext';
import * as api from '../services/api';

// Mock all API calls
jest.mock('../services/api');

// Mock file upload
const mockUploadFile = api.uploadFile;
const mockAskWithQuotes = api.askWithQuotes;

describe('Smart Quote Finder Integration Tests', () => {
  
  const TestWrapper = ({ children }) => (
    <NotificationProvider>
      <DocumentProvider>
        {children}
      </DocumentProvider>
    </NotificationProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('Complete Smart Quote Finder workflow', async () => {
    // Mock file upload response
    mockUploadFile.mockResolvedValue({
      document_id: 'test-doc-123',
      status: 'processing'
    });

    // Mock Smart Quote Finder response
    mockAskWithQuotes.mockResolvedValue({
      answer: 'The methodology involves quantitative analysis using statistical methods.',
      supporting_quotes: [
        {
          text: 'We employed quantitative analysis methods to evaluate the data',
          page: 5,
          section: 'Methodology',
          confidence: 92
        },
        {
          text: 'Statistical methods were used for data processing',
          page: 6,
          section: 'Data Analysis',
          confidence: 87
        }
      ],
      confidence: 85
    });

    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // 1. Upload PDF file
    const file = new File(['fake pdf content'], 'research-paper.pdf', {
      type: 'application/pdf'
    });
    
    const fileInput = screen.getByTestId('file-upload-input');
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Wait for upload to complete
    await waitFor(() => {
      expect(mockUploadFile).toHaveBeenCalledWith(file);
    });

    // 2. Simulate document ready state
    // (In real app, this would be handled by document context)
    
    // 3. Ask question with Smart Quote Finder
    const chatInput = screen.getByRole('textbox');
    const sendButton = screen.getByTitle('Send message');

    fireEvent.change(chatInput, { 
      target: { value: 'What methodology was used in this research?' } 
    });
    fireEvent.click(sendButton);

    // 4. Verify Smart Quote Finder response
    await waitFor(() => {
      expect(mockAskWithQuotes).toHaveBeenCalledWith(
        'test-doc-123',
        'What methodology was used in this research?'
      );
    });

    // 5. Check that answer is displayed
    await waitFor(() => {
      expect(screen.getByText(/quantitative analysis/)).toBeInTheDocument();
    });

    // 6. Check that supporting quotes are displayed
    await waitFor(() => {
      expect(screen.getByText('📍 Supporting Quotes')).toBeInTheDocument();
      expect(screen.getByText(/We employed quantitative analysis methods/)).toBeInTheDocument();
      expect(screen.getByText(/Statistical methods were used/)).toBeInTheDocument();
    });

    // 7. Test quote clicking for PDF highlighting
    const mockDispatchEvent = jest.fn();
    window.dispatchEvent = mockDispatchEvent;

    const firstQuote = screen.getByText(/We employed quantitative analysis methods/);
    fireEvent.click(firstQuote.closest('.quote-card'));

    expect(mockDispatchEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'highlightInPDF',
        detail: expect.objectContaining({
          page: 5,
          searchTerm: 'We employed quantitative analysis methods to evaluate the data'
        })
      })
    );
  });

  test('Error handling in Smart Quote Finder', async () => {
    mockUploadFile.mockResolvedValue({
      document_id: 'test-doc-123',
      status: 'ready'
    });

    mockAskWithQuotes.mockRejectedValue(new Error('API Error'));

    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Upload file first
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const fileInput = screen.getByTestId('file-upload-input');
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(mockUploadFile).toHaveBeenCalled();
    });

    // Ask question that will fail
    const chatInput = screen.getByRole('textbox');
    fireEvent.change(chatInput, { target: { value: 'Test question' } });
    fireEvent.click(screen.getByTitle('Send message'));

    // Check error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/Sorry, I encountered an error/)).toBeInTheDocument();
    });
  });

  test('Multiple questions maintain quote history', async () => {
    mockUploadFile.mockResolvedValue({
      document_id: 'test-doc-123',
      status: 'ready'
    });

    // Mock responses for multiple questions
    mockAskWithQuotes
      .mockResolvedValueOnce({
        answer: 'First answer',
        supporting_quotes: [{
          text: 'First quote',
          page: 1,
          section: 'Introduction',
          confidence: 85
        }]
      })
      .mockResolvedValueOnce({
        answer: 'Second answer',
        supporting_quotes: [{
          text: 'Second quote',
          page: 2,
          section: 'Methods',
          confidence: 90
        }]
      });

    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Upload file
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const fileInput = screen.getByTestId('file-upload-input');
    fireEvent.change(fileInput, { target: { files: [file] } });
    await waitFor(() => expect(mockUploadFile).toHaveBeenCalled());

    // Ask first question
    const chatInput = screen.getByRole('textbox');
    fireEvent.change(chatInput, { target: { value: 'First question' } });
    fireEvent.click(screen.getByTitle('Send message'));

    await waitFor(() => {
      expect(screen.getByText('First answer')).toBeInTheDocument();
      expect(screen.getByText('First quote')).toBeInTheDocument();
    });

    // Ask second question
    fireEvent.change(chatInput, { target: { value: 'Second question' } });
    fireEvent.click(screen.getByTitle('Send message'));

    await waitFor(() => {
      expect(screen.getByText('Second answer')).toBeInTheDocument();
      expect(screen.getByText('Second quote')).toBeInTheDocument();
    });

    // Both answers should still be visible (chat history)
    expect(screen.getByText('First answer')).toBeInTheDocument();
    expect(screen.getByText('First quote')).toBeInTheDocument();
  });

  test('Suggestion chips trigger Smart Quote Finder', async () => {
    mockUploadFile.mockResolvedValue({
      document_id: 'test-doc-123', 
      status: 'ready'
    });

    mockAskWithQuotes.mockResolvedValue({
      answer: 'Document summary',
      supporting_quotes: [],
      confidence: 85
    });

    render(
      <TestWrapper>
        <App />
      </TestWrapper>
    );

    // Upload file
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const fileInput = screen.getByTestId('file-upload-input');
    fireEvent.change(fileInput, { target: { files: [file] } });
    await waitFor(() => expect(mockUploadFile).toHaveBeenCalled());

    // Click summary suggestion
    const summaryChip = screen.getByText('📋 Generate Summary');
    fireEvent.click(summaryChip);

    // Should trigger Smart Quote Finder
    await waitFor(() => {
      expect(mockAskWithQuotes).toHaveBeenCalledWith(
        'test-doc-123',
        '📋 Generate document summary'
      );
    });
  });
});