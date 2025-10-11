import React from 'react';
import '../components/common.css';

const SavedPapers = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <i className="fas fa-bookmark"></i>
          Saved Papers
        </h1>
        <p className="page-description">
          Access your bookmarked research papers and personal research library
        </p>
      </div>

      <div className="content-section">
        <div className="empty-state">
          <i className="fas fa-book-open icon-large"></i>
          <h3>No Saved Papers Yet</h3>
          <p>Papers you bookmark will appear here for easy access later.</p>
          <a href="/" className="btn btn-primary">
            <i className="fas fa-search"></i>
            Discover Papers
          </a>
        </div>
      </div>
    </div>
  );
};

export default SavedPapers;