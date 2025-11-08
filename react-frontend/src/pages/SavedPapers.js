import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { getCurrentSessionId } from '../services/api';
import PaperCard from '../components/PaperCard/PaperCard';
import '../components/common.css';
import '../components/PaperDiscovery/PaperDiscovery.css';

const SavedPapers = () => {
  const { user, refreshToken } = useAuth();
  const { addNotification } = useNotification();
  const [bookmarks, setBookmarks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchBookmarks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const fetchBookmarks = async () => {
    try {
      setLoading(true);
      const sessionId = getCurrentSessionId();
      
      const headers = {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId
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

      const response = await fetch('http://localhost:5000/api/bookmarks', {
        method: 'GET',
        headers: headers
      });

      const data = await response.json();
      
      if (data.success) {
        setBookmarks(data.bookmarks);
        setError(null);
      } else {
        setError(data.error || 'Failed to load bookmarks');
      }
    } catch (err) {
      console.error('Error fetching bookmarks:', err);
      setError('Failed to load bookmarks');
    } finally {
      setLoading(false);
    }
  };

  const removeBookmark = async (paperId) => {
    try {
      const sessionId = getCurrentSessionId();
      
      const headers = {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId
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

      const response = await fetch('http://localhost:5000/api/bookmarks/remove', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ paper_id: paperId })
      });

      const data = await response.json();
      
      if (data.success) {
        setBookmarks(bookmarks.filter(paper => paper.paper_id !== paperId));
        addNotification('Paper removed from bookmarks', 'success');
      } else {
        addNotification(data.error || 'Failed to remove bookmark', 'error');
      }
    } catch (err) {
      console.error('Error removing bookmark:', err);
      addNotification('Failed to remove bookmark', 'error');
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">
            <i className="fas fa-bookmark"></i>
            Saved Papers
          </h1>
        </div>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading your saved papers...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">
            <i className="fas fa-bookmark"></i>
            Saved Papers
          </h1>
        </div>
        <div className="error-state">
          <i className="fas fa-exclamation-triangle"></i>
          <h3>Error Loading Bookmarks</h3>
          <p>{error}</p>
          <button onClick={fetchBookmarks} className="btn btn-primary">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <i className="fas fa-bookmark"></i>
          Saved Papers ({bookmarks.length})
        </h1>
        <p className="page-description">
          Your personal research library of bookmarked papers
        </p>
      </div>

      <div className="content-section">
        {bookmarks.length === 0 ? (
          <div className="empty-state">
            <i className="fas fa-book-open icon-large"></i>
            <h3>No Saved Papers Yet</h3>
            <p>Papers you bookmark will appear here for easy access later.</p>
            <a href="/" className="btn btn-primary">
              <i className="fas fa-search"></i>
              Discover Papers
            </a>
          </div>
        ) : (
          <div className="papers-grid">
            {bookmarks.map((paper, index) => (
              <PaperCard
                key={paper.paper_id || index}
                paper={paper}
                index={index}
                isBookmarked={true}
                onToggleBookmark={removeBookmark}
                showActions={true}
                showRelevanceScore={false}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SavedPapers;