import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import './LoginModal.css';

const LoginModal = ({ isOpen, onClose, title = "Sign In to Your Account", hideGuestMode = false }) => {
  const { signInWithGoogle, signInWithGitHub, signInAsGuest, error } = useAuth();
  const [loading, setLoading] = useState(false);
  const [loginError, setLoginError] = useState(null);

  const handleGoogleSignIn = async () => {
    try {
      setLoading(true);
      setLoginError(null);
      await signInWithGoogle();
      onClose();
    } catch (error) {
      console.error('Google sign in failed:', error);
      setLoginError('Failed to sign in with Google. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGitHubSignIn = async () => {
    try {
      setLoading(true);
      setLoginError(null);
      await signInWithGitHub();
      onClose();
    } catch (error) {
      console.error('GitHub sign in failed:', error);
      setLoginError('Failed to sign in with GitHub. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGuestMode = async () => {
    try {
      setLoading(true);
      setLoginError(null);
      await signInAsGuest();
      onClose();
    } catch (error) {
      console.error('Guest sign in failed:', error);
      setLoginError('Failed to continue as guest. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="login-modal-overlay" onClick={onClose}>
      <div className="login-modal" onClick={(e) => e.stopPropagation()}>
        <div className="login-header">
          <div className="login-title">
            <i className="fas fa-microscope"></i>
            <div>
              <h2>{title}</h2>
              <p>Access your research history and personalized features</p>
            </div>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close">
            <i className="fas fa-times"></i>
          </button>
        </div>

        {(error || loginError) && (
          <div className="error-message">
            <i className="fas fa-exclamation-triangle"></i>
            {loginError || error}
          </div>
        )}

        <div className="login-options">
          {/* Google Sign In - Most Popular */}
          <button 
            className="login-btn google-btn"
            onClick={handleGoogleSignIn}
            disabled={loading}
          >
            <div className="btn-content">
              <svg className="google-icon" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span>Continue with Google</span>
            </div>
          </button>

          {/* GitHub Sign In - Perfect for Academic */}
          <button 
            className="login-btn github-btn"
            onClick={handleGitHubSignIn}
            disabled={loading}
          >
            <div className="btn-content">
              <i className="fab fa-github"></i>
              <span>Continue with GitHub</span>
            </div>
          </button>

          <div className="divider">
            <span>or</span>
          </div>

          {/* Guest Mode - No Registration (only show for general login, not protected features) */}
          {!hideGuestMode && (
            <button 
              className="login-btn guest-btn"
              onClick={handleGuestMode}
              disabled={loading}
            >
              <div className="btn-content">
                <i className="fas fa-user-secret"></i>
                <span>Continue as Guest</span>
              </div>
            </button>
          )}
        </div>

        <div className="login-benefits">
          <h3>Why sign in?</h3>
          <div className="benefits-grid">
            <div className="benefit">
              <i className="fas fa-history"></i>
              <span>Persistent search history</span>
            </div>
            <div className="benefit">
              <i className="fas fa-bookmark"></i>
              <span>Save papers for later</span>
            </div>
            <div className="benefit">
              <i className="fas fa-sync-alt"></i>
              <span>Sync across devices</span>
            </div>
            <div className="benefit">
              <i className="fas fa-chart-line"></i>
              <span>Research analytics</span>
            </div>
          </div>
        </div>

        <div className="login-footer">
          <p>
            By signing in, you agree to save your research history and 
            access personalized features. Guest mode provides temporary access only.
          </p>
        </div>

        {loading && (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Signing you in...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default LoginModal;