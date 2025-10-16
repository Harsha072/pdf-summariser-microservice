import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotification } from '../context/NotificationContext';
import { getCurrentSessionId } from '../services/api';
import '../components/common.css';

const SavedPapers = () => {
  const { user } = useAuth();
  const { addNotification } = useNotification();
  const [bookmarks, setBookmarks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchBookmarks();
  }, [user]);

  const fetchBookmarks = async () => {
    try {
      setLoading(true);
      const sessionId = getCurrentSessionId();
      
      const response = await fetch('/api/bookmarks', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId,
          ...(user && { 'Authorization': `Bearer ${await user.getIdToken()}` })
        }
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
      
      const response = await fetch('/api/bookmarks/remove', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId,
          ...(user && { 'Authorization': `Bearer ${await user.getIdToken()}` })
        },
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

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleDateString();
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
            {bookmarks.map((paper) => (
              <div key={paper.paper_id} className="paper-card saved-paper-card">
                <div className="paper-header">
                  <h3 className="paper-title">
                    {paper.url ? (
                      <a href={paper.url} target="_blank" rel="noopener noreferrer">
                        {paper.title || 'Untitled Paper'}
                      </a>
                    ) : (
                      paper.title || 'Untitled Paper'
                    )}
                  </h3>
                  <button
                    onClick={() => removeBookmark(paper.paper_id)}
                    className="bookmark-btn bookmarked"
                    title="Remove from bookmarks"
                  >
                    <i className="fas fa-bookmark"></i>
                  </button>
                </div>

                <div className="paper-meta">
                  {paper.authors && paper.authors.length > 0 && (
                    <p className="authors">
                      <i className="fas fa-user"></i>
                      {Array.isArray(paper.authors) 
                        ? paper.authors.slice(0, 3).join(', ')
                        : paper.authors
                      }
                      {Array.isArray(paper.authors) && paper.authors.length > 3 && ' et al.'}
                    </p>
                  )}
                  
                  {paper.published && (
                    <p className="published">
                      <i className="fas fa-calendar"></i>
                      {formatDate(paper.published)}
                    </p>
                  )}
                  
                  <p className="bookmarked-date">
                    <i className="fas fa-bookmark"></i>
                    Saved on {formatDate(paper.bookmarked_at)}
                  </p>

                  {paper.source && (
                    <span className={`source-badge source-${paper.source.toLowerCase().replace(' ', '-')}`}>
                      {paper.source}
                    </span>
                  )}
                </div>

                {paper.summary && (
                  <p className="paper-summary">
                    {paper.summary.length > 300 
                      ? `${paper.summary.substring(0, 300)}...`
                      : paper.summary
                    }
                  </p>
                )}

                <div className="paper-actions">
                  {paper.url && (
                    <a 
                      href={paper.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn btn-secondary"
                    >
                      <i className="fas fa-external-link-alt"></i>
                      View Paper
                    </a>
                  )}
                  
                  {paper.pdf_url && (
                    <a 
                      href={paper.pdf_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn btn-outline"
                    >
                      <i className="fas fa-file-pdf"></i>
                      Download PDF
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SavedPapers;