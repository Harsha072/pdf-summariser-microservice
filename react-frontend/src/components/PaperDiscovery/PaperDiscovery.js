import React, { useState } from 'react';
import './PaperDiscovery.css';

const PaperDiscovery = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [discoveredPapers, setDiscoveredPapers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSources, setSelectedSources] = useState(['arxiv', 'semantic_scholar']);
  const [maxResults, setMaxResults] = useState(10);
  const [error, setError] = useState('');

  const availableSources = [
    { id: 'arxiv', name: 'arXiv', description: 'Open access repository of scientific papers' },
    { id: 'semantic_scholar', name: 'Semantic Scholar', description: 'AI-powered research tool' },
    { id: 'google_scholar', name: 'Google Scholar', description: 'Web search for scholarly literature' }
  ];

  const handleSearchByQuery = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a research query');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:5000/api/discover-papers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          sources: selectedSources,
          max_results: maxResults
        })
      });

      const data = await response.json();

      if (data.success) {
        setDiscoveredPapers(data.papers);
      } else {
        setError(data.error || 'Failed to discover papers');
      }
    } catch (err) {
      setError('Failed to connect to the discovery engine');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please upload a PDF file');
      return;
    }

    setUploadedFile(file);
    setIsLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('sources', selectedSources.join(','));
      formData.append('max_results', maxResults.toString());

      const response = await fetch('http://localhost:5000/api/upload-paper', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.success) {
        setDiscoveredPapers(data.similar_papers.papers || []);
      } else {
        setError(data.error || 'Failed to analyze uploaded paper');
      }
    } catch (err) {
      setError('Failed to upload and analyze paper');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSourceToggle = (sourceId) => {
    setSelectedSources(prev => 
      prev.includes(sourceId) 
        ? prev.filter(id => id !== sourceId)
        : [...prev, sourceId]
    );
  };

  const downloadPaper = async (paperUrl, paperTitle) => {
    try {
      const response = await fetch('http://localhost:5000/api/download-paper', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: paperUrl })
      });

      if (response.ok) {
        // Open the paper URL in a new tab
        window.open(paperUrl, '_blank');
      } else {
        setError('Failed to download paper');
      }
    } catch (err) {
      setError('Failed to download paper');
    }
  };

  return (
    <div className="paper-discovery">
      <div className="discovery-header">
        <h1>🔬 Academic Paper Discovery Engine</h1>
        <p>Find relevant research papers using AI analysis and multi-source web scraping</p>
      </div>

      <div className="discovery-controls">
        <div className="search-section">
          <h3>Search by Research Query</h3>
          <div className="search-input-group">
            <textarea
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Enter your research question or topic (e.g., 'machine learning for climate change prediction')"
              rows={3}
              className="search-textarea"
            />
            <button 
              onClick={handleSearchByQuery}
              disabled={isLoading}
              className="search-button primary"
            >
              {isLoading ? 'Discovering...' : 'Discover Papers'}
            </button>
          </div>
        </div>

        <div className="upload-section">
          <h3>Upload Research Paper</h3>
          <div className="upload-input-group">
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileUpload}
              className="file-input"
              id="paper-upload"
            />
            <label htmlFor="paper-upload" className="file-label">
              {uploadedFile ? uploadedFile.name : 'Choose PDF file to find similar papers'}
            </label>
          </div>
        </div>

        <div className="options-section">
          <div className="sources-selection">
            <h4>Search Sources</h4>
            <div className="sources-grid">
              {availableSources.map(source => (
                <label key={source.id} className="source-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedSources.includes(source.id)}
                    onChange={() => handleSourceToggle(source.id)}
                  />
                  <span className="source-name">{source.name}</span>
                  <span className="source-description">{source.description}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="max-results">
            <label>
              Max Results:
              <select 
                value={maxResults} 
                onChange={(e) => setMaxResults(parseInt(e.target.value))}
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={15}>15</option>
                <option value={20}>20</option>
              </select>
            </label>
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {isLoading && (
        <div className="loading-section">
          <div className="spinner"></div>
          <p>Discovering relevant papers...</p>
        </div>
      )}

      {discoveredPapers.length > 0 && (
        <div className="results-section">
          <h3>📚 Discovered Papers ({discoveredPapers.length})</h3>
          <div className="papers-grid">
            {discoveredPapers.map((paper, index) => (
              <div key={paper.id || index} className="paper-card">
                <div className="paper-header">
                  <h4 className="paper-title">{paper.title}</h4>
                  <div className="paper-meta">
                    <span className="paper-source">{paper.source}</span>
                    {paper.relevance_score && (
                      <span className="relevance-score">
                        Relevance: {Math.round(paper.relevance_score)}%
                      </span>
                    )}
                  </div>
                </div>

                <div className="paper-authors">
                  <strong>Authors:</strong> {paper.authors?.join(', ') || 'Unknown'}
                </div>

                <div className="paper-summary">
                  {paper.summary && paper.summary.length > 300 
                    ? paper.summary.substring(0, 300) + '...'
                    : paper.summary || 'No summary available'
                  }
                </div>

                <div className="paper-details">
                  {paper.published && (
                    <span className="paper-date">Published: {paper.published}</span>
                  )}
                  {paper.citation_count && (
                    <span className="citation-count">Citations: {paper.citation_count}</span>
                  )}
                  {paper.journal && (
                    <span className="journal">Journal: {paper.journal}</span>
                  )}
                </div>

                <div className="paper-actions">
                  {paper.pdf_url && (
                    <button 
                      onClick={() => downloadPaper(paper.pdf_url, paper.title)}
                      className="action-button download"
                    >
                      📄 View PDF
                    </button>
                  )}
                  {paper.url && (
                    <button 
                      onClick={() => window.open(paper.url, '_blank')}
                      className="action-button external"
                    >
                      🔗 View Details
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PaperDiscovery;