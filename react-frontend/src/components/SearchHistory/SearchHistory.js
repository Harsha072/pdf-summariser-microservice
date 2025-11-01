import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getUserSearchHistory, getSessionSearchHistory, clearUserSearchHistory, clearSessionSearchHistory } from '../../services/api';
import './SearchHistory.css';

const SearchHistory = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSearchHistory();
  }, [isAuthenticated]);

  const loadSearchHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      
      let response;
      if (isAuthenticated) {
        // Get user search history
        response = await getUserSearchHistory(20);
      } else {
        // Get session search history
        const sessionId = localStorage.getItem('paper_discovery_session_id');
        if (sessionId) {
          response = await getSessionSearchHistory(sessionId, 20);
        } else {
          setHistory([]);
          setLoading(false);
          return;
        }
      }
      
      if (response.success) {
        setHistory(response.history || []);
      } else {
        setError('Failed to load search history');
      }
    } catch (err) {
      setError('Error loading search history: ' + err.message);
      console.error('Search history error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRepeatSearch = async (searchItem) => {
    try {
      // Navigate to the search/discovery page with the search query
      // The PaperDiscovery component will load cached results for this query
      const searchParams = new URLSearchParams({
        q: searchItem.query,
        sources: searchItem.sources.join(','),
        from: 'history'
      });
      
      navigate(`/search?${searchParams.toString()}`);
    } catch (err) {
      console.error('Error repeating search:', err);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear your entire search history?')) {
      return;
    }
    
    try {
      let response;
      if (isAuthenticated) {
        response = await clearUserSearchHistory();
      } else {
        const sessionId = localStorage.getItem('paper_discovery_session_id');
        response = await clearSessionSearchHistory(sessionId);
      }
      
      if (response.success) {
        setHistory([]);
      }
    } catch (err) {
      console.error('Error clearing history:', err);
    }
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatSources = (sources) => {
    const sourceNames = {
      'openalex': 'OpenAlex',
      'semantic_scholar': 'Semantic Scholar',
      'google_scholar': 'Google Scholar'
    };
    return sources.map(source => sourceNames[source] || source).join(', ');
  };

  if (loading) {
    return (
      <div className="search-history">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading search history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="search-history">
      <div className="history-header">
        <div className="header-content">
          <h2>
            <span className="icon"></span>
            Search History
          </h2>
          <p className="subtitle">
            {isAuthenticated 
              ? `Your research journey - ${history.length} searches saved`
              : `Session history - ${history.length} recent searches`
            }
          </p>
        </div>
        
        {history.length > 0 && (
          <button 
            onClick={handleClearHistory} 
            className="clear-all-btn"
            title="Clear all history"
          >
            Clear All
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          <span className="error-icon"></span>
          {error}
        </div>
      )}

      {!isAuthenticated && (
        <div className="auth-notice">
          <div className="notice-content">
            <span className="notice-icon"></span>
            <div className="notice-text">
              <strong>Limited History:</strong> Anonymous users see recent session history only.
              <br />
              <span className="sign-in-prompt">
                Sign in to save your search history permanently across devices.
              </span>
            </div>
          </div>
        </div>
      )}

      {history.length === 0 ? (
        <div className="empty-history">
          <div className="empty-icon"></div>
          <h3>No search history yet</h3>
          <p>
            {isAuthenticated 
              ? "Start discovering papers to build your research history!"
              : "Your recent searches will appear here during this session."
            }
          </p>
          <button 
            onClick={() => navigate('/')}
            className="discover-link"
          >
            Start Researching →
          </button>
        </div>
      ) : (
        <div className="history-list">
          {history.map((searchItem, index) => (
            <div key={searchItem.search_id || index} className="history-item">
              <div className="search-info">
                <div className="search-query" title={searchItem.query}>
                  {searchItem.query}
                </div>
                
                <div className="search-meta">
                  <div className="meta-row">
                    <span className="meta-item">
                      <span className="meta-icon"></span>
                      {formatDate(searchItem.timestamp)}
                    </span>
                    <span className="meta-item">
                      <span className="meta-icon"></span>
                      {searchItem.results_count} results
                    </span>
                  </div>
                  
                  <div className="meta-row">
                    <span className="meta-item sources">
                      <span className="meta-icon"></span>
                      {formatSources(searchItem.sources)}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="search-actions">
                <button 
                  onClick={() => handleRepeatSearch(searchItem)}
                  className="action-btn repeat-btn"
                  title="Repeat this search"
                >
                  Repeat
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchHistory;