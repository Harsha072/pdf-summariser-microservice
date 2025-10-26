import React, { useState } from 'react';
import './CitationChecker.css';

const CitationChecker = () => {
    const [selectedFile, setSelectedFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);

    const handleFileSelect = (event) => {
        const file = event.target.files[0];
        if (file) {
            if (file.type === 'application/pdf') {
                if (file.size <= 10 * 1024 * 1024) { // 10MB limit
                    setSelectedFile(file);
                    setError(null);
                } else {
                    setError('File size too large. Maximum 10MB allowed.');
                    setSelectedFile(null);
                }
            } else {
                setError('Please select a PDF file.');
                setSelectedFile(null);
            }
        }
    };

    const checkCitations = async () => {
        if (!selectedFile) {
            setError('Please select a PDF file first.');
            return;
        }

        setLoading(true);
        setError(null);
        setResults(null);

        try {
            const formData = new FormData();
            formData.append('pdf_file', selectedFile);

            const response = await fetch('/api/check-citations', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                setResults(data);
            } else {
                setError(data.error || 'Citation check failed');
            }
        } catch (err) {
            console.error('Citation check error:', err);
            setError('Failed to check citations. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getScoreColor = (score) => {
        if (score >= 80) return '#28a745'; // Green
        if (score >= 60) return '#ffc107'; // Yellow
        return '#dc3545'; // Red
    };

    const getScoreDescription = (score) => {
        if (score >= 80) return 'Excellent';
        if (score >= 60) return 'Good';
        if (score >= 40) return 'Fair';
        return 'Needs Improvement';
    };

    return (
        <div className="citation-checker">
            <div className="citation-checker-container">
                <div className="upload-section">
                    <h2>Citation Quality Checker</h2>
                    <p className="description">
                        Upload your research paper (PDF) to analyze citation quality and identify potential issues.
                    </p>
                    
                    <div className="file-upload">
                        <input
                            type="file"
                            id="pdf-upload"
                            accept=".pdf"
                            onChange={handleFileSelect}
                            style={{ display: 'none' }}
                        />
                        <label htmlFor="pdf-upload" className="upload-button">
                            {selectedFile ? selectedFile.name : 'Choose PDF File'}
                        </label>
                        <button 
                            className="check-button"
                            onClick={checkCitations}
                            disabled={!selectedFile || loading}
                        >
                            {loading ? 'Analyzing...' : 'Check Citations'}
                        </button>
                    </div>

                    {error && (
                        <div className="error-message">
                            {error}
                        </div>
                    )}
                </div>

                {loading && (
                    <div className="loading-indicator">
                        <div className="spinner"></div>
                        <p>Analyzing citations in your paper...</p>
                    </div>
                )}

                {results && results.success && (
                    <div className="results-section">
                        {!results.analysis && (
                            <div className="error-message" style={{margin: '20px 0'}}>
                                Analysis data is missing. Please try uploading the file again.
                            </div>
                        )}
                        {results.analysis && (
                            <>
                        <div className="score-card">
                            <h3>Citation Quality Score</h3>
                            <div 
                                className="score-circle"
                                style={{ color: getScoreColor(results.analysis.overall_score || 0) }}
                            >
                                <span className="score-number">{results.analysis.overall_score || 0}</span>
                                <span className="score-label">/100</span>
                            </div>
                            <p className="score-description">
                                {getScoreDescription(results.analysis.overall_score || 0)}
                            </p>
                        </div>

                        <div className="analysis-grid">
                            <div className="analysis-card">
                                <h4>Citation Statistics</h4>
                                <div className="stats-list">
                                    <div className="stat-item">
                                        <span>Total Citations Found:</span>
                                        <strong>{results.analysis.total_citations || 0}</strong>
                                    </div>
                                    <div className="stat-item">
                                        <span>Unique Citations:</span>
                                        <strong>{results.analysis.unique_citations || 0}</strong>
                                    </div>
                                    <div className="stat-item">
                                        <span>Issues Detected:</span>
                                        <strong className="issues-count">{results.analysis.issues_detected || 0}</strong>
                                    </div>
                                </div>
                            </div>

                            <div className="analysis-card">
                                <h4>Format Analysis</h4>
                                <div className="format-stats">
                                    {results.analysis.format_distribution && Object.entries(results.analysis.format_distribution).map(([format, count]) => (
                                        <div key={format} className="format-item">
                                            <span className="format-name">{format.toUpperCase()}:</span>
                                            <span className="format-count">{count}</span>
                                        </div>
                                    ))}
                                    {(!results.analysis.format_distribution || Object.keys(results.analysis.format_distribution).length === 0) && (
                                        <div className="no-data">No format data available</div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {results.analysis.issues && results.analysis.issues.length > 0 && (
                            <div className="issues-section">
                                <h4>Issues Found</h4>
                                <div className="issues-list">
                                    {results.analysis.issues.map((issue, index) => (
                                        <div key={index} className="issue-item">
                                            <div className="issue-type">{(issue.type || 'unknown').replace('_', ' ').toUpperCase()}</div>
                                            <div className="issue-description">{issue.description || 'No description available'}</div>
                                            {issue.examples && issue.examples.length > 0 && (
                                                <div className="issue-examples">
                                                    <strong>Examples:</strong>
                                                    <ul>
                                                        {issue.examples.slice(0, 3).map((example, i) => (
                                                            <li key={i}>{example}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {results.analysis.recommendations && results.analysis.recommendations.length > 0 && (
                            <div className="recommendations-section">
                                <h4>Recommendations</h4>
                                <ul className="recommendations-list">
                                    {results.analysis.recommendations.map((rec, index) => (
                                        <li key={index}>{rec}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <div className="analysis-details">
                            <h4>Analysis Details</h4>
                            <div className="details-grid">
                                <div className="detail-item">
                                    <span>Analysis Time:</span>
                                    <span>{results.analysis.processing_time?.toFixed(2) || 'N/A'}s</span>
                                </div>
                                <div className="detail-item">
                                    <span>Pages Analyzed:</span>
                                    <span>{results.analysis.pages_processed || 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                        </>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default CitationChecker;