import React, { useState, useEffect } from 'react';
import './SimplePaperRelationships.css';

const SimplePaperRelationships = ({ paperId, onPaperClick, prefetchedGraphData }) => {
  const [relationships, setRelationships] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Auto-explore relationships when paper ID changes or prefetched data is available
  useEffect(() => {
    if (paperId) {
      if (prefetchedGraphData) {
        console.log('📈 Using prefetched graph data');
        setRelationships(prefetchedGraphData);
        setLoading(false);
        setError(null);
      } else {
        exploreRelationships();
      }
    }
  }, [paperId, prefetchedGraphData]);

  const exploreRelationships = async () => {
    if (!paperId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/paper-relationships/${encodeURIComponent(paperId)}?max_connections=10`);
      const data = await response.json();
      console.log("explore relationships:::::")
      if (data.success) {
        setRelationships(data);
      } else {
        setError(data.error || 'Failed to explore paper relationships');
      }
    } catch (error) {
      console.error('Failed to load relationships:', error);
      setError('Failed to connect to server. Please try again.');
    }
    
    setLoading(false);
  };

  const handlePaperClick = (paper) => {
    if (onPaperClick && paper.id) {
      onPaperClick(paper.id);
    }
  };

  const formatAuthors = (authors) => {
    if (!authors || authors.length === 0) return 'Unknown authors';
    if (authors.length === 1) return authors[0];
    if (authors.length === 2) return authors.join(' and ');
    return `${authors[0]} et al.`;
  };

  const getInfluenceColor = (score) => {
    if (score > 80) return '#e74c3c';  // High influence - red
    if (score > 50) return '#f39c12';  // Medium influence - orange
    if (score > 20) return '#3498db';  // Low influence - blue
    return '#95a5a6';  // Minimal influence - gray
  };

  const renderInsightIcon = (insight) => {
    if (insight.includes('influential')) return '🔥';
    if (insight.includes('comprehensive') || insight.includes('extensive')) return '📚';
    if (insight.includes('new') || insight.includes('exploring')) return '🆕';
    if (insight.includes('foundational')) return '🏛️';
    if (insight.includes('fast impact')) return '⚡';
    if (insight.includes('enduring')) return '🏆';
    return '💡';
  };

  if (!paperId) {
    return (
      <div className="simple-relationships">
        <div className="empty-state">
          <h3>📊 Paper Relationship Explorer</h3>
          <p>Select a paper to explore its research family tree</p>
          <div className="explanation">
            <p>This tool shows:</p>
            <ul>
              <li>💡 <strong>Research Insights:</strong> Understanding the paper's influence and impact</li>
              <li>� <strong>Interactive Visualization:</strong> Visual family tree of paper relationships</li>
              <li>� <strong>Related Authors:</strong> Key researchers in this field</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="simple-relationships">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <h3>🔍 Exploring Paper Relationships...</h3>
          <p>Analyzing citations and references for {paperId}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="simple-relationships">
        <div className="error-state">
          <h3>❌ Unable to Explore Relationships</h3>
          <p>{error}</p>
          <button onClick={exploreRelationships} className="retry-btn">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!relationships) {
    return (
      <div className="simple-relationships">
        <button onClick={exploreRelationships} className="explore-btn">
          🔍 Explore Paper Relationships
        </button>
        <p>Discover what this paper built upon and what built upon it</p>
      </div>
    );
  }

  const { connections, insights, patterns, paper_info } = relationships;

  return (
    <div className="paper-relationships-explorer">
      {/* Header with Paper Info */}
      <div className="paper-header">
        <h3>📊 Paper Family Tree</h3>
        {paper_info && (
          <div className="main-paper-info">
            <h4>{paper_info.title}</h4>
            <div className="paper-meta">
              <span className="authors">{formatAuthors(paper_info.authors)}</span>
              {paper_info.year && <span className="year">• {paper_info.year}</span>}
              {paper_info.citation_count > 0 && (
                <span className="citations">• {paper_info.citation_count} citations</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Similar Papers Section (if available from enhanced features) */}
      {connections.similar_papers && connections.similar_papers.length > 0 && (
        <div className="similar-section">
          <h4>🔗 Similar Research Papers</h4>
          <div className="paper-list">
            {connections.similar_papers.map((paper, index) => (
              <div 
                key={index} 
                className="relationship-card clickable enhanced-paper"
                onClick={() => handlePaperClick(paper)}
              >
                <div className="paper-title">{paper.title}</div>
                <div className="paper-stats">
                  <span className="authors">{formatAuthors(paper.authors)}</span>
                  {paper.year && <span className="year">• {paper.year}</span>}
                  <span className="citations">• {paper.citations_count} citations</span>
                  <span className="source-badge">{paper.source}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related Authors */}
      {connections.related_authors && connections.related_authors.length > 0 && (
        <div className="authors-section">
          <h4>👥 Key Related Authors</h4>
          <div className="authors-list">
            {connections.related_authors.map((author, index) => (
              <div key={index} className="author-card">
                <div className="author-name">{author.name}</div>
                <div className="author-stats">
                  {author.reference_papers > 0 && (
                    <span className="stat">📚 {author.reference_papers} refs</span>
                  )}
                  {author.citing_papers > 0 && (
                    <span className="stat">📈 {author.citing_papers} cites</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Interesting Patterns */}
      {patterns?.patterns && patterns.patterns.length > 0 && (
        <div className="patterns-section">
          <h4>🔍 Interesting Patterns</h4>
          <div className="patterns-list">
            {patterns.patterns.map((pattern, index) => (
              <div key={index} className="pattern-item">
                {pattern}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Family Tree Visualization - Always Displayed */}
      {relationships && relationships.visualization_data && (
        <div className="visualization-section">
          <h4>📊 Paper Family Tree</h4>
          <SimpleVisualization 
            data={relationships.visualization_data}
            onNodeClick={handlePaperClick}
          />
        </div>
      )}

      {/* Research Timeline */}
      {connections.research_timeline && connections.research_timeline.timeline && (
        <div className="timeline-section">
          <h4>📅 Research Timeline</h4>
          <div className="timeline-insights">
            {connections.research_timeline.insights?.map((insight, index) => (
              <div key={index} className="timeline-insight">
                {insight}
              </div>
            ))}
          </div>
          <div className="timeline-view">
            {Object.entries(connections.research_timeline.timeline)
              .slice(-8) // Show last 8 years to keep it manageable
              .map(([year, papers]) => (
              <div key={year} className="timeline-year">
                <div className="year-label">{year}</div>
                <div className="year-papers">
                  {papers.slice(0, 3).map((paper, index) => ( // Limit to 3 papers per year
                    <div key={index} className={`timeline-paper ${paper.type}`}>
                      <div className="paper-title-short">{paper.title}</div>
                      <div className="paper-citations">{paper.citations} cites</div>
                    </div>
                  ))}
                  {papers.length > 3 && (
                    <div className="more-papers">+{papers.length - 3} more</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};

// Interactive D3-style visualization component for paper relationships
const SimpleVisualization = ({ data, onNodeClick }) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !data || !data.nodes) {
    return <div className="viz-loading">Loading visualization...</div>;
  }

  const { nodes, links, legend } = data;

  // Color mapping for different node types
  const getNodeColor = (node) => {
    switch (node.type) {
      case 'center':
        return '#4CAF50';  // Green for the center/selected paper
      case 'reference':
        return '#2196F3';  // Blue for Foundation Papers (what this paper built upon)
      case 'citation':
        return '#FF9800';  // Orange for Building Papers (what built upon this paper)
      default:
        return node.color || '#9E9E9E';  // Fallback to original color or gray
    }
  };

  // BIGGER SVG layout - radial arrangement around center paper with better spacing
  const centerX = 600;  // Adjusted for larger SVG (1200px wide)
  const centerY = 450;  // Adjusted for larger SVG (900px tall)  
  const radius = 320;   // Increased radius for more spacing between bubbles

  const getNodePosition = (node, index) => {
    if (node.type === 'center') {
      return { x: centerX, y: centerY };
    }
    
    const totalNodes = nodes.filter(n => n.type !== 'center').length;
    const minAngleStep = Math.PI / 8; // Minimum 22.5 degrees between nodes to prevent overlap
    const angleStep = Math.max((2 * Math.PI) / Math.max(totalNodes, 1), minAngleStep);
    let angle;
    
    if (node.type === 'reference') {
      // References on the left side with better spacing
      const refNodes = nodes.filter(n => n.type === 'reference');
      const refIndex = refNodes.indexOf(node);
      const refSpacing = Math.max(angleStep, minAngleStep);
      angle = Math.PI + (refSpacing * refIndex) - (refSpacing * (refNodes.length - 1)) / 2;
    } else {
      // Citations on the right side with better spacing
      const citeNodes = nodes.filter(n => n.type === 'citation');
      const citeIndex = citeNodes.indexOf(node);
      const citeSpacing = Math.max(angleStep, minAngleStep);
      angle = (citeSpacing * citeIndex) - (citeSpacing * (citeNodes.length - 1)) / 2;
    }
    
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    };
  };

  return (
    <div className="simple-visualization">
      <svg width="1200" height="900" viewBox="0 0 1200 900">
        {/* Connection Lines */}
        {links && links.map((link, index) => {
          const sourceNode = nodes.find(n => n.id === link.source);
          const targetNode = nodes.find(n => n.id === link.target);
          
          if (!sourceNode || !targetNode) return null;
          
          const sourcePos = getNodePosition(sourceNode, nodes.indexOf(sourceNode));
          const targetPos = getNodePosition(targetNode, nodes.indexOf(targetNode));
          
          return (
            <line
              key={index}
              x1={sourcePos.x}
              y1={sourcePos.y}
              x2={targetPos.x}
              y2={targetPos.y}
              stroke={link.type === 'influences' ? '#4ecdc4' : '#45b7d1'}
              strokeWidth="3"    /* Increased from 2 to 3 for better visibility */
              opacity="0.7"      /* Slightly increased opacity */
            />
          );
        })}
        
        {/* Paper Nodes */}
        {nodes.map((node, index) => {
          const pos = getNodePosition(node, index);
          
          return (
            <g key={node.id}>
              <circle
                cx={pos.x}
                cy={pos.y}
                r={node.size || 18}  /* Increased from 10 to 18 */
                fill={getNodeColor(node)}  /* Use custom color mapping */
                stroke="#fff"
                strokeWidth="3"      /* Increased from 2 to 3 */
                onClick={() => onNodeClick && onNodeClick(node)}
                style={{ cursor: 'pointer' }}
                opacity="0.8"
              />
              <text
                x={pos.x}
                y={pos.y - (node.size || 18) - 15}  /* Increased from 8 to 15 for more spacing */
                textAnchor="middle"
                fontSize="12"        /* Reduced from 14 to 12 to fit better */
                fill="#333"
                className="node-label"
              >
                {node.title && node.title.length > 20 ? node.title.slice(0, 20) + '...' : node.title}  
              </text>
            </g>
          );
        })}
      </svg>
      
      {/* Color-coded Legend */}
      <div className="viz-legend">
        <div className="legend-item">
          <div 
            className="legend-color" 
            style={{ backgroundColor: '#4CAF50' }}
          ></div>
          <span>🎯 Selected Paper</span>
        </div>
        <div className="legend-item">
          <div 
            className="legend-color" 
            style={{ backgroundColor: '#2196F3' }}
          ></div>
          <span>🏛️ Foundation Papers (What this paper built upon)</span>
        </div>
        <div className="legend-item">
          <div 
            className="legend-color" 
            style={{ backgroundColor: '#FF9800' }}
          ></div>
          <span>🚀 Building Papers (What built upon this paper)</span>
        </div>
      </div>
      
      <div className="viz-explanation">
        <p>📊 <strong>Interactive Family Tree:</strong> Your selected paper is in the center with related papers connected around it. Click on any node to explore that paper's relationships!</p>
      </div>
    </div>
  );
};

export default SimplePaperRelationships;