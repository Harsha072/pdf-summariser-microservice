import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import LoginModal from './LoginModal';
import './AuthGuard.css';

/**
 * AuthGuard - Higher-order component that protects features requiring authentication
 * Shows login prompt for unauthenticated users trying to access protected features
 */
const AuthGuard = ({ 
  children, 
  fallback = null, 
  requireAuth = true,
  feature = "this feature",
  showInlinePrompt = false 
}) => {
  const { isAuthenticated, loading, user } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);

  // Show loading state
  if (loading) {
    return (
      <div className="auth-guard-loading">
        <div className="loading-spinner"></div>
        <p>Checking authentication...</p>
      </div>
    );
  }

  // If authentication is required and user is not authenticated
  if (requireAuth && !isAuthenticated) {
    // Show inline prompt instead of modal
    if (showInlinePrompt) {
      return (
        <div className="auth-guard-prompt">
          <div className="auth-prompt-card">
            <div className="auth-prompt-icon"></div>
            <h3>Sign In Required</h3>
            <p>You need to sign in to access {feature}.</p>
            <div className="auth-prompt-benefits">
              <h4>With an account, you can:</h4>
              <ul>
                <li>Download papers and PDFs</li>
                <li>View detailed paper analysis</li>
                <li>Access your search history</li>
                <li>Save favorite papers</li>
                <li>Sync across devices</li>
              </ul>
            </div>
            <button 
              className="auth-prompt-button"
              onClick={() => setShowLoginModal(true)}
            >
              Sign In to Continue
            </button>
            <button 
              className="auth-prompt-button secondary"
              onClick={() => setShowLoginModal(true)}
            >
              Create Free Account
            </button>
          </div>
          
          {showLoginModal && (
            <LoginModal 
              isOpen={showLoginModal}
              onClose={() => setShowLoginModal(false)}
              title={`Sign in to access ${feature}`}
            />
          )}
        </div>
      );
    }

    // Show fallback component or trigger login modal
    if (fallback) {
      return fallback;
    }

    // Auto-show login modal for protected actions
    return (
      <div className="auth-guard-modal-trigger">
        {!showLoginModal && (
          <div className="auth-required-overlay">
            <div className="auth-required-message">
              <div className="auth-icon"></div>
              <h3>Authentication Required</h3>
              <p>Please sign in to access {feature}</p>
              <button 
                className="sign-in-button"
                onClick={() => setShowLoginModal(true)}
              >
                Sign In
              </button>
            </div>
          </div>
        )}
        
        {showLoginModal && (
          <LoginModal 
            isOpen={showLoginModal}
            onClose={() => setShowLoginModal(false)}
            title={`Sign in to access ${feature}`}
          />
        )}
      </div>
    );
  }

  // User is authenticated or authentication not required
  return children;
};

/**
 * ProtectedButton - Button that shows login prompt when clicked by unauthenticated users
 */
export const ProtectedButton = ({ 
  onClick, 
  children, 
  feature = "this feature",
  className = "",
  disabled = false,
  ...props 
}) => {
  const { isAuthenticated, loading } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);

  // Execute pending action after successful authentication
  useEffect(() => {
    if (isAuthenticated && pendingAction && !loading) {
      const action = pendingAction;
      setPendingAction(null);
      setShowLoginModal(false);
      // Execute the original click handler
      if (onClick) {
        onClick(action);
      }
    }
  }, [isAuthenticated, pendingAction, loading, onClick]);

  const handleClick = (e) => {
    if (!isAuthenticated) {
      e.preventDefault();
      setPendingAction(e); // Store the event for later
      setShowLoginModal(true);
      return;
    }
    
    if (onClick) {
      onClick(e);
    }
  };

  const handleModalClose = () => {
    setShowLoginModal(false);
    setPendingAction(null); // Clear pending action if modal is closed without login
  };

  return (
    <>
      <button 
        {...props}
        className={`protected-button ${className} ${!isAuthenticated ? 'requires-auth' : ''}`}
        onClick={handleClick}
        disabled={disabled || loading}
      >
        {children}
        {!isAuthenticated && <span className="auth-lock-icon"></span>}
      </button>
      
      {showLoginModal && (
        <LoginModal 
          isOpen={showLoginModal}
          onClose={handleModalClose}
          title={`Sign in to ${feature}`}
          hideGuestMode={true}
        />
      )}
    </>
  );
};

/**
 * ProtectedLink - Link that shows login prompt when clicked by unauthenticated users  
 */
export const ProtectedLink = ({ 
  onClick, 
  href,
  children, 
  feature = "access this content",
  className = "",
  ...props 
}) => {
  const { isAuthenticated } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);

  const handleClick = (e) => {
    if (!isAuthenticated) {
      e.preventDefault();
      setShowLoginModal(true);
      return;
    }
    
    if (onClick) {
      onClick(e);
    }
  };

  return (
    <>
      <a 
        {...props}
        href={href}
        className={`protected-link ${className} ${!isAuthenticated ? 'requires-auth' : ''}`}
        onClick={handleClick}
      >
        {children}
        {!isAuthenticated && <span className="auth-lock-icon"></span>}
      </a>
      
      {showLoginModal && (
        <LoginModal 
          isOpen={showLoginModal}
          onClose={() => setShowLoginModal(false)}
          title={`Sign in to ${feature}`}
        />
      )}
    </>
  );
};

export default AuthGuard;