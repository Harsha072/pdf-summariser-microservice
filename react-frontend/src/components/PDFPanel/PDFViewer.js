import React, { useEffect, useRef, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import './PDFViewer.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';

// Set worker source to match package version
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`;

const PDFViewer = () => {
  const { document, updateDocument, clearDocument } = useDocument();
  const { showError, showInfo } = useNotification();
  const canvasRef = useRef(null);
  const pdfDocRef = useRef(null);

  // Load PDF when pdfData changes
  useEffect(() => {
    if (document.pdfData) {
      loadPDF(document.pdfData);
    }
  }, [document.pdfData]);

  // Render page when currentPage or zoom changes
  useEffect(() => {
    if (pdfDocRef.current && document.currentPage) {
      renderPage(document.currentPage);
    }
  }, [document.currentPage, document.zoom]);

  const loadPDF = async (pdfData) => {
    try {
      const pdf = await pdfjsLib.getDocument({ data: pdfData }).promise;
      pdfDocRef.current = pdf;
      
      updateDocument({
        totalPages: pdf.numPages,
        pageCount: pdf.numPages,
        currentPage: 1
      });

      renderPage(1);
    } catch (error) {
      console.error('Error loading PDF:', error);
      showError('Error loading PDF file');
    }
  };

  const renderPage = async (pageNum) => {
    if (!pdfDocRef.current || !canvasRef.current) return;

    try {
      const page = await pdfDocRef.current.getPage(pageNum);
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');

      const viewport = page.getViewport({ scale: document.zoom });
      canvas.height = viewport.height;
      canvas.width = viewport.width;

      const renderContext = {
        canvasContext: context,
        viewport: viewport
      };

      await page.render(renderContext).promise;
    } catch (error) {
      console.error('Error rendering page:', error);
      showError('Error rendering PDF page');
    }
  };

  const previousPage = useCallback(() => {
    if (document.currentPage > 1) {
      updateDocument({ currentPage: document.currentPage - 1 });
    }
  }, [document.currentPage, updateDocument]);

  const nextPage = useCallback(() => {
    if (document.currentPage < document.totalPages) {
      updateDocument({ currentPage: document.currentPage + 1 });
    }
  }, [document.currentPage, document.totalPages, updateDocument]);

  const goToPage = useCallback((pageNum) => {
    const page = parseInt(pageNum);
    if (page >= 1 && page <= document.totalPages) {
      updateDocument({ currentPage: page });
    }
  }, [document.totalPages, updateDocument]);

  const zoomIn = useCallback(() => {
    updateDocument({ zoom: Math.min(document.zoom * 1.2, 3) });
  }, [document.zoom, updateDocument]);

  const zoomOut = useCallback(() => {
    updateDocument({ zoom: Math.max(document.zoom / 1.2, 0.5) });
  }, [document.zoom, updateDocument]);

  const handleClear = useCallback(() => {
    clearDocument();
    showInfo('Document cleared');
  }, [clearDocument, showInfo]);

  return (
    <div className="pdf-viewer">
      {/* Toolbar */}
      <div className="pdf-toolbar">
        <div className="toolbar-section">
          <div className="page-navigation">
            <button 
              className="toolbar-btn" 
              onClick={previousPage}
              disabled={document.currentPage <= 1}
            >
              <i className="fas fa-chevron-left"></i> Previous
            </button>
            <span className="page-info">
              Page 
              <input 
                type="number" 
                className="page-input" 
                value={document.currentPage}
                min="1"
                max={document.totalPages}
                onChange={(e) => goToPage(e.target.value)}
              />
              of {document.totalPages}
            </span>
            <button 
              className="toolbar-btn"
              onClick={nextPage}
              disabled={document.currentPage >= document.totalPages}
            >
              Next <i className="fas fa-chevron-right"></i>
            </button>
          </div>
        </div>
        <div className="toolbar-section">
          <button className="toolbar-btn" onClick={zoomOut}>
            <i className="fas fa-search-minus"></i>
          </button>
          <span className="zoom-level">
            {Math.round(document.zoom * 100)}%
          </span>
          <button className="toolbar-btn" onClick={zoomIn}>
            <i className="fas fa-search-plus"></i>
          </button>
          <button className="toolbar-btn" onClick={handleClear}>
            <i className="fas fa-trash"></i> Clear
          </button>
        </div>
      </div>

      {/* PDF Content */}
      <div className="pdf-content">
        <div className="pdf-canvas-container">
          <canvas ref={canvasRef} className="pdf-canvas" />
        </div>
      </div>
    </div>
  );
};

export default PDFViewer;