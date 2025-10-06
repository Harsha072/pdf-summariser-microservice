import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import PDFViewer from './PDFViewer';
import { useDocument } from '../../context/DocumentContext';

jest.mock('../../context/DocumentContext');

// Mock PDF.js
const mockPdfJs = {
  getDocument: jest.fn(() => Promise.resolve({
    numPages: 10,
    getPage: jest.fn(() => Promise.resolve({
      getViewport: jest.fn(() => ({ width: 800, height: 1000 })),
      render: jest.fn(() => ({
        promise: Promise.resolve()
      })),
      getTextContent: jest.fn(() => Promise.resolve({
        items: [
          { str: 'This is a test sentence with methodology mentioned.' }
        ]
      }))
    }))
  })),
  GlobalWorkerOptions: { workerSrc: '' }
};

// Mock PDF.js globally
global.pdfjsLib = mockPdfJs;

describe('PDFViewer Component', () => {
  const mockPdfDocument = {
    pdfData: 'mock-pdf-data',
    currentPage: 1,
    totalPages: 10,
    zoom: 1.0
  };
  
  beforeEach(() => {
    useDocument.mockReturnValue({
      pdfDocument: mockPdfDocument
    });
    
    // Mock DOM methods
    document.querySelectorAll = jest.fn(() => []);
    document.getElementById = jest.fn(() => ({
      getContext: jest.fn(() => ({
        clearRect: jest.fn(),
        fillRect: jest.fn(),
        fillText: jest.fn(),
        setTransform: jest.fn()
      }))
    }));
    
    jest.clearAllMocks();
  });
  
  test('renders PDF viewer container', () => {
    render(<PDFViewer />);
    expect(screen.getByTestId('pdf-viewer')).toBeInTheDocument();
  });
  
  test('handles highlight event correctly', () => {
    const mockTextElement = {
      textContent: 'This is a test sentence with methodology mentioned.',
      style: {},
      classList: {
        add: jest.fn(),
        remove: jest.fn()
      },
      parentElement: {
        style: {}
      }
    };
    
    document.querySelectorAll = jest.fn(() => [mockTextElement]);
    
    render(<PDFViewer />);
    
    // Trigger highlight event
    const highlightEvent = new CustomEvent('highlightInPDF', {
      detail: {
        page: 1,
        searchTerm: 'methodology',
        searchTerms: ['methodology']
      }
    });
    
    window.dispatchEvent(highlightEvent);
    
    // Check if highlighting logic was triggered
    expect(document.querySelectorAll).toHaveBeenCalled();
  });
  
  test('handles undefined search terms safely', () => {
    render(<PDFViewer />);
    
    // Trigger highlight event with undefined terms
    const highlightEvent = new CustomEvent('highlightInPDF', {
      detail: {
        page: 1,
        searchTerm: undefined,
        searchTerms: undefined
      }
    });
    
    // Should not throw error
    expect(() => {
      window.dispatchEvent(highlightEvent);
    }).not.toThrow();
  });
  
  test('handles empty PDF document', () => {
    useDocument.mockReturnValue({
      pdfDocument: null
    });
    
    render(<PDFViewer />);
    
    // Should render without PDF data
    expect(screen.getByTestId('pdf-viewer')).toBeInTheDocument();
  });
  
  test('handles zoom changes', () => {
    const mockSetZoom = jest.fn();
    
    useDocument.mockReturnValue({
      pdfDocument: { ...mockPdfDocument, setZoom: mockSetZoom }
    });
    
    render(<PDFViewer />);
    
    // Mock zoom controls
    const zoomInBtn = screen.getByTitle('Zoom in');
    const zoomOutBtn = screen.getByTitle('Zoom out');
    
    fireEvent.click(zoomInBtn);
    fireEvent.click(zoomOutBtn);
    
    // Should handle zoom interactions
    expect(mockSetZoom).toHaveBeenCalled();
  });
  
  test('handles page navigation', () => {
    const mockSetPage = jest.fn();
    
    useDocument.mockReturnValue({
      pdfDocument: { ...mockPdfDocument, setCurrentPage: mockSetPage }
    });
    
    render(<PDFViewer />);
    
    // Mock page navigation
    const nextBtn = screen.getByTitle('Next page');
    const prevBtn = screen.getByTitle('Previous page');
    
    fireEvent.click(nextBtn);
    fireEvent.click(prevBtn);
    
    // Should handle page navigation
    expect(mockSetPage).toHaveBeenCalled();
  });
  
  test('highlights multiple search terms', () => {
    const mockTextElements = [
      {
        textContent: 'The methodology section discusses quantitative analysis.',
        style: {},
        classList: { add: jest.fn(), remove: jest.fn() },
        parentElement: { style: {} }
      },
      {
        textContent: 'Our methodology involved statistical methods.',
        style: {},
        classList: { add: jest.fn(), remove: jest.fn() },
        parentElement: { style: {} }
      }
    ];
    
    document.querySelectorAll = jest.fn(() => mockTextElements);
    
    render(<PDFViewer />);
    
    const highlightEvent = new CustomEvent('highlightInPDF', {
      detail: {
        page: 1,
        searchTerm: 'methodology',
        searchTerms: ['methodology', 'quantitative']
      }
    });
    
    window.dispatchEvent(highlightEvent);
    
    expect(document.querySelectorAll).toHaveBeenCalled();
    // Should apply highlighting to matching elements
    mockTextElements.forEach(element => {
      expect(element.classList.add).toHaveBeenCalled();
    });
  });
  
  test('clears previous highlights before applying new ones', () => {
    const mockTextElement = {
      textContent: 'Test content',
      style: {},
      classList: { 
        add: jest.fn(), 
        remove: jest.fn(),
        contains: jest.fn(() => true)
      },
      parentElement: { style: {} }
    };
    
    document.querySelectorAll = jest.fn()
      .mockReturnValueOnce([mockTextElement]) // For clearing
      .mockReturnValueOnce([mockTextElement]); // For highlighting
    
    render(<PDFViewer />);
    
    const highlightEvent = new CustomEvent('highlightInPDF', {
      detail: {
        page: 1,
        searchTerm: 'test',
        searchTerms: ['test']
      }
    });
    
    window.dispatchEvent(highlightEvent);
    
    // Should clear previous highlights first
    expect(mockTextElement.classList.remove).toHaveBeenCalled();
  });
});