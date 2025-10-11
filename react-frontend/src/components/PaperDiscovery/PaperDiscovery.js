import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCachedSearchResults, discoverPapers } from '../../services/api';
import { AuthButton, ProtectedFeature } from '../Auth/InlineAuth';
import { SmartPaperActions } from './ProtectedPaperFeatures';
import { useAuth } from '../../context/AuthContext';
import './PaperDiscovery.css';

const PaperDiscovery = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user, isAnonymous } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [discoveredPapers, setDiscoveredPapers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSources, setSelectedSources] = useState(['arxiv', 'semantic_scholar']);
  const [maxResults, setMaxResults] = useState(10);
  const [error, setError] = useState('');
  const [cacheStatus, setCacheStatus] = useState('');

  const availableSources = [
    { id: 'arxiv', name: 'arXiv', description: 'Open access repository of scientific papers' },
    { id: 'semantic_scholar', name: 'Semantic Scholar', description: 'AI-powered research tool' },
    { id: 'google_scholar', name: 'Google Scholar', description: 'Web search for scholarly literature' }
  ];

  // Check for cached results on page load
  useEffect(() => {
    const loadCachedResults = async () => {
      try {
        console.log("page reload")
        const cachedData = await getCachedSearchResults();
        if (cachedData.success && cachedData.has_cache) {
          if (cachedData.results && cachedData.results.length > 0) {
            // Load the most recent search results
            const mostRecent = cachedData.results[0];
            setSearchQuery(mostRecent.query || '');
            setDiscoveredPapers(mostRecent.results?.papers || []);
            setSelectedSources(mostRecent.sources || ['arxiv', 'semantic_scholar']);
            setMaxResults(mostRecent.max_results || 10);
            setCacheStatus(`Loaded cached results from ${new Date(mostRecent.timestamp).toLocaleTimeString()}`);
          } else if (cachedData.result) {
            // Single result format
            setSearchQuery(cachedData.query || '');
            setDiscoveredPapers(cachedData.result?.papers || []);
            setCacheStatus(`Loaded cached results from ${new Date(cachedData.result.timestamp).toLocaleTimeString()}`);
          }
        }
      } catch (error) {
        console.error('Failed to load cached results:', error);
      }
    };

    loadCachedResults();
  }, []);

  const handleViewDetails = (paper, index) => {
    // Store paper data in localStorage for the details page
    const paperId = `paper_${Date.now()}_${index}`;
    localStorage.setItem(`paper_${paperId}`, JSON.stringify(paper));
    
    // Navigate to details page
    navigate(`/paper-details/${paperId}`);
  };

  const handleSearchByQuery = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a research query');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const data = await discoverPapers(searchQuery, selectedSources, maxResults);

      if (data.success) {
        setDiscoveredPapers(data.papers);
        // Update cache status
        if (data.from_cache) {
          setCacheStatus(`Results loaded from cache (${new Date(data.cache_timestamp).toLocaleTimeString()})`);
        } else {
          setCacheStatus('Fresh results - now cached for future use');
        }
      } else {
        setError(data.error || 'Failed to discover papers');
        setCacheStatus('');
      }
    } catch (err) {
      setError('Failed to connect to the discovery engine');
      setCacheStatus('');
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
      {/* Authorization Status Banner */}
      {!isAuthenticated && (
        <div className="auth-status-banner">
          <div className="auth-banner-content">
            <div className="auth-banner-icon">ℹ️</div>
            <div className="auth-banner-text">
              <strong>Free Access:</strong> You can search and browse papers freely. 
              <span className="auth-banner-highlight"> Sign in to download papers and view detailed AI analysis.</span>
            </div>
          </div>
        </div>
      )}
      
      {isAuthenticated && (
        <div className="auth-status-banner authenticated">
          <div className="auth-banner-content">
            <div className="auth-banner-icon">✅</div>
            <div className="auth-banner-text">
              <strong>Welcome back, {user?.displayName || user?.email}!</strong> 
              You have full access to all features including downloads and detailed analysis.
            </div>
          </div>
        </div>
      )}
      
      <div className="discovery-controls">
        <div className="search-section">
          <div className="search-header">
            <h3>Discover Academic Papers</h3>
            <p className="search-subtitle">Search by research topic or upload your paper to find similar work</p>
          </div>
          
          <div className="search-input-group">
            <div className="textarea-container">
              <textarea
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Enter your research question or topic (e.g., 'machine learning for climate change prediction')"
                rows={3}
                className="search-textarea"
              />
              
              <div className="input-actions">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileUpload}
                  className="file-input"
                  id="paper-upload"
                />
                <label htmlFor="paper-upload" className="file-upload-btn" title="Upload PDF to find similar papers">
                  📎
                </label>
                
                {uploadedFile && (
                  <div className="uploaded-file-indicator">
                    <span className="file-name" title={uploadedFile.name}>
                      {uploadedFile.name.length > 20 ? uploadedFile.name.substring(0, 20) + '...' : uploadedFile.name}
                    </span>
                    <button 
                      onClick={() => setUploadedFile(null)} 
                      className="remove-file-btn-small"
                      title="Remove file"
                    >
                      ✕
                    </button>
                  </div>
                )}
              </div>
            </div>
            
            <button 
              onClick={handleSearchByQuery}
              disabled={isLoading}
              className="search-button primary"
            >
              {isLoading ? 'Discovering...' : 'Discover Papers'}
            </button>
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
                  <div className="source-content">
                    <span className="source-name">{source.name}</span>
                    <span className="source-description">{source.description}</span>
                  </div>
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
          <div className="results-header">
            <h3>📚 Discovered Papers ({discoveredPapers.length})</h3>
            {cacheStatus && (
              <div className="cache-status">
                <span className="cache-indicator">🔄 {cacheStatus}</span>
              </div>
            )}
          </div>
          
          {/* Authorization info for search results */}
          {!isAuthenticated && discoveredPapers.length > 0 && (
            <div className="results-auth-info">
              <div className="auth-info-content">
                <span className="auth-info-icon">🔓</span>
                <span className="auth-info-text">
                  You can browse all papers freely. Sign in to unlock downloads and detailed analysis.
                </span>
              </div>
            </div>
          )}
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

                <SmartPaperActions
                  paper={paper}
                  index={index}
                  onViewDetails={handleViewDetails}
                  onDownloadPaper={downloadPaper}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PaperDiscovery;