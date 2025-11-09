import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import LoginModal from './LoginModal';
import './UserProfile.css';

const UserProfile = () => {
  const { user, logout, isAnonymous } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  const handleSignOut = async () => {
    try {
      await logout();
      setShowDropdown(false);
    } catch (error) {
      console.error('Sign out failed:', error);
    }
  };

  const openLoginModal = () => {
    setShowLoginModal(true);
    setShowDropdown(false);
  };

  if (!user) {
    return (
      <>
        <button className="login-trigger-btn" onClick={openLoginModal}>
          <i className="fas fa-user"></i>
          <span>Sign In</span>
        </button>
        <LoginModal 
          isOpen={showLoginModal} 
          onClose={() => setShowLoginModal(false)} 
        />
      </>
    );
  }

  return (
    <>
      <div className="user-profile-container">
        <button 
          className="user-profile-btn"
          onClick={() => setShowDropdown(!showDropdown)}
          aria-label="User menu"
        >
          {user.photoURL ? (
            <img 
              src={user.photoURL} 
              alt={user.displayName || user.email}
              className="user-avatar"
            />
          ) : (
            <div className="user-avatar-placeholder">
              <i className={isAnonymous ? "fas fa-user-secret" : "fas fa-user"}></i>
            </div>
          )}
          <div className="user-info">
            <span className="user-name">
              {isAnonymous ? 'Guest User' : (user.displayName || user.email)}
            </span>
            <span className="user-status">
              {isAnonymous ? 'Anonymous Session' : 'Signed In'}
            </span>
          </div>
          <i className={`fas fa-chevron-down dropdown-arrow ${showDropdown ? 'open' : ''}`}></i>
        </button>

        {showDropdown && (
          <div className="user-dropdown">
            <div className="dropdown-header">
              <div className="user-details">
                {user.photoURL ? (
                  <img 
                    src={user.photoURL} 
                    alt={user.displayName || user.email}
                    className="dropdown-avatar"
                  />
                ) : (
                  <div className="dropdown-avatar-placeholder">
                    <i className={isAnonymous ? "fas fa-user-secret" : "fas fa-user"}></i>
                  </div>
                )}
                <div className="user-text">
                  <div className="dropdown-name">
                    {isAnonymous ? 'Guest User' : (user.displayName || 'User')}
                  </div>
                  <div className="dropdown-email">
                    {isAnonymous ? 'Temporary session' : (user.email || 'No email')}
                  </div>
                  {!isAnonymous && (
                    <div className="user-provider">
                      <i className={`fab fa-${user.providerId === 'google.com' ? 'google' : user.providerId === 'github.com' ? 'github' : 'user'}`}></i>
                      <span>{user.providerId === 'google.com' ? 'Google' : user.providerId === 'github.com' ? 'GitHub' : 'Account'}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="dropdown-menu">
              {isAnonymous ? (
                <>
                  <button className="dropdown-item upgrade-btn" onClick={openLoginModal}>
                    <i className="fas fa-user-plus"></i>
                    <div>
                      <span>Create Account</span>
                      <small>Save your research permanently</small>
                    </div>
                  </button>
                  <div className="dropdown-divider"></div>
                </>
              ) : (
                <div className="dropdown-divider"></div>
              )}
              
              <a href="/help" className="dropdown-item">
                <i className="fas fa-question-circle"></i>
                <span>Help & Support</span>
              </a>
              
              <div className="dropdown-divider"></div>
              
              <button className="dropdown-item sign-out-btn" onClick={handleSignOut}>
                <i className="fas fa-sign-out-alt"></i>
                <span>{isAnonymous ? 'End Session' : 'Sign Out'}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      <LoginModal 
        isOpen={showLoginModal} 
        onClose={() => setShowLoginModal(false)} 
      />

      {/* Backdrop to close dropdown */}
      {showDropdown && (
        <div 
          className="dropdown-backdrop" 
          onClick={() => setShowDropdown(false)}
        ></div>
      )}
    </>
  );
};

export default UserProfile;