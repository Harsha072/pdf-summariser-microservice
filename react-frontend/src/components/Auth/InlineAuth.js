import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import './InlineAuth.css';

/**
 * InlineAuthPrompt - Shows authentication prompt directly in place of protected content
 * More user-friendly than modals, less intrusive
 */
const InlineAuthPrompt = ({ 
  feature = "this feature",
  children,
  compact = false,
  showBenefits = true
}) => {
  const { signInWithGoogle, signInWithGitHub } = useAuth();
  const [authLoading, setAuthLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleGoogleSignIn = async () => {
    try {
      setAuthLoading(true);
      setError(null);
      await signInWithGoogle();
    } catch (error) {
      setError('Sign in failed. Please try again.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleGitHubSignIn = async () => {
    try {
      setAuthLoading(true);
      setError(null);
      await signInWithGitHub();
    } catch (error) {
      setError('Sign in failed. Please try again.');
    } finally {
      setAuthLoading(false);
    }
  };

  if (compact) {
    return (
      <div className="inline-auth-compact">
        <div className="auth-compact-content">
          <span className="auth-lock"></span>
          <span className="auth-message">Sign in to {feature}</span>
          <div className="auth-compact-buttons">
            <button 
              className="auth-btn-mini google"
              onClick={handleGoogleSignIn}
              disabled={authLoading}
              title="Sign in with Google"
            >
              <i className="fab fa-google"></i>
            </button>
            <button 
              className="auth-btn-mini github"
              onClick={handleGitHubSignIn}
              disabled={authLoading}
              title="Sign in with GitHub"
            >
              <i className="fab fa-github"></i>
            </button>
          </div>
        </div>
        {error && <div className="auth-error-mini">{error}</div>}
      </div>
    );
  }

  return (
    <div className="inline-auth-prompt">
      <div className="auth-prompt-content">
        <div className="auth-icon-large"></div>
        <h3>Sign in required</h3>
        <p>You need to sign in to {feature}</p>
        
        {showBenefits && (
          <div className="auth-benefits-mini">
            <div className="benefit-item">Download papers and PDFs</div>
            <div className="benefit-item">View detailed AI analysis</div>
            <div className="benefit-item">Access search history</div>
            <div className="benefit-item">Save favorite papers</div>
          </div>
        )}

        <div className="auth-buttons">
          <button 
            className="auth-btn primary"
            onClick={handleGoogleSignIn}
            disabled={authLoading}
          >
            <i className="fab fa-google"></i>
            <span>Continue with Google</span>
          </button>
          
          <button 
            className="auth-btn secondary"
            onClick={handleGitHubSignIn}
            disabled={authLoading}
          >
            <i className="fab fa-github"></i>
            <span>Continue with GitHub</span>
          </button>
        </div>

        {error && <div className="auth-error">{error}</div>}
        
        <div className="auth-privacy">
          <small>Your data is secure. We only store your basic profile information.</small>
        </div>
      </div>
    </div>
  );
};

/**
 * ProtectedFeature - Replace protected buttons with inline auth when not authenticated
 */
export const ProtectedFeature = ({ 
  children, 
  feature = "this feature",
  fallback = null,
  compact = false,
  showBenefits = true
}) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-loading">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (fallback) {
      return fallback;
    }
    
    return (
      <InlineAuthPrompt 
        feature={feature}
        compact={compact}
        showBenefits={showBenefits}
      />
    );
  }

  return children;
};

/**
 * AuthButton - Smart button that handles authentication inline
 */
export const AuthButton = ({ 
  onClick,
  children,
  feature = "access this feature",
  className = "",
  disabled = false,
  ...props
}) => {
  const { isAuthenticated, signInWithGoogle, loading } = useAuth();
  const [showInlineAuth, setShowInlineAuth] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);

  const handleClick = async (e) => {
    if (!isAuthenticated) {
      e.preventDefault();
      setShowInlineAuth(true);
      return;
    }
    
    if (onClick) {
      onClick(e);
    }
  };

  const handleQuickAuth = async () => {
    try {
      setAuthLoading(true);
      await signInWithGoogle();
      setShowInlineAuth(false);
      // After auth, trigger the original action
      if (onClick) {
        onClick({});
      }
    } catch (error) {
      console.error('Quick auth failed:', error);
    } finally {
      setAuthLoading(false);
    }
  };

  if (showInlineAuth && !isAuthenticated) {
    return (
      <div className="auth-button-expanded">
        <div className="auth-button-prompt">
          <div>
            <strong>Sign in to {feature}</strong>
            <p>Quick and secure authentication</p>
          </div>
          <div className="auth-button-actions">
            <button 
              className="quick-auth-btn"
              onClick={handleQuickAuth}
              disabled={authLoading}
            >
              <i className="fab fa-google"></i>
              Google
            </button>
            <button 
              className="cancel-auth-btn"
              onClick={() => setShowInlineAuth(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <button 
      {...props}
      className={`auth-button ${className} ${!isAuthenticated ? 'requires-auth' : ''}`}
      onClick={handleClick}
      disabled={disabled || loading}
    >
      {children}
      {!isAuthenticated && <span className="auth-indicator"></span>}
    </button>
  );
};

export default InlineAuthPrompt;