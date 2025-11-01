import React from 'react';
import '../components/common.css';

const HelpGuide = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <i className="fas fa-question-circle"></i>
          Help & Guide
        </h1>
        <p className="page-description">
          Learn how to use the Academic Paper Discovery Engine effectively
        </p>
      </div>

      <div className="content-section">
        <div className="help-grid">
          <div className="help-card">
            <div className="help-icon">
              <i className="fas fa-search"></i>
            </div>
            <h3>How to Search</h3>
            <p>Enter keywords, topics, or research questions to discover relevant academic papers using AI-powered search.</p>
          </div>

          <div className="help-card">
            <div className="help-icon">
              <i className="fas fa-filter"></i>
            </div>
            <h3>Advanced Filtering</h3>
            <p>Use filters to narrow down results by publication date, journal, author, or research domain.</p>
          </div>

          <div className="help-card">
            <div className="help-icon">
              <i className="fas fa-bookmark"></i>
            </div>
            <h3>Save & Organize</h3>
            <p>Bookmark interesting papers and organize them into collections for future reference.</p>
          </div>

          <div className="help-card">
            <div className="help-icon">
              <i className="fas fa-robot"></i>
            </div>
            <h3>AI Analysis</h3>
            <p>Get AI-powered summaries, key insights, and research recommendations for each paper.</p>
          </div>
        </div>

        <div className="faq-section">
          <h3>Frequently Asked Questions</h3>
          <div className="faq-item">
            <details>
              <summary>How does the AI search work?</summary>
              <p>Our AI uses advanced natural language processing to understand your research intent and find the most relevant papers from academic databases.</p>
            </details>
          </div>
          
          <div className="faq-item">
            <details>
              <summary>Can I access full paper texts?</summary>
              <p>We provide abstracts and metadata. For full texts, you'll be directed to the original publisher or repository where the paper is hosted.</p>
            </details>
          </div>
          
          <div className="faq-item">
            <details>
              <summary>Is my search history saved?</summary>
              <p>Yes, your search history is saved locally to help you track your research progress and revisit previous queries.</p>
            </details>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HelpGuide;