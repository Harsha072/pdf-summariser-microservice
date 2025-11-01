import React, { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import '../components/common.css';
import './UserProfile.css';

const UserProfile = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      navigate('/');
    }
  }, [user, navigate]);

  const handleSignOut = async () => {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Sign out failed:', error);
    }
  };

  const getProviderName = () => {
    if (user.isAnonymous) return 'Guest';
    if (user.providerId?.includes('google')) return 'Google';
    if (user.providerId?.includes('github')) return 'GitHub';
    return 'Email';
  };

  const getProviderIcon = () => {
    if (user.isAnonymous) return 'fa-user-secret';
    if (user.providerId?.includes('google')) return 'fab fa-google';
    if (user.providerId?.includes('github')) return 'fab fa-github';
    return 'fa-envelope';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!user) {
    return null;
  }

  return (
    <div className="page-container profile-page">
      <div className="page-header">
        <h1 className="page-title">
          <i className="fas fa-user-circle"></i>
          User Profile
        </h1>
        <p className="page-description">
          Manage your account and view your research activity
        </p>
      </div>

      <div className="profile-content">
        {/* Profile Header Card */}
        <div className="profile-header-card">
          <div className="profile-photo-section">
            {user.photoURL ? (
              <img 
                src={user.photoURL} 
                alt={user.displayName || 'User'} 
                className="profile-photo-large"
              />
            ) : (
              <div className="profile-photo-placeholder">
                <i className={user.isAnonymous ? 'fas fa-user-secret' : 'fas fa-user'}></i>
              </div>
            )}
          </div>
          
          <div className="profile-header-info">
            <h2 className="profile-display-name">
              {user.isAnonymous ? 'Guest User' : (user.displayName || 'User')}
            </h2>
            <p className="profile-email-display">
              {user.email || 'No email provided'}
              {user.emailVerified && !user.isAnonymous && (
                <span className="verified-badge">
                  <i className="fas fa-check-circle"></i> Verified
                </span>
              )}
            </p>
            <p className="profile-member-since">
              <i className="fas fa-calendar-alt"></i>
              Member since {formatDate(user.createdAt)}
            </p>
          </div>
        </div>

        {/* Account Information Section */}
        <div className="profile-section">
          <h3 className="section-title">
            <i className="fas fa-info-circle"></i>
            Account Information
          </h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">
                <i className={getProviderIcon()}></i>
                Authentication Provider
              </span>
              <span className="info-value">{getProviderName()}</span>
            </div>
            
            <div className="info-item">
              <span className="info-label">
                <i className="fas fa-user-tag"></i>
                Account Type
              </span>
              <span className="info-value">
                {user.isAnonymous ? (
                  <span className="badge badge-warning">Guest Session</span>
                ) : (
                  <span className="badge badge-success">Registered User</span>
                )}
              </span>
            </div>
            
            <div className="info-item">
              <span className="info-label">
                <i className="fas fa-envelope-open-text"></i>
                Email Status
              </span>
              <span className="info-value">
                {user.isAnonymous ? 'N/A' : (user.emailVerified ? (
                  <span className="badge badge-success">Verified</span>
                ) : (
                  <span className="badge badge-warning">Not Verified</span>
                ))}
              </span>
            </div>
            
            <div className="info-item">
              <span className="info-label">
                <i className="fas fa-clock"></i>
                Last Sign In
              </span>
              <span className="info-value">{formatDateTime(user.lastLoginAt)}</span>
            </div>
            
            <div className="info-item">
              <span className="info-label">
                <i className="fas fa-fingerprint"></i>
                User ID
              </span>
              <span className="info-value mono-text">{user.uid}</span>
            </div>
          </div>
        </div>

        {/* Guest User Notice */}
        {user.isAnonymous && (
          <div className="profile-section guest-notice">
            <div className="notice-icon">
              <i className="fas fa-info-circle"></i>
            </div>
            <div className="notice-content">
              <h4>Guest Session</h4>
              <p>You're using Scholar Quest as a guest. Your data is temporary and will be lost when you sign out.</p>
              <p><strong>Sign in with Google or GitHub to:</strong></p>
              <ul>
                <li>Save your search history permanently</li>
                <li>Sync bookmarks across devices</li>
                <li>Access advanced features</li>
              </ul>
            </div>
          </div>
        )}

        {/* Actions Section */}
        <div className="profile-actions">
          <button className="btn-secondary" onClick={() => navigate('/history')}>
            <i className="fas fa-history"></i>
            View Search History
          </button>
          
          <button className="btn-secondary" onClick={() => navigate('/saved')}>
            <i className="fas fa-bookmark"></i>
            View Saved Papers
          </button>
          
          <button className="btn-danger" onClick={handleSignOut}>
            <i className="fas fa-sign-out-alt"></i>
            {user.isAnonymous ? 'End Session' : 'Sign Out'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;

