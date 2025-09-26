import React from 'react';
import './ProgressBar.css';

const ProgressBar = ({ progress = 0, message = '', showPercentage = true, className = '' }) => {
  const clampedProgress = Math.min(Math.max(progress, 0), 100);
  
  return (
    <div className={`progress-bar-container ${className}`}>
      {message && <div className="progress-message">{message}</div>}
      <div className="progress-bar">
        <div 
          className="progress-bar-fill" 
          style={{ width: `${clampedProgress}%` }}
        >
          {showPercentage && (
            <span className="progress-percentage">{Math.round(clampedProgress)}%</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProgressBar;