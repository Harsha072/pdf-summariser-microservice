import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getCachedSearchResults, discoverPapers, getCurrentSessionId } from '../../services/api';
// import { AuthButton, ProtectedFeature } from '../Auth/InlineAuth'; // Currently unused
// import { SmartPaperActions } from './ProtectedPaperFeatures'; // Currently unused
import { useAuth } from '../../context/AuthContext';
import PaperCard from '../PaperCard/PaperCard';
import './PaperDiscovery.css';

// Helper function to format authors list (currently unused but kept for future use)
// const formatAuthors = (authors, maxAuthors = 3) => {
//   if (!authors || authors.length === 0) return 'Unknown';
//   
//   if (authors.length <= maxAuthors) {
//     return authors.join(', ');
//   }
//   
//   const displayedAuthors = authors.slice(0, maxAuthors).join(', ');
//   const remainingCount = authors.length - maxAuthors;
//   return `${displayedAuthors} +${remainingCount} more`;
// };

const PaperDiscovery = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, refreshToken } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [discoveredPapers, setDiscoveredPapers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSources, setSelectedSources] = useState(['openalex']);
  const [maxResults, setMaxResults] = useState(10);
  const [error, setError] = useState('');
  const [cacheStatus, setCacheStatus] = useState('');
  const [bookmarkStatus, setBookmarkStatus] = useState({}); // Track bookmark status for papers
  const [buildingGraphFor, setBuildingGraphFor] = useState(null); // Track which paper is building graph

  const availableSources = [
    { id: 'openalex', name: 'OpenAlex', description: 'Open catalog of scholarly papers with comprehensive metadata' },
    { id: 'google_scholar', name: 'Google Scholar', description: 'Web search for scholarly literature' }
  ];

  const exampleQueries = [
    "How can machine learning improve medical diagnosis accuracy?",
    "What are the latest developments in quantum computing for cryptography?",
    "How does climate change affect biodiversity in marine ecosystems?",
    "What is the impact of artificial intelligence on cybersecurity?",
    "How can renewable energy systems be optimized for efficiency?"
  ];

  // Handle URL parameters for search from history
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const queryParam = urlParams.get('q');
    const sourcesParam = urlParams.get('sources');
    const fromParam = urlParams.get('from');
    
    if (queryParam && fromParam === 'history') {
      console.log('Repeating search from history:', queryParam);
      setSearchQuery(queryParam);
      
      if (sourcesParam) {
        const sources = sourcesParam.split(',');
        setSelectedSources(sources);
      }
      
      // Load cached results for this query instead of making a new search
      loadCachedResultsForQuery(queryParam);
      
      // Clear URL parameters
      navigate('/search', { replace: true });
    }
  }, [location.search, navigate]);

  // Load cached results for a specific query
  const loadCachedResultsForQuery = async (query) => {
    try {
      console.log("Loading cached results for query:", query);
      const cachedData = await getCachedSearchResults();
      console.log("Cached data response:", cachedData);
      
      if (cachedData.success && cachedData.has_cache && cachedData.results) {
        // Find the cached result matching this query
        const matchingResult = cachedData.results.find(
          result => result.query.toLowerCase() === query.toLowerCase()
        );
        
        if (matchingResult) {
          console.log("Found matching cached result");
          setDiscoveredPapers(matchingResult.results?.papers || []);
          setSelectedSources(matchingResult.sources || ['openalex']);
          setMaxResults(matchingResult.max_results || 10);
          setCacheStatus(`Loaded from cache (${new Date(matchingResult.timestamp).toLocaleTimeString()})`);
        } else {
          console.log("No matching cache found, will need to search");
          setCacheStatus('No cached results found for this query');
        }
      }
    } catch (error) {
      console.error('Failed to load cached results for query:', error);
    }
  };

  // Check for cached results on page load
  useEffect(() => {
    const loadCachedResults = async () => {
      try {
        console.log("PaperDiscovery: Loading cached results on page load...");
        console.log("PaperDiscovery: Current session ID:", getCurrentSessionId());
        
        const cachedData = await getCachedSearchResults();
        console.log("PaperDiscovery: Cached data response:", cachedData);
        
        if (cachedData.success && cachedData.has_cache) {
          if (cachedData.results && cachedData.results.length > 0) {
            // Load the most recent search results
            const mostRecent = cachedData.results[0];
            console.log("PaperDiscovery: Loading most recent cached result");
            console.log("PaperDiscovery: Query:", mostRecent.query);
            console.log("PaperDiscovery: Papers count:", mostRecent.results?.papers?.length || 0);
            
            setSearchQuery(mostRecent.query || '');
            setDiscoveredPapers(mostRecent.results?.papers || []);
            setSelectedSources(mostRecent.sources || ['openalex']);
            setMaxResults(mostRecent.max_results || 10);
            setCacheStatus(`Loaded cached results from ${new Date(mostRecent.timestamp).toLocaleTimeString()}`);
          } else if (cachedData.result) {
            // Single result format
            console.log("PaperDiscovery: Loading single cached result");
            console.log("PaperDiscovery: Papers count:", cachedData.result?.papers?.length || 0);
            
            setSearchQuery(cachedData.query || '');
            setDiscoveredPapers(cachedData.result?.papers || []);
            setCacheStatus(`Loaded cached results from ${new Date(cachedData.result.timestamp).toLocaleTimeString()}`);
          }
        } else {
          console.log("PaperDiscovery: No cached results found");
        }
      } catch (error) {
        console.error('PaperDiscovery: Failed to load cached results:', error);
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

  const handleBuildGraph = async (paper) => {
    console.log('handleBuildGraph called with paper:', paper);
    
    // Use OpenAlex work ID if available, otherwise fall back to existing logic
    let paperId = paper.openalex_work_id || paper.paper_id || paper.id;
    console.log('Initial paperId:', paperId);
    
    // If we still don't have a work ID but have a URL, try to extract it
    if (!paperId && paper.url && paper.url.includes('openalex.org/W')) {
      paperId = paper.url.split('/W')[1] || paper.url.split('W')[1];
      if (paperId.startsWith('W')) {
        paperId = paperId; // Keep the W prefix for OpenAlex IDs
      } else {
        paperId = 'W' + paperId; // Add W prefix if missing
      }
      console.log('Extracted paperId from URL:', paperId);
    }
    
    // Legacy fallback for other ID formats
    if (!paperId) {
      paperId = paper.paper_id || paper.id;
      if (paperId && paperId.includes('openalex.org/W')) {
        paperId = paperId.split('/W')[1] || paperId.split('W')[1];
      } else if (paperId && paperId.startsWith('W')) {
        paperId = paperId; // Keep as is for OpenAlex work IDs
      }
      console.log('Fallback paperId:', paperId);
    }
    
    if (!paperId) {
      console.error('No paper ID found!');
      alert('Unable to build graph: Paper ID not found');
      return;
    }
    
    console.log('Building network graph for paper:', paperId, paper.title);
    console.log('Using OpenAlex work ID:', paper.openalex_work_id || 'Not available');
    
    try {
      // Show loading state for this specific paper
      setBuildingGraphFor(paper.paper_id || paperId);
      setError('');
      
      // Call the backend API to build the graph
      const headers = {
        'Content-Type': 'application/json'
      };
      
      // Add authorization header if user is authenticated
      if (user && refreshToken) {
        try {
          const token = await refreshToken();
          if (token) {
            headers['Authorization'] = `Bearer ${token}`;
            console.log('Firebase token obtained successfully');
          }
        } catch (tokenError) {
          console.warn('Failed to get user token:', tokenError);
          // Continue without token
        }
      }
      
      const apiUrl = `http://localhost:5000/api/paper-relationships/${encodeURIComponent(paperId)}?max_connections=10`;
      console.log('Calling API:', apiUrl);
      
      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: headers
      });
      
      console.log('API Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const graphData = await response.json();
      console.log('Graph data received:', graphData);
      
      if (graphData.success) {
        console.log('Graph built successfully, navigating to /paper-relationships');
        
        // Navigate to the SimplePaperRelationships page with the graph data
        navigate(`/paper-relationships?ts=${Date.now()}`, { 
          state: { 
            paperId: paperId,
            paperTitle: paper.title,
            fromDiscovery: true,
            openalexWorkId: paper.openalex_work_id,
            graphData: graphData // Pass the pre-fetched graph data
          } 
        });
      } else {
        console.error('Graph build failed:', graphData.error);
        throw new Error(graphData.error || 'Failed to build graph');
      }
      
    } catch (error) {
      console.error('Error building graph:', error);
      setError(`Failed to build graph: ${error.message}`);
      
      // Still navigate to the page but without pre-fetched data
      // The SimplePaperRelationships component will handle the API call
      console.log('Navigating to /paper-relationships with error state');
      navigate(`/paper-relationships?ts=${Date.now()}`, { 
        state: { 
          paperId: paperId,
          paperTitle: paper.title,
          fromDiscovery: true,
          openalexWorkId: paper.openalex_work_id,
          error: error.message
        } 
      });
    } finally {
      setBuildingGraphFor(null);
    }
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

  // BOOKMARK FUNCTIONS
  const toggleBookmark = async (paper) => {
    try {
      const paperId = paper.paper_id;
      const isCurrentlyBookmarked = bookmarkStatus[paperId] || paper.is_bookmarked;
      
      const endpoint = isCurrentlyBookmarked ? '/api/bookmarks/remove' : '/api/bookmarks/save';
      const payload = isCurrentlyBookmarked 
        ? { paper_id: paperId }
        : { paper: paper };

      const headers = {
        'Content-Type': 'application/json',
        'X-Session-ID': getCurrentSessionId()
      };

      // Add authorization header if user is authenticated
      if (user && refreshToken) {
        try {
          const token = await refreshToken();
          if (token) {
            headers['Authorization'] = `Bearer ${token}`;
          }
        } catch (tokenError) {
          console.warn('Failed to get user token:', tokenError);
        }
      }

      const response = await fetch(`http://localhost:5000${endpoint}`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      
      if (data.success) {
        // Update bookmark status locally
        setBookmarkStatus(prev => ({
          ...prev,
          [paperId]: !isCurrentlyBookmarked
        }));
        
        // Update the paper's bookmark status in the discoveredPapers array
        setDiscoveredPapers(prev => 
          prev.map(p => 
            p.paper_id === paperId 
              ? { ...p, is_bookmarked: !isCurrentlyBookmarked }
              : p
          )
        );
      } else {
        setError(data.error || 'Failed to toggle bookmark');
      }
    } catch (err) {
      console.error('Error toggling bookmark:', err);
      setError('Failed to toggle bookmark');
    }
  };

  return (
    <div className="paper-discovery">
      <div className="discovery-controls">

        <div className="options-section">
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
            <h3>Discovered Papers ({discoveredPapers.length})</h3>
            <div className="results-actions">
              {cacheStatus && (
                <div className="cache-status">
                  <span className="cache-indicator">{cacheStatus}</span>
                </div>
              )}
              <button
                onClick={() => navigate(`/paper-relationships?ts=${Date.now()}`, { 
                  state: { papers: discoveredPapers.slice(0, 5) } 
                })}
                className="citation-network-btn"
                disabled={discoveredPapers.length === 0}
                title="Explore paper relationships with discovered papers"
              >
                <i className="fas fa-project-diagram"></i>
                Explore Paper Network
              </button>
            </div>
          </div>
          
          {/* Authorization info for search results */}
          {!isAuthenticated && discoveredPapers.length > 0 && (
            <div className="results-auth-info">
              <div className="auth-info-content">
                <span className="auth-info-icon">i</span>
                <span className="auth-info-text">
                  You can browse all papers freely. Sign in to unlock downloads and detailed analysis.
                </span>
              </div>
            </div>
          )}
          <div className="papers-grid">
            {discoveredPapers.map((paper, index) => (
              <PaperCard
                key={paper.id || index}
                paper={paper}
                index={index}
                isBookmarked={bookmarkStatus[paper.paper_id] || paper.is_bookmarked}
                onToggleBookmark={toggleBookmark}
                onViewDetails={handleViewDetails}
                onDownloadPaper={downloadPaper}
                onBuildGraph={handleBuildGraph}
                isBuildingGraph={buildingGraphFor === (paper.paper_id || paper.id)}
                showActions={true}
                showRelevanceScore={true}
              />
            ))}
          </div>
        </div>
      )}

      {/* No results message */}
      {searchQuery && !isLoading && discoveredPapers.length === 0 && !error && (
        <div className="no-results-section">
          <div className="no-results-content">
            <div className="no-results-icon">!</div>
            <h3>No Papers Found</h3>
            <p>We couldn't find any papers matching your research question.</p>
            <div className="no-results-suggestions">
              <h4>Try these suggestions:</h4>
              <ul>
                <li>Use broader or different keywords</li>
                <li>Check spelling of technical terms</li>
                <li>Try rephrasing your research question</li>
                <li>The academic databases might be temporarily unavailable - try again in a few minutes</li>
              </ul>
            </div>
            <div className="no-results-examples">
              <p>Or try one of these example searches:</p>
              <div className="example-queries">
                {exampleQueries.map((example, index) => (
                  <button
                    key={index}
                    className="example-button"
                    onClick={() => setSearchQuery(example)}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaperDiscovery;