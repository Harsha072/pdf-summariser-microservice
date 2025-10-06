import React, { useState } from 'react';
import './ControlPanel.css';
import CitationTab from './CitationTab';
import QATab from './QATab';
import SummaryTab from './SummaryTab';
import { useDocument } from '../../context/DocumentContext';

const ControlPanel = () => {
  const { document } = useDocument();
  const [activeTab, setActiveTab] = useState('citations'); // Default to citations

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

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button 
          className={`tab-button ${activeTab === 'citations' ? 'active' : ''}`}
          onClick={() => setActiveTab('citations')}
        >
          <i className="fas fa-quote-right"></i>
          Citation Extractor
        </button>
        <button 
          className={`tab-button ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          <i className="fas fa-file-text"></i>
          Summary
        </button>
        <button 
          className={`tab-button ${activeTab === 'qa' ? 'active' : ''}`}
          onClick={() => setActiveTab('qa')}
        >
          <i className="fas fa-question-circle"></i>
          Q&A
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'citations' && <CitationTab />}
        {activeTab === 'summary' && <SummaryTab />}
        {activeTab === 'qa' && <QATab />}
      </div>
    </div>
  );
};

export default ControlPanel;