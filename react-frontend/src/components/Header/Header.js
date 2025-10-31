import React from 'react';

import './Header.css';

const Header = () => {
  return (
    <header className="header navbar">
      <div className="navbar-container">
        <div className="navbar-logo">
          {/* Replace with your logo SVG or image if available */}
          <span className="logo-icon">{/* ◯─◯ (placeholder for Litmaps-like icon) */}</span>
          <span className="logo-text">Litmaps</span>
          <span className="logo-reg">®</span>
        </div>
        <nav className="navbar-menu">
          <a href="#about" className="navbar-link">About <span className="navbar-caret">▼</span></a>
          <a href="#features" className="navbar-link">Features</a>
          <a href="#pricing" className="navbar-link">Pricing</a>
          <a href="#company" className="navbar-link">Company</a>
          <a href="#blog" className="navbar-link">Blog</a>
        </nav>
        <div className="navbar-login">
          <button className="login-btn">Login</button>
        </div>
      </div>
    </header>
  );
};

export default Header;