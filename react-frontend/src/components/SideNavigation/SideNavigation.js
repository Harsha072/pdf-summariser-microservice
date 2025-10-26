import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './SideNavigation.css';

const SideNavigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);

  const navigationSections = [
    {
      title: "Research",
      items: [
        {
          icon: "",
          label: "Discover Papers",
          path: "/",
          description: "Search academic papers",
          badge: null
        },
        {
          icon: "",
          label: "Paper Relationships",
          path: "/paper-relationships",
          description: "Explore paper family trees",
          badge: "SIMPLE"
        },
        {
          icon: "",
          label: "Search History",
          path: "/history",
          description: "Recent searches",
          badge: "3"
        },
        {
          icon: "",
          label: "Saved Papers",
          path: "/saved",
          description: "Bookmarked papers",
          badge: "12"
        }
      ]
    },
    {
      title: "Settings",
      items: [
        {
          icon: "",
          label: "Help & Guide",
          path: "/help",
          description: "Usage instructions",
          badge: null
        },
        {
          icon: "",
          label: "User Profile",
          path: "/profile",
          description: "User Profile",
          badge: null
        },
        {
          icon: "",
          label: "Login/Logout",
          path: "/login",
          description: "Authentication",
          badge: null
        }
      ]
    }
  ];

  const handleNavigation = (path) => {
    navigate(path);
    setIsOpen(false); // Close nav after navigation
  };

  const isActive = (path) => location.pathname === path;

  const toggleNavigation = () => {
    setIsOpen(!isOpen);
  };

  const closeNavigation = () => {
    setIsOpen(false);
  };

  return (
    <>
      {/* Hamburger Menu Button */}
      <button 
        className="hamburger-menu"
        onClick={toggleNavigation}
        aria-label="Toggle navigation menu"
      >
        <div className={`hamburger-lines ${isOpen ? 'open' : ''}`}>
          <span></span>
          <span></span>
          <span></span>
        </div>
      </button>

      {/* Overlay */}
      {isOpen && (
        <div 
          className="nav-overlay"
          onClick={closeNavigation}
        />
      )}

      {/* Side Navigation */}
      <nav className={`side-navigation ${isOpen ? 'open' : ''}`}>
        <div className="nav-header">
          <div className="nav-brand">
            <span className="brand-icon"></span>
            <h2>Paper Discovery</h2>
          </div>
          <button 
            className="nav-close"
            onClick={closeNavigation}
            aria-label="Close navigation"
          >
            ×
          </button>
        </div>

        <div className="nav-content">
          {navigationSections.map((section, sectionIndex) => (
            <div key={sectionIndex} className="nav-section">
              <div className="section-title">{section.title}</div>
              
              {section.items.map((item, itemIndex) => (
                <button
                  key={itemIndex}
                  className={`nav-item ${isActive(item.path) ? 'active' : ''}`}
                  onClick={() => handleNavigation(item.path)}
                  title={item.description}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <div className="nav-text">
                    <span className="nav-label">{item.label}</span>
                    <span className="nav-description">{item.description}</span>
                  </div>
                  {item.badge && (
                    <span className="nav-badge">{item.badge}</span>
                  )}
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="nav-footer">
          <div className="session-info">
            <span className="session-label">Session Active</span>
            <span className="session-status">●</span>
          </div>
          <div className="app-version">
            <span>Academic Paper Discovery v2.0</span>
          </div>
        </div>
      </nav>
    </>
  );
};

export default SideNavigation;