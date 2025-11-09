import React from 'react';
import './PaperCard.css';

// Helper function to format authors list
const formatAuthors = (authors, maxAuthors = 3) => {
  if (!authors || authors.length === 0) return 'Unknown';
  
  if (authors.length <= maxAuthors) {
    return authors.join(', ');
  }
  
  const displayedAuthors = authors.slice(0, maxAuthors).join(', ');
  const remainingCount = authors.length - maxAuthors;
  return `${displayedAuthors} +${remainingCount} more`;
};

const PaperCard = ({ 
  paper, 
  index,
  isBookmarked = false,
  onToggleBookmark,
  onViewDetails,
  onDownloadPaper,
  onBuildGraph,
  isBuildingGraph = false,
  showActions = true,
  showRelevanceScore = false
}) => {
  return (
    <div className="paper-card">
      <div className="paper-header">
        <h4 className="paper-title">{paper.title || 'Untitled Paper'}</h4>
        <div className="paper-header-actions">
          {showRelevanceScore && paper.relevance_score && (
            <div className="paper-meta">
              <span className="relevance-score">
                Relevance: {Math.round(paper.relevance_score)}%
              </span>
            </div>
          )}
          {onToggleBookmark && (
            <button
              onClick={() => onToggleBookmark(paper)}
              className={`bookmark-btn ${isBookmarked ? 'bookmarked' : 'not-bookmarked'}`}
              title={isBookmarked ? 'Remove from bookmarks' : 'Add to bookmarks'}
            >
              <i className={`fas fa-bookmark ${isBookmarked ? '' : 'far'}`}></i>
            </button>
          )}
        </div>
      </div>

      <div className="paper-authors">
        <strong>Authors:</strong> {formatAuthors(paper.authors, 3)}
      </div>

      <div className="paper-details">
        {paper.published && (
          <span className="paper-date"><strong>Published:</strong> {paper.published}</span>
        )}
        {paper.citation_count !== undefined && paper.citation_count !== null && (
          <span className="citation-count"><strong>Citations:</strong> {paper.citation_count}</span>
        )}
      </div>

      {showActions && (
        <div className="paper-actions">
          {onViewDetails && (
            <button 
              onClick={() => onViewDetails(paper, index)}
              className="action-btn view-btn"
            >
              <i className="fas fa-eye"></i>
              View Details
            </button>
          )}
          
          {onBuildGraph && (
            <button 
              onClick={() => onBuildGraph(paper)}
              className="action-btn graph-btn"
              disabled={isBuildingGraph}
            >
              {isBuildingGraph ? (
                <>
                  <i className="fas fa-spinner fa-spin"></i>
                  Building...
                </>
              ) : (
                <>
                  <i className="fas fa-project-diagram"></i>
                  Build Graph
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default PaperCard;
