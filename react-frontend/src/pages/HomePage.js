import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { discoverPapers, getCurrentSessionId } from '../services/api';
import './HomePage.css';

const HomePage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const handleSearchClick = async () => {
    if (!searchQuery.trim()) return;

    try {
      setIsSearching(true);
      console.log('HomePage: Starting search for:', searchQuery.trim());
      console.log('HomePage: Current session ID:', getCurrentSessionId());
      
      // Call backend API to discover papers
      const response = await discoverPapers(searchQuery.trim(), ['openalex'], 10);
      console.log('HomePage: API Response received:', response);
      console.log('HomePage: Number of papers:', response?.papers?.length || 0);
      console.log('HomePage: Success status:', response?.success);
      
      // Small delay to ensure backend cache is written
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Navigate to search page - PaperDiscovery will load cached results
      console.log('HomePage: Navigating to /search');
      if (location.pathname !== '/search') {
        navigate('/search');
      }
    } catch (error) {
      console.error('HomePage: Search failed:', error);
      // Navigate anyway to show error state
      if (location.pathname !== '/search') {
        navigate('/search');
      }
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !isSearching) {
      handleSearchClick();
    }
  };

  const features = [
    {
      title: 'Discover',
      description: 'Discover the most relevant academic papers faster',
      link: '/about'
    },
    {
      title: 'Visualize',
      description: 'See your research paper connections from a bird\'s-eye view',
      link: '/about'
    },

    {
      title: 'Save',
      description: 'Save your favourite research paper for future',
      link: '/about'
    }
  ];

  return (
    <div className="homepage">
      {/* Loading Overlay */}
      {isSearching && (
        <div className="loading-overlay">
          <div className="loading-spinner-container">
            <div className="loading-spinner"></div>
            <p className="loading-text">Discovering papers...</p>
          </div>
        </div>
      )}

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            Find the Most Relevant Research Papers<br />
            <span className="hero-highlight">for Your Questions</span>
          </h1>
          
          <div className="hero-search-container">
            <div className="hero-search-box">
              <svg className="search-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" />
              </svg>
              <input
                type="text"
                placeholder="Search by keyword, author, DOI, Pubmed ID or arXiv ID"
                className="hero-search-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
              />
            </div>
            
            <button 
              className="hero-discover-button"
              onClick={handleSearchClick}
              disabled={!searchQuery.trim() || isSearching}
            >
              <svg className="button-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" />
              </svg>
              Discover Papers
            </button>
          </div>
        </div>

        {/* Decorative network background */}
        <div className="hero-background">
          <svg className="network-svg" viewBox="0 0 1200 400" preserveAspectRatio="none">
            {/* Network nodes and connections */}
            <defs>
              <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#667eea" stopOpacity="0.2" />
                <stop offset="100%" stopColor="#764ba2" stopOpacity="0.1" />
              </linearGradient>
            </defs>
            
            {/* Connection lines */}
            <line x1="100" y1="150" x2="250" y2="100" stroke="url(#lineGradient)" strokeWidth="1" />
            <line x1="250" y1="100" x2="400" y2="180" stroke="url(#lineGradient)" strokeWidth="1" />
            <line x1="400" y1="180" x2="550" y2="120" stroke="url(#lineGradient)" strokeWidth="1" />
            <line x1="550" y1="120" x2="700" y2="200" stroke="url(#lineGradient)" strokeWidth="1" />
            <line x1="700" y1="200" x2="850" y2="140" stroke="url(#lineGradient)" strokeWidth="1" />
            <line x1="850" y1="140" x2="1000" y2="180" stroke="url(#lineGradient)" strokeWidth="1" />
            
            {/* Nodes */}
            <circle cx="100" cy="150" r="4" fill="#667eea" opacity="0.3" />
            <circle cx="250" cy="100" r="5" fill="#667eea" opacity="0.4" />
            <circle cx="400" cy="180" r="4" fill="#764ba2" opacity="0.3" />
            <circle cx="550" cy="120" r="6" fill="#667eea" opacity="0.5" />
            <circle cx="700" cy="200" r="5" fill="#764ba2" opacity="0.4" />
            <circle cx="850" cy="140" r="4" fill="#667eea" opacity="0.3" />
            <circle cx="1000" cy="180" r="5" fill="#764ba2" opacity="0.4" />
            
            {/* Additional decorative nodes */}
            <circle cx="300" cy="250" r="3" fill="#667eea" opacity="0.2" />
            <circle cx="600" cy="280" r="4" fill="#764ba2" opacity="0.3" />
            <circle cx="900" cy="250" r="3" fill="#667eea" opacity="0.2" />
          </svg>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="features-header">
          <h2 className="features-title">YOUR AI COMPANION FOR SEARCHING RESEARCH PAPERS</h2>
          <p className="features-subtitle">
            Navigate <strong>Academic papers </strong>, <strong>Build Citation Graphs </strong>, and uncover hidden connections.
          </p>
        </div>

        <div className="features-grid">
          {features.map((feature, index) => (
            <div key={index} className="feature-card">
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
              <button 
                className="feature-link"
                onClick={() => navigate(feature.link)}
              >
                LEARN MORE
              </button>
            </div>
          ))}
        </div>

        <div className="cta-section">
          <button 
            className="cta-button"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          >
            Get Started
            <svg className="cta-arrow" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" />
            </svg>
          </button>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
