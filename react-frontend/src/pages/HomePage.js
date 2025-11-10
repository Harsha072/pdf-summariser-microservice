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

      {/* Our Impact Section */}
      <section className="impact-section">
        <h2 className="section-title">Our Impact</h2>
        <div className="impact-grid">
          <div className="impact-card">
            <div className="impact-number">10x</div>
            <div className="impact-label">Faster Literature Reviews</div>
            <div className="impact-description">Students complete literature reviews in days instead of weeks</div>
          </div>
          <div className="impact-card">
            <div className="impact-number">Paper Networks</div>
            <div className="impact-label">Visualize Connections</div>
            <div className="impact-description">Visualize paper connections and citation relationships</div>
          </div>
        </div>
      </section>

      {/* Our Mission Section */}
      <section className="mission-section">
        <h2 className="section-title">Our Mission</h2>
        <div className="mission-content">
          <p className="mission-intro">
            Our mission is to <span className="mission-highlight">democratize academic research</span> by making literature discovery fast, intuitive, and accessible to everyone. We believe that:
          </p>
          <div className="mission-beliefs">
            <div className="belief-item">
              <svg className="check-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
              <span>Every student deserves powerful research tools, regardless of their institution or budget</span>
            </div>
            <div className="belief-item">
              <svg className="check-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
              <span>Technology should simplify research, not complicate it</span>
            </div>
            <div className="belief-item">
              <svg className="check-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
              <span>Understanding research connections is as important as finding individual papers</span>
            </div>
            <div className="belief-item">
              <svg className="check-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
              <span>AI can augment human intelligence to accelerate discovery</span>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action Section */}
      <section className="transform-section">
        <div className="transform-content">
          <h2 className="transform-title">Ready to Transform Your Research?</h2>
          <p className="transform-description">
            Join thousands of students and researchers who are discovering papers faster and understanding research better.
          </p>
          <button 
            className="transform-button"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          >
            Start Exploring
            <svg className="arrow-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" />
            </svg>
          </button>
        </div>
      </section>
      <footer className="about-footer">
        <div className="footer-content">
          <div className="footer-grid">
            <div className="footer-column">
              <h3 className="footer-heading">Scholar Quest</h3>
              <p className="footer-description">
                Empowering researchers and students to navigate academic literature with AI-powered tools and intelligent insights.
              </p>
            </div>

            <div className="footer-column">
              <h4 className="footer-title">Product</h4>
              <ul className="footer-links">
                <li><a href="/search">Search Papers</a></li>
                <li><a href="/saved">Saved Papers</a></li>
                <li><a href="/history">Search History</a></li>
                <li><a href="/paper-relationships">Citation Network</a></li>
              </ul>
            </div>

            <div className="footer-column">
              <h4 className="footer-title">Company</h4>
              <ul className="footer-links">
                <li><a href="/about">About Us</a></li>
                <li><a href="/about#mission">Our Mission</a></li>
                <li><a href="/about#impact">Impact</a></li>
              </ul>
            </div>

            <div className="footer-column">
              <h4 className="footer-title">Connect</h4>
              <ul className="footer-links">
                <li><a href="mailto:support@scholarquest.com">Contact Us</a></li>
                <li><a href="https://github.com/Harsha072/pdf-summariser-microservice" target="_blank" rel="noopener noreferrer">GitHub</a></li>
              </ul>
            </div>
          </div>

          <div className="footer-bottom">
            <p className="footer-copyright">
              &copy; {new Date().getFullYear()} Scholar Quest. All rights reserved.
            </p>
            <div className="footer-bottom-links">
              <a href="/privacy">Privacy Policy</a>
              <span className="separator">•</span>
              <a href="/terms">Terms of Service</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;
