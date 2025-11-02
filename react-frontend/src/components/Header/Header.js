import React from 'react';


import { Link, useLocation } from 'react-router-dom';
import UserProfile from '../Auth/UserProfile';
import './Header.css';


const navItems = [

   { label: 'About', path: '/help', description: 'Usage instructions'},
  { label: 'Search History', path: '/history', description: 'Recent searches'},
  { label: 'Saved Papers', path: '/saved', description: 'Bookmarked papers'},
  { label: 'User Profile', path: '/profile', description: 'User Profile' },
];

const Header = () => {
  const location = useLocation();
  return (
    <header className="header navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          {/* Replace with your logo SVG or image if available */}
          <span className="logo-icon">{/* ◯─◯ (placeholder for Litmaps-like icon) */}</span>
          <span className="logo-text">Scholar Quest</span>
          <span className="logo-reg">®</span>
        </Link>
        <nav className="navbar-menu">
          {navItems.map((item, idx) => (
            <Link
              key={item.label}
              to={item.path}
              className={`navbar-link${location.pathname === item.path ? ' active' : ''}`}
              title={item.description}
            >
              {item.label}
              {item.badge && (
                <span className="nav-badge" style={{ marginLeft: 6, fontSize: '0.8em', background: '#e5e7eb', color: '#111', borderRadius: '8px', padding: '2px 7px' }}>{item.badge}</span>
              )}
            </Link>
          ))}
        </nav>
        <div className="navbar-user">
          <UserProfile />
        </div>
      </div>
    </header>
  );
};

export default Header;