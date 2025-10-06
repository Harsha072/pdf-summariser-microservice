import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ControlPanel from './ControlPanel';
import { useDocument } from '../../context/DocumentContext';

jest.mock('../../context/DocumentContext');
jest.mock('../ChatBot/ChatBot', () => {
  return function MockChatBot() {
    return <div data-testid="mock-chatbot">ChatBot Component</div>;
  };
});

describe('ControlPanel Component', () => {
  const mockDocument = {
    id: 'test-doc-123',
    fileName: 'test-document.pdf',
    status: 'ready'
  };
  
  beforeEach(() => {
    useDocument.mockReturnValue({
      document: mockDocument
    });
    
    jest.clearAllMocks();
  });
  
  test('renders control panel with ChatBot', () => {
    render(<ControlPanel />);
    
    expect(screen.getByTestId('mock-chatbot')).toBeInTheDocument();
  });
  
  test('shows popup overlay during upload', () => {
    useDocument.mockReturnValue({
      document: { ...mockDocument, status: 'uploading' }
    });
    
    render(<ControlPanel />);
    
    expect(screen.getByText('Analysing document')).toBeInTheDocument();
    expect(screen.getByText('Please wait while we process your document...')).toBeInTheDocument();
  });
  
  test('shows popup overlay during processing', () => {
    useDocument.mockReturnValue({
      document: { ...mockDocument, status: 'processing' }
    });
    
    render(<ControlPanel />);
    
    expect(screen.getByText('Analysing document')).toBeInTheDocument();
    expect(screen.getByText('Please wait while we process your document...')).toBeInTheDocument();
  });
  
  test('hides popup when document is ready', () => {
    useDocument.mockReturnValue({
      document: { ...mockDocument, status: 'ready' }
    });
    
    render(<ControlPanel />);
    
    expect(screen.queryByText('Analysing document')).not.toBeInTheDocument();
  });
  
  test('popup has correct styling classes', () => {
    useDocument.mockReturnValue({
      document: { ...mockDocument, status: 'processing' }
    });
    
    render(<ControlPanel />);
    
    const popupOverlay = screen.getByText('Analysing document').closest('.popup-overlay');
    expect(popupOverlay).toBeInTheDocument();
    
    const popupAlert = screen.getByText('Analysing document').closest('.popup-alert');
    expect(popupAlert).toBeInTheDocument();
  });
  
  test('shows spinner during processing', () => {
    useDocument.mockReturnValue({
      document: { ...mockDocument, status: 'processing' }
    });
    
    render(<ControlPanel />);
    
    const spinner = document.querySelector('.processing-spinner');
    expect(spinner).toBeInTheDocument();
  });
  
  test('handles different document statuses correctly', () => {
    const statuses = ['idle', 'ready', 'error'];
    
    statuses.forEach(status => {
      useDocument.mockReturnValue({
        document: { ...mockDocument, status }
      });
      
      const { rerender } = render(<ControlPanel />);
      
      // Should not show popup for non-processing statuses
      expect(screen.queryByText('Analysing document')).not.toBeInTheDocument();
      
      rerender(<div />); // Clear for next iteration
    });
  });
  
  test('popup overlay covers entire viewport', () => {
    useDocument.mockReturnValue({
      document: { ...mockDocument, status: 'uploading' }
    });
    
    render(<ControlPanel />);
    
    const overlay = document.querySelector('.popup-overlay');
    expect(overlay).toHaveStyle({
      position: 'fixed',
      top: '0',
      left: '0',
      width: '100vw',
      height: '100vh'
    });
  });
  
  test('renders without document context', () => {
    useDocument.mockReturnValue({
      document: null
    });
    
    render(<ControlPanel />);
    
    // Should render ChatBot even without document
    expect(screen.getByTestId('mock-chatbot')).toBeInTheDocument();
    // Should not show popup
    expect(screen.queryByText('Analysing document')).not.toBeInTheDocument();
  });
  
  test('handles undefined document status', () => {
    useDocument.mockReturnValue({
      document: { ...mockDocument, status: undefined }
    });
    
    render(<ControlPanel />);
    
    // Should not show popup for undefined status
    expect(screen.queryByText('Analysing document')).not.toBeInTheDocument();
  });
});