import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import SimplePaperRelationships from '../components/SimplePaperRelationships';
import './SimplePaperRelationshipsPage.css';

const SimplePaperRelationshipsPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [currentPaperId, setCurrentPaperId] = useState('');
  const [inputPaperId, setInputPaperId] = useState('');
  const [recentPapers, setRecentPapers] = useState([]);
  const [paperTitle, setPaperTitle] = useState('');
  const [prefetchedGraphData, setPrefetchedGraphData] = useState(null);

  useEffect(() => {
    // Check if we have state from the discovery page
    if (location.state?.paperId) {
      const { paperId, paperTitle: title, openalexWorkId, graphData, error } = location.state;
      console.log('📊 Building graph from discovery page for:', paperId, title);
      
      // Log if we received an OpenAlex work ID
      if (openalexWorkId) {
        console.log('🔗 Received OpenAlex work ID:', openalexWorkId);
      }
      
      // Log if we received pre-fetched graph data
      if (graphData) {
        console.log('📈 Received pre-fetched graph data:', graphData);
      }
      
      // Log if there was an error during graph building
      if (error) {
        console.log('❌ Error from discovery page:', error);
      }
      
      setCurrentPaperId(paperId);
      setInputPaperId(paperId);
      setPaperTitle(title || '');
      
      // Store prefetched graph data if available
      if (graphData) {
        setPrefetchedGraphData(graphData);
      }
      
      addToRecentPapers(paperId);
      
      // Update URL params
      setSearchParams({ paperId: paperId });
      
      // Clear the state to prevent re-triggering
      navigate(location.pathname, { state: null, replace: true });
      return;
    }

    // Get paper ID from URL params if provided
    const paperId = searchParams.get('paperId');
    if (paperId) {
      setCurrentPaperId(paperId);
      setInputPaperId(paperId);
      addToRecentPapers(paperId);
    }
  }, [searchParams, location.state, location.pathname, navigate, setSearchParams]);

  const handlePaperClick = (paperId) => {
    if (paperId) {
      setCurrentPaperId(paperId);
      setInputPaperId(paperId);
      setSearchParams({ paperId: paperId });
      addToRecentPapers(paperId);
      // Clear prefetched data when clicking on a different paper
      setPrefetchedGraphData(null);
    }
  };

  const addToRecentPapers = (paperId) => {
    setRecentPapers(prev => {
      // Remove if already exists, then add to front
      const filtered = prev.filter(id => id !== paperId);
      return [paperId, ...filtered].slice(0, 5); // Keep only last 5
    });
  };

  const clearRecentPapers = () => {
    setRecentPapers([]);
  };

  const handleExamplePaper = (exampleId) => {
    setInputPaperId(exampleId);
    setCurrentPaperId(exampleId);
    setSearchParams({ paperId: exampleId });
    addToRecentPapers(exampleId);
  };

  // Example papers for demonstration
  const examplePapers = [
    {
      id: '1706.03762',
      title: 'Attention Is All You Need',
      description: 'The famous Transformer paper - great for seeing foundational AI research'
    },
    {
      id: '2010.11929',
      title: 'An Image is Worth 16x16 Words',
      description: 'Vision Transformer paper - shows how ideas evolve from text to vision'
    },
    {
      id: '1512.03385',
      title: 'Deep Residual Learning for Image Recognition',
      description: 'ResNet paper - highly influential computer vision work'
    }
  ];

  return (
    <div className="paper-relationships-page">
      <div className="page-header">
        <h1>📊 Paper Relationship Explorer</h1>
        <p className="page-subtitle">
          Discover how research ideas connect - see what papers built upon each other like a family tree
        </p>
        
        {/* Show paper title when coming from discovery */}
        {paperTitle && (
          <div className="current-paper-info">
            <div className="current-paper-label">Building graph for:</div>
            <div className="current-paper-title">{paperTitle}</div>
          </div>
        )}
      </div>

      {/* Example Papers */}
      {!currentPaperId && (
        <div className="examples-section">
          <h3>🎯 Try These Famous Papers</h3>
          <div className="example-papers">
            {examplePapers.map((paper, index) => (
              <div key={index} className="example-paper-card">
                <h4>{paper.title}</h4>
                <p>{paper.description}</p>
                <button 
                  onClick={() => handleExamplePaper(paper.id)}
                  className="try-example-btn"
                >
                  🔍 Explore This Paper
                </button>
                <div className="paper-id-display">
                  <code>{paper.id}</code>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Papers */}
      {recentPapers.length > 0 && (
        <div className="recent-section">
          <div className="recent-header">
            <h4>📚 Recently Explored</h4>
            <button onClick={clearRecentPapers} className="clear-recent-btn">
              Clear History
            </button>
          </div>
          <div className="recent-papers">
            {recentPapers.map((paperId, index) => (
              <button
                key={index}
                onClick={() => handlePaperClick(paperId)}
                className={`recent-paper-btn ${paperId === currentPaperId ? 'active' : ''}`}
              >
                {paperId}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="main-content">
        <SimplePaperRelationships 
          paperId={currentPaperId}
          onPaperClick={handlePaperClick}
          prefetchedGraphData={prefetchedGraphData}
        />
      </div>
    </div>
  );
};

export default SimplePaperRelationshipsPage;