import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { ProtectedFeature } from '../Auth/InlineAuth';
import './ProtectedPaperFeatures.css';

/**
 * ProtectedPaperActions - Shows paper actions with inline auth for protected features
 */
const ProtectedPaperActions = ({ 
  paper, 
  index, 
  onViewDetails, 
  onDownloadPaper,
  onBuildGraph,
  isBuildingGraph = false
}) => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="paper-actions">
      {/* View AI Analysis - Protected Feature */}
      <ProtectedFeature
        feature="view detailed AI analysis"
        compact={true}
        showBenefits={false}
        fallback={
          <div className="protected-action-placeholder">
            <button className="action-button details disabled">
              View AI Analysis
            </button>
            <div className="auth-hint">
              <small>Sign in to view detailed AI analysis</small>
              <div className="quick-auth-buttons">
                <AuthQuickButton feature="view analysis" />
              </div>
            </div>
          </div>
        }
      >
        <button 
          onClick={() => onViewDetails(paper, index)}
          className="action-button details"
        >
          View AI Analysis
        </button>
      </ProtectedFeature>

      {/* Download PDF - Protected Feature */}
      {paper.pdf_url && (
        <ProtectedFeature
          feature="download papers"
          compact={true}
          showBenefits={false}
          fallback={
            <div className="protected-action-placeholder">
              <button className="action-button download disabled">
                Download PDF
              </button>
              <div className="auth-hint">
                <small>Sign in to download papers</small>
                <div className="quick-auth-buttons">
                  <AuthQuickButton feature="download papers" />
                </div>
              </div>
            </div>
          }
        >
          <button 
            onClick={() => onDownloadPaper(paper.pdf_url, paper.title)}
            className="action-button download"
          >
            Download PDF
          </button>
        </ProtectedFeature>
      )}

      {/* Build Graph - Always Available */}
      {(paper.paper_id || paper.id) ? (
        <button 
          onClick={() => onBuildGraph && onBuildGraph(paper)}
          className="action-button graph"
          title="Build network analysis graph for this paper"
        >
          Build Graph
        </button>
      ) : (
        <button 
          className="action-button graph disabled"
          title="Graph building not available for this paper (missing paper ID)"
          disabled
        >
          Build Graph (N/A)
        </button>
      )}

      {/* Open Online - Always Available */}
      {paper.url && (
        <button 
          onClick={() => window.open(paper.url, '_blank')}
          className="action-button external"
        >
          Open Online
        </button>
      )}
    </div>
  );
};

/**
 * AuthQuickButton - Quick authentication button for inline use
 */
const AuthQuickButton = ({ feature }) => {
  const { signInWithGoogle } = useAuth();
  const [loading, setLoading] = React.useState(false);

  const handleQuickAuth = async () => {
    try {
      setLoading(true);
      await signInWithGoogle();
    } catch (error) {
      console.error('Quick auth failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button 
      className="quick-auth-btn-mini"
      onClick={handleQuickAuth}
      disabled={loading}
      title={`Sign in with Google to ${feature}`}
    >
      {loading ? '...' : 'Sign In'}
    </button>
  );
};

/**
 * Alternative approach - Replace the entire paper card actions section
 */
export const SmartPaperActions = ({ 
  paper, 
  index, 
  onViewDetails, 
  onDownloadPaper,
  onBuildGraph,
  isBuildingGraph = false
}) => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return (
      <div className="paper-actions-protected">
        <div className="protected-features-notice">
          <div className="notice-content">
            <span className="notice-icon"></span>
            <div className="notice-text">
              <strong>Sign in for full access</strong>
              <p>View detailed AI analysis and build paper networks</p>
            </div>
          </div>
          <div className="notice-actions">
            <AuthQuickButton feature="access all features" />
          </div>
        </div>
        
        {/* Show available actions */}
        <div className="available-actions">
          {/* Build Graph - Always Available */}
          {(paper.paper_id || paper.id) ? (
            <button 
              onClick={() => onBuildGraph && onBuildGraph(paper)}
              className="action-button graph"
              title="Build network analysis graph for this paper"
              disabled={isBuildingGraph}
            >
              {isBuildingGraph ? 'Building...' : 'Build Graph'}
            </button>
          ) : (
            <button 
              className="action-button graph disabled"
              title="Graph building not available for this paper (missing paper ID)"
              disabled
            >
              Build Graph (N/A)
            </button>
          )}
        </div>
      </div>
    );
  }

  // User is authenticated - show only View AI Analysis and Build Graph
  return (
    <div className="paper-actions">
      <button 
        onClick={() => onViewDetails(paper, index)}
        className="action-button details"
      >
        View AI Analysis
      </button>
      
      {/* Build Graph - Always Available */}
      {(paper.paper_id || paper.id) ? (
        <button 
          onClick={() => onBuildGraph && onBuildGraph(paper)}
          className="action-button graph"
          title="Build network analysis graph for this paper"
          disabled={isBuildingGraph}
        >
          {isBuildingGraph ? 'Building...' : 'Build Graph'}
        </button>
      ) : (
        <button 
          className="action-button graph disabled"
          title="Graph building not available for this paper (missing paper ID)"
          disabled
        >
          Build Graph (N/A)
        </button>
      )}
    </div>
  );
};

export default ProtectedPaperActions;