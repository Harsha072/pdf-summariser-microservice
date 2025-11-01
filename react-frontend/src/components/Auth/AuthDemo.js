import React from 'react';
import { useAuth } from '../../context/AuthContext';
import AuthGuard, { ProtectedButton, ProtectedLink } from '../Auth/AuthGuard';
import './AuthDemo.css';

const AuthDemo = () => {
  const { isAuthenticated, user } = useAuth();

  const demoFeatures = [
    {
      id: 'search',
      title: 'Search Papers',
      description: 'Browse and search academic papers from multiple sources',
      access: 'free',
      status: 'Available to everyone'
    },
    {
      id: 'view-basic',
      title: 'View Basic Info',
      description: 'See paper title, authors, summary, and source',
      access: 'free',
      status: 'Available to everyone'
    },
    {
      id: 'download',
      title: 'Download Papers',
      description: 'Download PDF files of research papers',
      access: 'premium',
      status: 'Requires sign in'
    },
    {
      id: 'analysis',
      title: 'AI Analysis',
      description: 'Get detailed AI-powered analysis and insights',
      access: 'premium',
      status: 'Requires sign in'
    },
    {
      id: 'history',
      title: 'Search History',
      description: 'Access your personal search history across sessions',
      access: 'premium',
      status: 'Requires sign in'
    },
    {
      id: 'favorites',
      title: 'Save Favorites',
      description: 'Save and organize your favorite papers',
      access: 'premium',
      status: 'Coming soon - Requires sign in'
    }
  ];

  const handleProtectedAction = (featureName) => {
    alert(`This would trigger: ${featureName}`);
  };

  return (
    <div className="auth-demo">
      <div className="demo-header">
        <h2>Authorization Features Demo</h2>
        <p className="demo-subtitle">
          Academic Paper Discovery Engine offers both free and premium features. 
          See what's available to you based on your account status.
        </p>
        
        <div className="current-status">
          {isAuthenticated ? (
            <div className="status-card authenticated">
              <div className="status-icon"></div>
              <div className="status-info">
                <strong>Signed In</strong>
                <p>Welcome {user?.displayName || user?.email}! You have access to all features.</p>
              </div>
            </div>
          ) : (
            <div className="status-card guest">
              <div className="status-icon"></div>
              <div className="status-info">
                <strong>Guest User</strong>
                <p>You have free access to search and browse. Sign in for premium features.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="features-grid">
        {demoFeatures.map((feature) => (
          <div 
            key={feature.id} 
            className={`feature-card ${feature.access === 'premium' && !isAuthenticated ? 'locked' : 'unlocked'}`}
          >
            <div className="feature-header">
              <h3>{feature.title}</h3>
              <div className={`access-badge ${feature.access}`}>
                {feature.access === 'free' ? 'Free' : 'Premium'}
              </div>
            </div>
            
            <p className="feature-description">{feature.description}</p>
            
            <div className="feature-status">
              <span className={`status-indicator ${feature.access === 'free' || isAuthenticated ? 'available' : 'locked'}`}>
                {feature.status}
              </span>
            </div>
            
            <div className="feature-actions">
              {feature.access === 'free' ? (
                <button 
                  className="demo-button available"
                  onClick={() => handleProtectedAction(feature.title)}
                >
                  Try Now
                </button>
              ) : (
                <ProtectedButton
                  className="demo-button protected"
                  onClick={() => handleProtectedAction(feature.title)}
                  feature={feature.title.toLowerCase()}
                >
                  {isAuthenticated ? 'Try Now' : 'Sign In Required'}
                </ProtectedButton>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="auth-examples">
        <h3>Interactive Examples</h3>
        <div className="examples-grid">
          
          <div className="example-card">
            <h4>Protected Button Example</h4>
            <p>This button requires authentication to work:</p>
            <ProtectedButton
              className="example-button"
              onClick={() => alert('Success! You are authenticated.')}
              feature="access this demo feature"
            >
              Download Sample Paper
            </ProtectedButton>
          </div>

          <div className="example-card">
            <h4>Protected Link Example</h4>
            <p>This link requires authentication to navigate:</p>
            <ProtectedLink
              href="#premium-content"
              className="example-link"
              onClick={(e) => {
                e.preventDefault();
                alert('Success! You are authenticated.');
              }}
              feature="access premium content"
            >
              View Detailed Analysis
            </ProtectedLink>
          </div>

          <div className="example-card">
            <h4>Auth Guard Example</h4>
            <p>This content is protected by an auth guard:</p>
            <AuthGuard 
              requireAuth={true} 
              feature="premium dashboard"
              showInlinePrompt={true}
            >
              <div className="protected-content">
                <div className="premium-feature">
                  <h5>Premium Content</h5>
                  <p>This is exclusive content only available to signed-in users!</p>
                  <ul>
                    <li>Advanced search filters</li>
                    <li>Unlimited downloads</li>
                    <li>Priority support</li>
                    <li>Export to citation managers</li>
                  </ul>
                </div>
              </div>
            </AuthGuard>
          </div>
        </div>
      </div>

      <div className="benefits-section">
        <h3>Why Sign In?</h3>
        <div className="benefits-grid">
          <div className="benefit-item">
            <div className="benefit-icon"></div>
            <h4>Download Papers</h4>
            <p>Download PDF files directly to your device for offline reading</p>
          </div>
          <div className="benefit-item">
            <div className="benefit-icon"></div>
            <h4>AI Analysis</h4>
            <p>Get detailed AI-powered insights, summaries, and analysis</p>
          </div>
          <div className="benefit-item">
            <div className="benefit-icon"></div>
            <h4>Search History</h4>
            <p>Access your search history across devices and sessions</p>
          </div>
          <div className="benefit-item">
            <div className="benefit-icon"></div>
            <h4>Sync Across Devices</h4>
            <p>Your preferences and history sync across all your devices</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthDemo;