import React from 'react';
import './ControlPanel.css';
import ChatBot from '../ChatBot/ChatBot';
import { useDocument } from '../../context/DocumentContext';

const ControlPanel = () => {
  const { document } = useDocument();

  return (
    <div className="control-panel">
      {/* Popup Alert Overlay - Show during upload/processing */}
      {(document.status === 'uploading' || document.status === 'processing') && (
        <div className="popup-overlay">
          <div className="popup-alert">
            <div className="popup-content">
              <div className="processing-spinner"></div>
              <div className="processing-message">
                <h4>Analysing document</h4>
                <p>Please wait while we process your document...</p>
              </div>
            </div>
          </div>
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