import React from 'react';
import '../components/common.css';

const SearchHistory = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <i className="fas fa-history"></i>
          Search History
        </h1>
        <p className="page-description">
          View and manage your previous research queries and results
        </p>
      </div>

      <div className="content-section">
        <div className="empty-state">
          <i className="fas fa-search icon-large"></i>
          <h3>No Search History Yet</h3>
          <p>Your previous searches will appear here once you start discovering papers.</p>
          <a href="/" className="btn btn-primary">
            <i className="fas fa-rocket"></i>
            Start Searching
          </a>
        </div>
      </div>
    </div>
  );
};

export default SearchHistory;