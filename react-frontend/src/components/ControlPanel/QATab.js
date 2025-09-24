import React, { useCallback } from 'react';
import './QATab.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';
import { askQuestion as apiAskQuestion } from '../../services/api';
import LoadingSpinner from '../common/LoadingSpinner';
import CopyButton from '../common/CopyButton';

const QATab = () => {
  const { document, qa, updateQa } = useDocument();
  const { showError, showSuccess } = useNotification();

  const handleQuestionChange = useCallback((e) => {
    updateQa({ question: e.target.value });
  }, [updateQa]);

  const handleAskQuestion = useCallback(async () => {
    if (!document.id) {
      showError('Please upload a document first');
      return;
    }

    if (!qa.question.trim()) {
      showError('Please enter a question');
      return;
    }

    try {
      updateQa({ loading: true, error: null });

      const result = await apiAskQuestion(document.id, qa.question);
      
      updateQa({ 
        answer: result.answer,
        loading: false 
      });

      showSuccess('Answer generated with source citations!');

    } catch (error) {
      console.error('Error asking question:', error);
      updateQa({ 
        error: error.message,
        loading: false 
      });
      showError('Failed to get answer');
    }
  }, [document.id, qa.question, updateQa, showError, showSuccess]);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleAskQuestion();
    }
  }, [handleAskQuestion]);

  return (
    <div className="qa-tab">
      <div className="form-group">
        <label className="form-label" htmlFor="questionInput">
          <i className="fas fa-question"></i>
          Ask a question about your document
        </label>
        <textarea 
          id="questionInput"
          className="form-textarea"
          placeholder="What are the main findings? What methodology was used? Who are the authors?"
          rows="3"
          value={qa.question}
          onChange={handleQuestionChange}
          onKeyPress={handleKeyPress}
        />
      </div>
      
      <button 
        className="btn btn-primary btn-full"
        onClick={handleAskQuestion}
        disabled={!document.id || qa.loading || !qa.question.trim()}
      >
        <i className="fas fa-search"></i>
        {qa.loading ? 'Getting Answer...' : 'Get Answer'}
      </button>
      
      <div className="result-area">
        {qa.loading && (
          <div className="loading-container">
            <LoadingSpinner />
            <p>Analyzing document and generating answer...</p>
          </div>
        )}
        
        {qa.error && (
          <div className="error-container">
            <i className="fas fa-exclamation-triangle"></i>
            <p>Error: {qa.error}</p>
          </div>
        )}
        
        {qa.answer && !qa.loading && (
          <div className="content-container">
            <div className="content-text">
              {qa.answer}
            </div>
            <CopyButton content={qa.answer} />
          </div>
        )}
        
        {!qa.answer && !qa.loading && !qa.error && (
          <div className="placeholder-text">
            Ask a question above to get an AI-generated answer with detailed source citations...
          </div>
        )}
      </div>
    </div>
  );
};

export default QATab;