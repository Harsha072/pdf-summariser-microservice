import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './PaperDetails.css';
import { getPaperDetails } from '../../services/api';

const PaperDetails = () => {
  const { paperId } = useParams();
  const navigate = useNavigate();
  const [paper, setPaper] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    // Get paper data from localStorage or sessionStorage
    const storedPaper = localStorage.getItem(`paper_${paperId}`);
    if (storedPaper) {
      const paperData = JSON.parse(storedPaper);
      setPaper(paperData);
      fetchPaperAnalysis(paperData);
    } else {
      setError('Paper data not found');
    }
  }, [paperId]);

  const fetchPaperAnalysis = async (paperData) => {
    try {
      const response = await getPaperDetails(paperData);
      
      if (response.success) {
        setAnalysis(response.detailed_analysis);
      } else {
        setError(response.error || 'Failed to generate analysis');
      }
    } catch (error) {
      console.error('Error fetching paper analysis:', error);
      setError('Failed to load paper analysis');
    }
  };

  const handleBackClick = () => {
    navigate(-1);
  };

  const getDifficultyColor = (difficulty) => {
    switch (difficulty) {
      case 'beginner': return '#28a745';
      case 'intermediate': return '#ffc107';
      case 'advanced': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const getImpactColor = (score) => {
    if (score >= 90) return '#28a745';
    if (score >= 75) return '#17a2b8';
    if (score >= 60) return '#ffc107';
    return '#dc3545';
  };

  if (error) {
    return (
      <div className="paper-details">
        <div className="error-container">
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={handleBackClick} className="back-button">
            ← Back to Results
          </button>
        </div>
      </div>
    );
  }

  if (!paper || !analysis) {
    return (
      <div className="paper-details">
        <div className="error-container">
          <h2>Paper Not Found</h2>
          <p>The requested paper details could not be loaded.</p>
          <button onClick={handleBackClick} className="back-button">
            ← Back to Results
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="paper-details">
      <div className="paper-details-header">
        <button onClick={handleBackClick} className="back-button">
          ← Back to Results
        </button>
        <div className="paper-source-badge">
          {paper.source}
        </div>
      </div>

      <div className="paper-details-content">
        {/* Paper Title and Basic Info */}
        <div className="paper-header-section">
          <h1 className="paper-details-title">{paper.title}</h1>
          
          <div className="paper-meta-info">
            <div className="meta-item">
              <span className="meta-label">Authors:</span>
              <span className="meta-value">
                {paper.authors && paper.authors.length > 0 
                  ? paper.authors.slice(0, 5).join(', ')
                  : 'Unknown Authors'}
              </span>
            </div>
            
            {paper.published && (
              <div className="meta-item">
                <span className="meta-label">Published:</span>
                <span className="meta-value">{paper.published}</span>
              </div>
            )}
            
            {paper.citation_count !== undefined && (
              <div className="meta-item">
                <span className="meta-label">Citations:</span>
                <span className="meta-value">{paper.citation_count}</span>
              </div>
            )}
            
            {paper.journal && (
              <div className="meta-item">
                <span className="meta-label">Journal:</span>
                <span className="meta-value">{paper.journal}</span>
              </div>
            )}
          </div>

          <div className="paper-scores">
            <div className="score-item circular">
              <div className="circular-score relevance">
                <div className="score-circle">
                  <span className="score-number">{Math.round(paper.relevance_score || 0)}</span>
                  <span className="score-unit">%</span>
                </div>
              </div>
              <span className="score-label">Relevance Score</span>
            </div>
            <div className="score-item circular">
              <div className="circular-score impact" style={{borderColor: getImpactColor(analysis.impact_score)}}>
                <div className="score-circle">
                  <span className="score-number">{analysis.impact_score}</span>
                  <span className="score-unit">/100</span>
                </div>
              </div>
              <span className="score-label">Impact Score</span>
            </div>
            <div className="score-item">
              <span className="score-label">Difficulty</span>
              <span className="score-value difficulty" style={{color: getDifficultyColor(analysis.reading_difficulty)}}>
                {analysis.reading_difficulty}
              </span>
            </div>
            <div className="score-item">
              <span className="score-label">Reading Time</span>
              <span className="score-value time">
                {analysis.estimated_reading_time}
              </span>
            </div>
          </div>
        </div>

        {/* AI-Generated Analysis */}
        <div className="analysis-section">
          <h2>AI-Generated Analysis</h2>
          
          <div className="analysis-grid">
            {/* Brief Summary */}
            <div className="analysis-card full-width">
              <h3>Brief Summary</h3>
              <p className="brief-summary">{analysis.brief_summary}</p>
            </div>

            {/* Detailed Summary */}
            <div className="analysis-card full-width">
              <h3>Detailed Analysis</h3>
              <div className="detailed-summary">
                {analysis.detailed_summary.split('\n').map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
            </div>

            {/* Key Contributions */}
            <div className="analysis-card">
              <h3>Key Contributions</h3>
              <ul className="contribution-list">
                {analysis.key_contributions.map((contribution, index) => (
                  <li key={index}>{contribution}</li>
                ))}
              </ul>
            </div>

            {/* Methodology */}
            <div className="analysis-card">
              <h3>Methodology</h3>
              <p>{analysis.methodology}</p>
            </div>

            {/* Practical Applications */}
            <div className="analysis-card">
              <h3>Practical Applications</h3>
              <ul className="applications-list">
                {analysis.practical_applications.map((application, index) => (
                  <li key={index}>{application}</li>
                ))}
              </ul>
            </div>

            {/* Strengths and Limitations */}
            <div className="analysis-card">
              <h3>Strengths</h3>
              <ul className="strengths-list">
                {analysis.strengths.map((strength, index) => (
                  <li key={index}>{strength}</li>
                ))}
              </ul>
            </div>

            <div className="analysis-card">
              <h3>Limitations</h3>
              <ul className="limitations-list">
                {analysis.limitations.map((limitation, index) => (
                  <li key={index}>{limitation}</li>
                ))}
              </ul>
            </div>

            {/* Target Audience and Related Topics */}
            <div className="analysis-card">
              <h3>Target Audience</h3>
              <p>{analysis.target_audience}</p>
            </div>

            <div className="analysis-card">
              <h3>Related Topics</h3>
              <div className="related-topics">
                {analysis.related_topics.map((topic, index) => (
                  <span key={index} className="topic-tag">{topic}</span>
                ))}
              </div>
            </div>

            {/* Recommendation */}
            <div className="analysis-card full-width recommendation-card">
              <h3>AI Recommendation</h3>
              <p className="recommendation-text">{analysis.recommendation}</p>
            </div>
          </div>
        </div>

        {/* Original Abstract */}
        {paper.summary && (
          <div className="original-abstract-section">
            <h2>Original Abstract</h2>
            <div className="original-abstract">
              <p>{paper.summary}</p>
            </div>
          </div>
        )}

        {/* Paper Actions */}
        <div className="paper-actions-section">
          <h2>Access & Explore</h2>
          <div className="action-buttons">
            <button
              onClick={() => navigate(`/paper-relationships?paperId=${encodeURIComponent(paper.id || paper.url || paperId)}`)}
              className="action-button relationships"
            >
              Explore Paper Relationships
            </button>
            
            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                className="action-button external"
              >
                View Paper Online
              </a>
            )}
            
            {paper.pdf_url && paper.pdf_url !== paper.url && (
              <a
                href={paper.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="action-button download"
              >
                Download PDF
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PaperDetails;