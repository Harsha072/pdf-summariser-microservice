import React from 'react';
import UserProfile from '../Auth/UserProfile';
import './Header.css';

const Header = ({ connectionStatus, onMenuToggle, isMenuOpen }) => {
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
          <button 
            className="hamburger-menu"
            onClick={onMenuToggle}
            aria-label="Toggle navigation menu"
            aria-expanded={isMenuOpen}
          >
            <div className={`hamburger-lines ${isMenuOpen ? 'open' : ''}`}>
              <span></span>
              <span></span>
              <span></span>
            </div>
          </button>
          <div className="header-title">
            <i className="fas fa-microscope header-icon"></i>
            <div>
              <h1> Academic Paper Discovery Engine</h1>
              <div className="header-subtitle">
                AI-Powered Research Paper Discovery & Analysis Platform
              </div>
            </div>
          </div>
          <div className="header-actions">
            <div className="header-status">
              <div className="status-indicator">
                <div className={`status-dot ${getStatusClass()}`}></div>
                <span className="status-text">{getStatusText()}</span>
              </div>
            </div>
            <UserProfile />
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;