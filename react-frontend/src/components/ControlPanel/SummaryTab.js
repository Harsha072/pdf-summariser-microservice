import React, { useCallback } from 'react';
import './SummaryTab.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';
import { generateSummary as apiGenerateSummary } from '../../services/api';
import LoadingSpinner from '../common/LoadingSpinner';
import CopyButton from '../common/CopyButton';

const SummaryTab = () => {
  const { document, summary, updateSummary } = useDocument();
  const { showError, showSuccess } = useNotification();

  const handleGenerateSummary = useCallback(async () => {
    if (!document.id) {
      showError('Please upload a document first');
      return;
    }

    try {
      updateSummary({ loading: true, error: null });

      const result = await apiGenerateSummary(document.id);
      
      updateSummary({ 
        content: result.answer,
        loading: false 
      });

      showSuccess('Summary generated successfully!');

    } catch (error) {
      console.error('Error generating summary:', error);
      updateSummary({ 
        error: error.message,
        loading: false 
      });
      showError('Failed to generate summary');
    }
  }, [document.id, updateSummary, showError, showSuccess]);

  return (
    <div className="summary-tab">
      <button 
        className="btn btn-primary btn-full"
        onClick={handleGenerateSummary}
        disabled={!document.id || summary.loading}
      >
        <i className="fas fa-magic"></i>
        {summary.loading ? 'Generating...' : 'Generate Summary'}
      </button>
      
      <div className="result-area">
        {summary.loading && (
          <div className="loading-container">
            <LoadingSpinner />
            <p>Generating comprehensive summary...</p>
          </div>
        )}
        
        {summary.error && (
          <div className="error-container">
            <i className="fas fa-exclamation-triangle"></i>
            <p>Error: {summary.error}</p>
          </div>
        )}
        
        {summary.content && !summary.loading && (
          <div className="content-container">
            <div className="content-text">
              {summary.content}
            </div>
            <CopyButton content={summary.content} />
          </div>
        )}
        
        {!summary.content && !summary.loading && !summary.error && (
          <div className="placeholder-text">
            Upload a PDF document and click "Generate Summary" to see an AI-powered analysis...
          </div>
        )}
      </div>
    </div>
  );
};

export default SummaryTab;