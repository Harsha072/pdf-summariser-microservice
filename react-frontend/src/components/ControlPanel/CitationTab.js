import React, { useState, useCallback } from 'react';
import './CitationTab.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';
import { extractCitations, exportCitations } from '../../services/api';
import LoadingSpinner from '../common/LoadingSpinner';
import CopyButton from '../common/CopyButton';

const CitationTab = () => {
  const { document } = useDocument();
  const { showError, showSuccess } = useNotification();
  
  const [citations, setCitations] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState('apa');
  const [exportedCitations, setExportedCitations] = useState('');

  const handleExtractCitations = useCallback(async () => {
    if (!document.id) {
      showError('Please upload a document first');
      return;
    }

    try {
      setExtracting(true);
      const result = await extractCitations(document.id);
      
      setCitations(result.citations);
      showSuccess(`Successfully extracted ${result.total_count} citations!`);
      
    } catch (error) {
      console.error('Error extracting citations:', error);
      showError('Failed to extract citations: ' + error.message);
    } finally {
      setExtracting(false);
    }
  }, [document.id, showError, showSuccess]);

  const handleExportCitations = useCallback(async () => {
    if (!citations.length) {
      showError('No citations to export. Please extract citations first.');
      return;
    }

    try {
      setExporting(true);
      const result = await exportCitations(document.id, selectedFormat, citations);
      
      setExportedCitations(result.formatted_citations.join('\n\n'));
      showSuccess(`Citations exported in ${result.format} format!`);
      
    } catch (error) {
      console.error('Error exporting citations:', error);
      showError('Failed to export citations: ' + error.message);
    } finally {
      setExporting(false);
    }
  }, [document.id, selectedFormat, citations, showError, showSuccess]);

  const downloadCitations = useCallback(() => {
    if (!exportedCitations) return;

    const blob = new Blob([exportedCitations], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `citations_${selectedFormat}_${document.metadata?.title || 'document'}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showSuccess('Citations downloaded successfully!');
  }, [exportedCitations, selectedFormat, document.metadata, showSuccess]);

  return (
    <div className="citation-tab">
      <div className="citation-header">
        <h3>
          <i className="fas fa-quote-right"></i>
          Citation Extractor for Masters Students
        </h3>
        <p>Extract academic citations from your research papers and export them in standard formats (APA, MLA, Harvard, BibTeX)</p>
      </div>

      <div className="citation-controls">
        <button 
          className="btn btn-primary"
          onClick={handleExtractCitations}
          disabled={!document.id || extracting}
        >
          <i className="fas fa-search"></i>
          {extracting ? 'Extracting Citations...' : 'Extract Citations'}
        </button>

        {citations.length > 0 && (
          <div className="export-section">
            <div className="format-selector">
              <label htmlFor="formatSelect">Export Format:</label>
              <select 
                id="formatSelect"
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
              >
                <option value="apa">APA Style</option>
                <option value="mla">MLA Style</option>
                <option value="harvard">Harvard Style</option>
                <option value="bibtex">BibTeX</option>
              </select>
            </div>

            <button 
              className="btn btn-secondary"
              onClick={handleExportCitations}
              disabled={exporting}
            >
              <i className="fas fa-file-export"></i>
              {exporting ? 'Exporting...' : 'Export Citations'}
            </button>
          </div>
        )}
      </div>

      <div className="citation-results">
        {extracting && (
          <div className="loading-container">
            <LoadingSpinner />
            <p>Scanning document for academic citations...</p>
          </div>
        )}

        {citations.length > 0 && !extracting && (
          <div className="citations-list">
            <div className="citations-header">
              <h4>Found {citations.length} Citations</h4>
              <small>These citations were automatically detected in your document</small>
            </div>
            
            <div className="citations-grid">
              {citations.map((citation, index) => (
                <div key={index} className="citation-card">
                  <div className="citation-type">
                    <span className={`type-badge ${citation.type}`}>
                      {citation.type.replace('_', ' ').toUpperCase()}
                    </span>
                    <span className="format-detected">
                      {citation.format_detected}
                    </span>
                  </div>
                  
                  <div className="citation-content">
                    {citation.authors && (
                      <div className="citation-authors">
                        <strong>Authors:</strong> {citation.authors.join(', ')}
                      </div>
                    )}
                    
                    {citation.year && (
                      <div className="citation-year">
                        <strong>Year:</strong> {citation.year}
                      </div>
                    )}
                    
                    {citation.title && (
                      <div className="citation-title">
                        <strong>Title:</strong> {citation.title}
                      </div>
                    )}
                    
                    {citation.journal && (
                      <div className="citation-journal">
                        <strong>Journal:</strong> {citation.journal}
                        {citation.volume && ` Vol. ${citation.volume}`}
                        {citation.issue && ` (${citation.issue})`}
                        {citation.pages && `, pp. ${citation.pages}`}
                      </div>
                    )}
                    
                    {citation.doi && (
                      <div className="citation-doi">
                        <strong>DOI:</strong> {citation.doi}
                      </div>
                    )}
                    
                    {citation.url && (
                      <div className="citation-url">
                        <strong>URL:</strong> 
                        <a href={citation.url} target="_blank" rel="noopener noreferrer">
                          {citation.url.length > 50 ? citation.url.substring(0, 50) + '...' : citation.url}
                        </a>
                      </div>
                    )}
                    
                    <div className="citation-location">
                      <i className="fas fa-map-marker-alt"></i>
                      Page {citation.page} • {citation.section}
                    </div>
                  </div>
                  
                  <div className="citation-raw">
                    <details>
                      <summary>Raw Text</summary>
                      <code>{citation.raw_text}</code>
                    </details>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {exportedCitations && (
          <div className="exported-citations">
            <div className="export-header">
              <h4>Exported Citations ({selectedFormat.toUpperCase()})</h4>
              <div className="export-actions">
                <CopyButton content={exportedCitations} />
                <button 
                  className="btn btn-success btn-small"
                  onClick={downloadCitations}
                >
                  <i className="fas fa-download"></i>
                  Download
                </button>
              </div>
            </div>
            
            <div className="citations-text">
              <pre>{exportedCitations}</pre>
            </div>
          </div>
        )}

        {!extracting && citations.length === 0 && !exportedCitations && (
          <div className="placeholder-text">
            <i className="fas fa-graduation-cap"></i>
            <h3>Ready to extract citations!</h3>
            <p>Upload your research paper and click "Extract Citations" to automatically find and format academic references.</p>
            
            <div className="features-list">
              <h4>What this tool can extract:</h4>
              <ul>
                <li><i className="fas fa-check"></i> Author names and publication years</li>
                <li><i className="fas fa-check"></i> Journal articles with volume/issue numbers</li>
                <li><i className="fas fa-check"></i> DOI links and URLs</li>
                <li><i className="fas fa-check"></i> Book references and conference papers</li>
                <li><i className="fas fa-check"></i> Multiple citation formats (APA, MLA, Harvard, BibTeX)</li>
              </ul>
            </div>
            
            <div className="benefits">
              <h4>Perfect for Masters students:</h4>
              <ul>
                <li>Save hours of manual citation formatting</li>
                <li>Ensure consistent referencing style</li>
                <li>Export directly to your thesis or assignment</li>
                <li>Identify all sources used in literature reviews</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CitationTab;