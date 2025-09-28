import React, { useEffect, useRef, useCallback, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
// Remove problematic CSS import that references missing SVGs
// import 'pdfjs-dist/web/pdf_viewer.css';
import './PDFViewer.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';

// Set worker source to match package version
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`;

// Custom TextLayerBuilder to avoid CSS import issues
class SimpleTextLayerBuilder {
  constructor({ textLayerDiv, pageIndex, viewport, textDivs, textContentItemsStr }) {
    this.textLayerDiv = textLayerDiv;
    this.pageIndex = pageIndex;
    this.viewport = viewport;
    this.textDivs = textDivs || [];
    this.textContentItemsStr = textContentItemsStr || [];
  }

  render(timeout) {
    const textLayerDiv = this.textLayerDiv;
    const textContent = this.textContentItemsStr;
    const viewport = this.viewport;

    if (!textContent || textContent.length === 0) {
      return;
    }

    // Clear existing content
    textLayerDiv.innerHTML = '';
    textLayerDiv.style.position = 'absolute';
    textLayerDiv.style.top = '0';
    textLayerDiv.style.left = '0';
    textLayerDiv.style.color = 'transparent';
    textLayerDiv.style.lineHeight = '1.0';
    textLayerDiv.style.overflow = 'hidden';
    textLayerDiv.style.pointerEvents = 'none';

    // Create text spans for each item
    textContent.items.forEach((item, index) => {
      const span = document.createElement('span');
      span.textContent = item.str;
      span.style.position = 'absolute';
      span.style.whiteSpace = 'pre';
      span.style.color = 'transparent';
      span.style.cursor = 'text';
      span.style.transformOrigin = '0 0';

      // Calculate position and transform
      const transform = viewport.transform;
      const tx = transform[4] + item.transform[4];
      const ty = transform[5] + item.transform[5];
      const rotation = Math.atan2(item.transform[1], item.transform[0]);
      
      span.style.left = `${tx}px`;
      span.style.top = `${ty}px`;
      span.style.fontSize = `${Math.sqrt(item.transform[0] * item.transform[0] + item.transform[1] * item.transform[1])}px`;
      
      if (rotation !== 0) {
        span.style.transform = `rotate(${rotation}rad)`;
      }

      // Store reference to the text item
      span.setAttribute('data-text-index', index);
      span.setAttribute('data-text-content', item.str);
      
      this.textDivs.push(span);
      textLayerDiv.appendChild(span);
    });
  }

  cancel() {
    // Cleanup if needed
  }
}

const PDFViewer = () => {
  const { document: pdfDocument, updateDocument, clearDocument } = useDocument();
  const { showError, showInfo } = useNotification();
  const canvasRef = useRef(null);
  const textLayerRef = useRef(null);
  const pdfDocRef = useRef(null);
  const [textContent, setTextContent] = useState(null);
  const [currentHighlight, setCurrentHighlight] = useState(null);
  const [textLayer, setTextLayer] = useState(null);

  // Load PDF when pdfData changes
  useEffect(() => {
    if (pdfDocument.pdfData) {
      loadPDF(pdfDocument.pdfData);
    }
  }, [pdfDocument.pdfData]);

  // Render page when currentPage or zoom changes
  useEffect(() => {
    if (pdfDocRef.current && pdfDocument.currentPage) {
      renderPage(pdfDocument.currentPage);
    }
  }, [pdfDocument.currentPage, pdfDocument.zoom]);

  // Listen for highlight events from ChatBot
  useEffect(() => {
    const handleHighlight = async (event) => {
      const { 
        page, 
        searchTerm, 
        searchTerms, 
        exactMatch, 
        highlightInfo, 
        chunkText,
        highlightText 
      } = event.detail;
      
      // Handle both old and new formats
      const termToHighlight = searchTerm || 
                             (searchTerms && searchTerms[0]) || 
                             highlightText || 
                             'text';
      
      console.log('🎯 Received highlight request:', {
        page,
        termToHighlight,
        exactMatch,
        currentPage: pdfDocument.currentPage
      });
      
      if (page && pdfDocRef.current && page <= pdfDocument.totalPages) {
        // Navigate to the page first if different
        if (pdfDocument.currentPage !== page) {
          console.log(`📄 Navigating to page ${page}`);
          updateDocument({ currentPage: page });
          
          // Wait for page to render before highlighting
          setTimeout(() => {
            highlightTextInLayer(termToHighlight, exactMatch, highlightInfo);
          }, 1000); // Give more time for page to render
        } else {
          // Same page, highlight immediately
          highlightTextInLayer(termToHighlight, exactMatch, highlightInfo);
        }
      }
    };

    window.addEventListener('highlightInPDF', handleHighlight);
    return () => window.removeEventListener('highlightInPDF', handleHighlight);
  }, [pdfDocument.currentPage, pdfDocument.totalPages, updateDocument]);

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
      const textLayerDiv = textLayerRef.current;

      const viewport = page.getViewport({ scale: pdfDocument.zoom });
      canvas.height = viewport.height;
      canvas.width = viewport.width;

      // Clear and setup text layer
      if (textLayerDiv) {
        textLayerDiv.innerHTML = '';
        textLayerDiv.style.width = `${viewport.width}px`;
        textLayerDiv.style.height = `${viewport.height}px`;
      }

      const renderContext = {
        canvasContext: context,
        viewport: viewport
      };

      // Render the PDF page
      await page.render(renderContext).promise;
      console.log(`✅ Rendered page ${pageNum}`);
      
      // Build text layer for highlighting
      if (textLayerDiv) {
        const pageTextContent = await page.getTextContent();
        console.log(`📝 Extracted ${pageTextContent.items.length} text items from page ${pageNum}`);
        setTextContent(pageTextContent);
        
        // Create text layer spans
        pageTextContent.items.forEach((textItem, index) => {
          const tx = pdfjsLib.Util.transform(
            pdfjsLib.Util.transform(viewport.transform, textItem.transform),
            [1, 0, 0, -1, 0, 0]
          );
          
          const span = document.createElement('span');
          span.textContent = textItem.str;
          span.setAttribute('role', 'presentation');
          span.style.position = 'absolute';
          span.style.left = `${tx[4]}px`;
          span.style.top = `${tx[5]}px`;
          span.style.fontSize = `${Math.abs(tx[0])}px`;
          span.style.fontFamily = textItem.fontName || 'sans-serif';
          span.style.color = 'transparent';
          span.style.whiteSpace = 'pre';
          span.style.pointerEvents = 'none';
          
          textLayerDiv.appendChild(span);
        });
        
        console.log(`🏗️ Built text layer for page ${pageNum}`);
      }
    } catch (error) {
      console.error('Error rendering page:', error);
      showError('Error rendering PDF page');
    }
  };

  // Enhanced text highlighting using text layer
  const highlightTextInLayer = (searchTerm, exactMatch = null, highlightInfo = null) => {
    console.log('🔍 Starting highlight search for:', searchTerm);
    
    // Safety check: ensure searchTerm is valid
    if (!searchTerm || typeof searchTerm !== 'string' || searchTerm.trim() === '') {
      console.log('❌ Invalid search term:', searchTerm);
      return;
    }
    
    const textLayerDiv = textLayerRef.current;
    if (!textLayerDiv) {
      console.log('❌ No text layer found');
      showFallbackHighlight(searchTerm);
      return;
    }

    // Clear previous highlights
    clearHighlights();

    // Strategy 1: Use the exact match from backend if available
    let searchTerms = [searchTerm.trim()];
    if (exactMatch && exactMatch !== searchTerm && typeof exactMatch === 'string') {
      searchTerms.unshift(exactMatch.trim()); // Try exact match first
    }

    let found = false;

    for (const term of searchTerms) {
      // Additional safety check for each term
      if (!term || typeof term !== 'string' || term.trim() === '') {
        console.log('⚠️ Skipping invalid term:', term);
        continue;
      }
      
      console.log('🔍 Trying to highlight:', term);
      
      // Get all text spans from the text layer
      const textSpans = textLayerDiv.querySelectorAll('span[role="presentation"]');
      console.log(`📝 Found ${textSpans.length} text spans in layer`);
      
      let matchCount = 0;
      
      textSpans.forEach((span, index) => {
        const spanText = span.textContent || '';
        const lowerSpanText = spanText.toLowerCase();
        const lowerSearchTerm = term.toLowerCase();
        
        // Check if this span contains our search term
        if (lowerSpanText.includes(lowerSearchTerm)) {
          console.log(`✅ Found match in span ${index}: "${spanText}"`);
          
          // Create highlight overlay
          const highlight = document.createElement('div');
          highlight.className = 'pdf-search-highlight';
          highlight.style.cssText = `
            position: absolute;
            left: ${span.offsetLeft}px;
            top: ${span.offsetTop}px;
            width: ${span.offsetWidth}px;
            height: ${span.offsetHeight}px;
            background-color: rgba(255, 255, 0, 0.6);
            border: 2px solid rgba(255, 193, 7, 0.8);
            border-radius: 3px;
            pointer-events: none;
            z-index: 100;
            animation: highlightPulse 2s ease-in-out;
            box-shadow: 0 0 10px rgba(255, 255, 0, 0.5);
          `;
          
          textLayerDiv.appendChild(highlight);
          matchCount++;
          found = true;
          
          // Scroll to first match
          if (matchCount === 1) {
            span.scrollIntoView({ 
              behavior: 'smooth', 
              block: 'center',
              inline: 'center'
            });
          }
        }
      });
      
      if (matchCount > 0) {
        console.log(`🎉 Successfully highlighted ${matchCount} instances of "${term}"`);
        showSuccessNotification(term, matchCount, pdfDocument.currentPage);
        break; // Stop trying other search terms if we found matches
      }
    }

    if (!found) {
      console.log('❌ No matches found in text layer, trying paragraph matching');
      tryParagraphMatching(searchTerm, highlightInfo);
    }
  };

  // Try to match based on paragraph context
  const tryParagraphMatching = (searchTerm, highlightInfo) => {
    const textLayerDiv = textLayerRef.current;
    if (!textLayerDiv || !highlightInfo?.containing_paragraph) {
      showFallbackHighlight(searchTerm);
      return;
    }

    const paragraphText = highlightInfo.containing_paragraph.toLowerCase();
    const textSpans = textLayerDiv.querySelectorAll('span[role="presentation"]');
    
    // Get first few words from paragraph for matching
    const paragraphWords = paragraphText.split(' ').slice(0, 5);
    
    let found = false;
    let matchingSpans = [];
    
    // Look for spans that contain words from the target paragraph
    textSpans.forEach(span => {
      const spanText = (span.textContent || '').toLowerCase();
      const matchCount = paragraphWords.filter(word => 
        word.length > 3 && spanText.includes(word)
      ).length;
      
      if (matchCount >= 2) { // At least 2 words match
        matchingSpans.push(span);
      }
    });
    
    if (matchingSpans.length > 0) {
      console.log(`📍 Found ${matchingSpans.length} spans matching paragraph context`);
      
      // Highlight the matching spans
      matchingSpans.forEach(span => {
        const highlight = document.createElement('div');
        highlight.className = 'pdf-context-highlight';
        highlight.style.cssText = `
          position: absolute;
          left: ${span.offsetLeft}px;
          top: ${span.offsetTop}px;
          width: ${span.offsetWidth}px;
          height: ${span.offsetHeight}px;
          background-color: rgba(0, 255, 0, 0.3);
          border: 1px solid rgba(0, 200, 0, 0.6);
          border-radius: 2px;
          pointer-events: none;
          z-index: 99;
        `;
        
        textLayerDiv.appendChild(highlight);
      });
      
      // Scroll to first match
      matchingSpans[0].scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
      });
      
      showContextNotification(searchTerm, matchingSpans.length, pdfDocument.currentPage);
      found = true;
    }

    if (!found) {
      showFallbackHighlight(searchTerm);
    }
  };

  // Clear all existing highlights
  const clearHighlights = () => {
    const textLayerDiv = textLayerRef.current;
    if (textLayerDiv) {
      const highlights = textLayerDiv.querySelectorAll('.pdf-search-highlight, .pdf-context-highlight');
      highlights.forEach(h => h.remove());
    }
  };

  // Show success notification
  const showSuccessNotification = (term, count, page) => {
    const notification = document.createElement('div');
    notification.className = 'highlight-success-notification';
    notification.innerHTML = `
      <div class="notification-content">
        <i class="fas fa-check-circle"></i>
        <div>
          <strong>Found & Highlighted!</strong>
          <div>"${term}" - ${count} matches on page ${page}</div>
        </div>
      </div>
    `;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: linear-gradient(135deg, #10b981, #059669);
      color: white;
      padding: 16px;
      border-radius: 12px;
      font-weight: 500;
      box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);
      z-index: 1000;
      animation: slideInSuccess 0.5s ease, fadeOutSuccess 0.5s ease 4s;
      min-width: 300px;
      pointer-events: none;
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
    }, 4500);
  };

  // Show context match notification
  const showContextNotification = (term, count, page) => {
    const notification = document.createElement('div');
    notification.innerHTML = `
      <div class="notification-content">
        <i class="fas fa-search"></i>
        <div>
          <strong>Context Found!</strong>
          <div>"${term}" found in ${count} text sections on page ${page}</div>
        </div>
      </div>
    `;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: linear-gradient(135deg, #3b82f6, #1d4ed8);
      color: white;
      padding: 16px;
      border-radius: 12px;
      font-weight: 500;
      box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3);
      z-index: 1000;
      animation: slideInSuccess 0.5s ease, fadeOutSuccess 0.5s ease 4s;
      min-width: 300px;
      pointer-events: none;
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
    }, 4500);
  };

  // Show fallback notification
  const showFallbackHighlight = (term) => {
    const notification = document.createElement('div');
    notification.innerHTML = `
      <div class="notification-content">
        <i class="fas fa-exclamation-triangle"></i>
        <div>
          <strong>Term Located!</strong>
          <div>"${term}" is on this page but exact highlighting unavailable</div>
        </div>
      </div>
    `;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: linear-gradient(135deg, #f59e0b, #d97706);
      color: white;
      padding: 16px;
      border-radius: 12px;
      font-weight: 500;
      box-shadow: 0 8px 25px rgba(245, 158, 11, 0.3);
      z-index: 1000;
      animation: slideInSuccess 0.5s ease, fadeOutSuccess 0.5s ease 4s;
      min-width: 300px;
      pointer-events: none;
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
    }, 4500);
  };

  const previousPage = useCallback(() => {
    if (pdfDocument.currentPage > 1) {
      updateDocument({ currentPage: pdfDocument.currentPage - 1 });
    }
  }, [pdfDocument.currentPage, updateDocument]);

  const nextPage = useCallback(() => {
    if (pdfDocument.currentPage < pdfDocument.totalPages) {
      updateDocument({ currentPage: pdfDocument.currentPage + 1 });
    }
  }, [pdfDocument.currentPage, pdfDocument.totalPages, updateDocument]);

  const goToPage = useCallback((pageNum) => {
    const page = parseInt(pageNum);
    if (page >= 1 && page <= pdfDocument.totalPages) {
      updateDocument({ currentPage: page });
    }
  }, [pdfDocument.totalPages, updateDocument]);

  const zoomIn = useCallback(() => {
    updateDocument({ zoom: Math.min(pdfDocument.zoom * 1.2, 3) });
  }, [pdfDocument.zoom, updateDocument]);

  const zoomOut = useCallback(() => {
    updateDocument({ zoom: Math.max(pdfDocument.zoom / 1.2, 0.5) });
  }, [pdfDocument.zoom, updateDocument]);

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
          <div 
            ref={textLayerRef} 
            className="textLayer"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              color: 'transparent',
              lineHeight: 1.0,
              overflow: 'hidden'
            }}
          ></div>
        </div>
      </div>
    </div>
  );
};

export default PDFViewer;