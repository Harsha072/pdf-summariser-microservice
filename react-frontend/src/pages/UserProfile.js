import React from 'react';
import '../components/common.css';

const UserProfile = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <i className="fas fa-user-circle"></i>
          User Profile
        </h1>
        <p className="page-description">
          Manage your account settings and research preferences
        </p>
      </div>

      <div className="content-section">
        <div className="profile-card">
          <div className="profile-avatar">
            <i className="fas fa-user-graduate"></i>
          </div>
          <div className="profile-info">
            <h3>Research User</h3>
            <p className="profile-email">researcher@example.com</p>
            <div className="profile-stats">
              <div className="stat">
                <span className="stat-number">0</span>
                <span className="stat-label">Searches</span>
              </div>
              <div className="stat">
                <span className="stat-number">0</span>
                <span className="stat-label">Saved Papers</span>
              </div>
              <div className="stat">
                <span className="stat-number">0</span>
                <span className="stat-label">Collections</span>
              </div>
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h3>Preferences</h3>
          <div className="setting-item">
            <label>Research Domain</label>
            <select className="form-control">
              <option>Computer Science</option>
              <option>Biology</option>
              <option>Physics</option>
              <option>Mathematics</option>
              <option>Other</option>
            </select>
          </div>
          
          <div className="setting-item">
            <label>Default Search Filters</label>
            <div className="checkbox-group">
              <label className="checkbox-label">
                <input type="checkbox" />
                Only peer-reviewed papers
              </label>
              <label className="checkbox-label">
                <input type="checkbox" />
                Last 5 years only
              </label>
              <label className="checkbox-label">
                <input type="checkbox" />
                Open access papers
              </label>
            </div>
          </div>

          <div className="setting-item">
            <button className="btn btn-primary">Save Preferences</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;