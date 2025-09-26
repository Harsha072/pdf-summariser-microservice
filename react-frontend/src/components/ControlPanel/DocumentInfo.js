import React, { useState } from 'react';
import './DocumentInfo.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';
import { 
  analyzePaper, 
  generateResearchQuestions, 
  explainConcept,
  getSectionSummary,
  askAcademicQuestion 
} from '../../services/api';

const DocumentInfo = () => {
  const { document } = useDocument();
  const { showError, showSuccess, showInfo } = useNotification();
  const [paperAnalysis, setPaperAnalysis] = useState(null);
  const [researchQuestions, setResearchQuestions] = useState(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingQuestions, setLoadingQuestions] = useState(false);

  const handleAnalyzePaper = async () => {
    if (!document.id) {
      showError('Please upload a document first');
      return;
    }

    setLoadingAnalysis(true);
    try {
      const analysis = await analyzePaper(document.id);
      setPaperAnalysis(analysis);
      showSuccess('Paper analysis completed!');
    } catch (error) {
      showError(`Analysis failed: ${error.message}`);
      console.error('Paper analysis error:', error);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleGenerateQuestions = async () => {
    if (!document.id) {
      showError('Please upload a document first');
      return;
    }

    setLoadingQuestions(true);
    try {
      const questions = await generateResearchQuestions(document.id);
      setResearchQuestions(questions);
      showSuccess('Research questions generated!');
    } catch (error) {
      showError(`Question generation failed: ${error.message}`);
      console.error('Question generation error:', error);
    } finally {
      setLoadingQuestions(false);
    }
  };

  return (
    <div className="control-card document-info">
      {/* <div className="card-header">
        <i className="fas fa-info-circle card-icon"></i>
        <h2>Status</h2>
      </div> */}
      <div className="card-content">
        <div className="info-grid">
          <div className="info-item">
            <strong>Status:</strong> 
            <span className={`status ${document.status}`}>
              {document.status === 'ready' ? 'Ready' : 
               document.status === 'uploading' ? 'Uploading...' :
               document.status === 'processing' ? 'Processing...' :
               document.status === 'error' ? 'Error' : '-'}
            </span>
          </div>
        </div>

        {/* Academic Tools */}
        {document.status === 'ready' && (
          <div className="academic-tools">
            <h3>📚 Academic Tools</h3>
            <div className="tool-buttons">
              <button 
                className="tool-btn"
                onClick={handleAnalyzePaper}
                disabled={loadingAnalysis}
              >
                <i className="fas fa-brain"></i>
                {loadingAnalysis ? 'Analyzing...' : 'Analyze Paper'}
              </button>
              
              <button 
                className="tool-btn"
                onClick={handleGenerateQuestions}
                disabled={loadingQuestions}
              >
                <i className="fas fa-question-circle"></i>
                {loadingQuestions ? 'Generating...' : 'Research Questions'}
              </button>
            </div>

            {/* Paper Analysis Results */}
            {paperAnalysis && (
              <div className="analysis-results">
                <h4>📊 Paper Analysis</h4>
                {paperAnalysis.research_focus && (
                  <div className="analysis-item">
                    <strong>🎯 Research Focus:</strong>
                    <p>{paperAnalysis.research_focus}</p>
                  </div>
                )}
                {paperAnalysis.paper_type && (
                  <div className="analysis-item">
                    <strong>📑 Paper Type:</strong>
                    <span className="paper-type-badge">{paperAnalysis.paper_type}</span>
                  </div>
                )}
                {paperAnalysis.research_question && (
                  <div className="analysis-item">
                    <strong>❓ Research Question:</strong>
                    <p>{paperAnalysis.research_question}</p>
                  </div>
                )}
                {paperAnalysis.key_findings && (
                  <div className="analysis-item">
                    <strong>🔍 Key Findings:</strong>
                    <div className="findings-list">
                      {Array.isArray(paperAnalysis.key_findings) ? 
                        paperAnalysis.key_findings.map((finding, idx) => (
                          <div key={idx} className="finding-item">• {finding}</div>
                        )) : 
                        <p>{paperAnalysis.key_findings}</p>
                      }
                    </div>
                  </div>
                )}
                {paperAnalysis.methodology && (
                  <div className="analysis-item">
                    <strong>🔬 Methodology:</strong>
                    <p>{paperAnalysis.methodology}</p>
                  </div>
                )}
                {paperAnalysis.contributions && (
                  <div className="analysis-item">
                    <strong>💡 Main Contributions:</strong>
                    <p>{paperAnalysis.contributions}</p>
                  </div>
                )}
                {paperAnalysis.document_structure && (
                  <div className="analysis-item">
                    <strong>📖 Document Structure:</strong>
                    <p>
                      {paperAnalysis.document_structure.total_pages} pages, 
                      {' ' + Object.keys(paperAnalysis.document_structure.sections || {}).length} sections identified
                    </p>
                  </div>
                )}
                {paperAnalysis.raw_analysis && !paperAnalysis.research_focus && (
                  <div className="analysis-item">
                    <strong>📝 Analysis:</strong>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>
                      {paperAnalysis.raw_analysis}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Research Questions Results */}
            {researchQuestions && (
              <div className="questions-results">
                <h4>🤔 Research Questions</h4>
                <div className="questions-content">
                  <pre>{researchQuestions.questions}</pre>
                </div>
                <small style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                  Generated at: {new Date(researchQuestions.generated_at * 1000).toLocaleString()}
                </small>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentInfo;