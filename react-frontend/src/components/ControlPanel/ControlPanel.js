import React from 'react';
import './ControlPanel.css';
import ChatBot from '../ChatBot/ChatBot';
import DocumentInfo from './DocumentInfo';
import { useDocument } from '../../context/DocumentContext';

const ControlPanel = () => {
  const { document } = useDocument();

  return (
    <div className="control-panel">
      {/* Progress Bar - Show during upload/processing */}
      {(document.status === 'uploading' || document.status === 'processing') && (
        <div className="progress-container">
          <div className="progress-bar-thin">
            <div 
              className="progress-fill-thin" 
              style={{ width: `${document.progress || 0}%` }}
            ></div>
          </div>
          {document.progressMessage && (
            <div className="progress-text">{document.progressMessage}</div>
          )}
        </div>
      )}

      {/* ChatBot Interface */}
      <div className="chatbot-wrapper">
        <ChatBot />
      </div>
    </div>
  );
};

export default ControlPanel;