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
            <i className="fas fa-microscope header-icon"></i>
            <div>
              <h1> Academic Paper Discovery Engine</h1>
              <div className="header-subtitle">
                AI-Powered Research Paper Discovery & Analysis Platform
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