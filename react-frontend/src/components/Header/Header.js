import React from 'react';
import './Header.css';

const Header = ({ connectionStatus }) => {
  const getStatusClass = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'status-connected';
      case 'disconnected':
        return 'status-disconnected';
      default:
        return 'status-checking';
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected';
      case 'disconnected':
        return 'Disconnected';
      default:
        return 'Checking...';
    }
  };

  return (
    <header className="header">
      <div className="header-container">
        <div className="header-content">
          <div className="header-title">
            <i className="fas fa-file-pdf header-icon"></i>
            <div>
              <h1>PDF AI Assistant</h1>
              <div className="header-subtitle">
                Professional Document Analysis & AI-Powered Insights
              </div>
            </div>
          </div>
          <div className="header-status">
            <div className="status-indicator">
              <div className={`status-dot ${getStatusClass()}`}></div>
              <span className="status-text">{getStatusText()}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;