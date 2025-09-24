import React, { useState } from 'react';
import './ControlPanel.css';
import DocumentInfo from './DocumentInfo';
import SummaryTab from './SummaryTab';
import QATab from './QATab';
import { useDocument } from '../../context/DocumentContext';

const ControlPanel = () => {
  const { document } = useDocument();
  const [activeTab, setActiveTab] = useState('summary');

  return (
    <div className="control-panel">
      {/* Document Info Card */}
      {document.id && (
        <DocumentInfo />
      )}

      {/* Features Card */}
      <div className="control-card">
        <div className="card-header">
          <i className="fas fa-robot card-icon"></i>
          <h2>AI Analysis</h2>
        </div>
        <div className="card-content">
          {/* Feature Tabs */}
          <div className="feature-tabs">
            <button 
              className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
              onClick={() => setActiveTab('summary')}
            >
              <i className="fas fa-file-alt"></i> Summary
            </button>
            <button 
              className={`tab-btn ${activeTab === 'qa' ? 'active' : ''}`}
              onClick={() => setActiveTab('qa')}
            >
              <i className="fas fa-question-circle"></i> Q&A
            </button>
          </div>

          {/* Tab Content */}
          <div className="tab-content-area">
            {activeTab === 'summary' && <SummaryTab />}
            {activeTab === 'qa' && <QATab />}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;