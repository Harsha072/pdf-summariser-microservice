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
        console.log('Using prefetched graph data:', prefetchedGraphData);
        console.log('Has visualization_data:', !!prefetchedGraphData.visualization_data);
        console.log('Has connections:', !!prefetchedGraphData.connections);
        console.log('Full data structure:', JSON.stringify(Object.keys(prefetchedGraphData), null, 2));
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
      console.log("Paper relationships API response:", data);
      console.log("Foundation papers:", data?.connections?.foundation_papers);
      console.log("Building papers:", data?.connections?.building_papers);
      console.log("Similar papers:", data?.connections?.similar_papers);
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
    return ''; // Removed emoji icons
  };

  if (!paperId) {
    return (
      <div className="simple-relationships">
        <div className="empty-state">
          <p>Select a paper to explore its research family tree</p>
          <div className="explanation">
            <p>This tool shows:</p>
            <ul>
              <li><strong>Research Insights:</strong> Understanding the paper's influence and impact</li>
              <li><strong>Interactive Visualization:</strong> Visual family tree of paper relationships</li>
              <li><strong>Related Authors:</strong> Key researchers in this field</li>
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
          <h3>Exploring Paper Relationships...</h3>
          <p>Analyzing citations and references for {paperId}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="simple-relationships">
        <div className="error-state">
          <h3>Unable to Explore Relationships</h3>
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
          Explore Paper Relationships
        </button>
        <p>Discover what this paper built upon and what built upon it</p>
      </div>
    );
  }

  const { connections, insights, patterns, paper_info, data_status } = relationships;

  return (
    <div className="paper-relationships-explorer">
      {/* Header with Paper Info */}
      <div className="paper-header">
        <h3>Paper Family Tree</h3>
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

      {/* Data Status Message */}
      {data_status && data_status.message && (
        <div className={`data-status-banner ${data_status.total_connections === 0 ? 'warning' : 'info'}`}>
          <span className="status-icon">{data_status.total_connections === 0 ? '!' : 'i'}</span>
          <div className="status-content">
            <p>{data_status.message}</p>
            {data_status.total_connections > 0 && !data_status.has_references && !data_status.has_citations && (
              <p className="status-hint">Showing similar papers based on research topics</p>
            )}
          </div>
        </div>
      )}

      {/* Family Tree Visualization */}
      {relationships && relationships.visualization_data && (
        <div className="visualization-section">
          <h4>
            {relationships.visualization_data.graph_type === 'similarity' 
              ? 'Research Topic Network' 
              : 'Paper Family Tree'}
          </h4>
          {relationships.visualization_data.graph_type === 'similarity' && (
            <p className="viz-description">
              No citation data available - showing papers researching similar topics
            </p>
          )}
          <SimpleVisualization 
            data={relationships.visualization_data}
            onNodeClick={handlePaperClick}
            connections={connections}
          />
        </div>
      )}

      {/* Related Authors */}
      {connections.related_authors && connections.related_authors.length > 0 && (
        <div className="authors-section">
          <h4>Key Related Authors</h4>
          <div className="authors-list">
            {connections.related_authors.map((author, index) => (
              <div key={index} className="author-card">
                <div className="author-name">{author.name}</div>
                <div className="author-stats">
                  {author.reference_papers > 0 && (
                    <span className="stat">{author.reference_papers} refs</span>
                  )}
                  {author.citing_papers > 0 && (
                    <span className="stat">{author.citing_papers} cites</span>
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
          <h4>Interesting Patterns</h4>
          <div className="patterns-list">
            {patterns.patterns.map((pattern, index) => (
              <div key={index} className="pattern-item">
                {pattern}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Family Tree Visualization - Always Displayed (like Litmaps) */}
      {/* {relationships && relationships.visualization_data && (
        <div className="visualization-section">
          <h4>
            {relationships.visualization_data.graph_type === 'similarity' 
              ? 'Research Topic Network' 
              : 'Paper Family Tree'}
          </h4>
          {relationships.visualization_data.graph_type === 'similarity' && (
            <p className="viz-description">
              No citation data available - showing papers researching similar topics
            </p>
          )}
          <SimpleVisualization 
            data={relationships.visualization_data}
            onNodeClick={handlePaperClick}
          />
        </div>
      )} */}

      {/* Research Timeline - Horizontal Layout */}
      {connections.research_timeline && connections.research_timeline.timeline && (
        <div className="timeline-section-horizontal">
          <h4>Research Timeline</h4>
          <div className="timeline-insights">
            {connections.research_timeline.insights?.map((insight, index) => (
              <div key={index} className="timeline-insight">
                {insight}
              </div>
            ))}
          </div>
          <div className="timeline-horizontal-container">
            <div className="timeline-track">
              {Object.entries(connections.research_timeline.timeline)
                .slice(-8) // Show last 8 years to keep it manageable
                .map(([year, papers]) => (
                <div key={year} className="timeline-year-box">
                  <div className="year-marker">{year}</div>
                  <div className="year-content">
                    <div className="year-stats">
                      {papers.length} paper{papers.length > 1 ? 's' : ''}
                    </div>
                    <div className="year-papers-compact">
                      {papers.slice(0, 2).map((paper, index) => ( // Show top 2 papers
                        <div key={index} className={`timeline-paper-mini ${paper.type}`} title={paper.title}>
                          <div className="paper-type-indicator">
                            {paper.type === 'main' ? '●' : paper.type === 'reference' ? '▲' : '▼'}
                          </div>
                          <div className="paper-mini-info">
                            <div className="paper-title-mini">{paper.title}</div>
                            <div className="paper-citations-mini">{paper.citations} cites</div>
                          </div>
                        </div>
                      ))}
                      {papers.length > 2 && (
                        <div className="more-papers-mini">+{papers.length - 2} more</div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

// Interactive D3-style visualization component for paper relationships
const SimpleVisualization = ({ data, onNodeClick, connections }) => {
  const [mounted, setMounted] = useState(false);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !data || !data.nodes) {
    return <div className="viz-loading">Loading visualization...</div>;
  }

  const { nodes, links, legend } = data;

  // Get full paper details from connections
  const getFullPaperDetails = (node) => {
    if (node.type === 'center') {
      return null; // Center node doesn't need tooltip
    }

    // Find paper in connections arrays
    let paperDetails = null;
    
    if (node.type === 'reference' && connections?.foundation_papers) {
      paperDetails = connections.foundation_papers.find(p => 
        p.title === node.title || p.id === node.id
      );
    } else if (node.type === 'citation' && connections?.building_papers) {
      paperDetails = connections.building_papers.find(p => 
        p.title === node.title || p.id === node.id
      );
    } else if (node.type === 'similar' && connections?.similar_papers) {
      paperDetails = connections.similar_papers.find(p => 
        p.title === node.title || p.id === node.id
      );
    }

    return paperDetails;
  };

  const handleNodeHover = (node, event) => {
    if (node.type === 'center') return; // Don't show tooltip for center node
    
    setHoveredNode(node);
    const rect = event.currentTarget.getBoundingClientRect();
    setTooltipPos({
      x: rect.left + rect.width / 2,
      y: rect.top - 10
    });
  };

  const handleNodeLeave = () => {
    setHoveredNode(null);
  };

  const formatAuthors = (authors) => {
    if (!authors || authors.length === 0) return 'Unknown authors';
    if (authors.length === 1) return authors[0];
    if (authors.length === 2) return authors.join(' & ');
    return `${authors[0]} et al.`;
  };

  // Color mapping for different node types
  const getNodeColor = (node) => {
    switch (node.type) {
      case 'center':
        return '#4CAF50';  // Green for the center/selected paper
      case 'reference':
        return '#2196F3';  // Blue for Foundation Papers (what this paper built upon)
      case 'citation':
        return '#FF9800';  // Orange for Building Papers (what built upon this paper)
      case 'similar':
        return '#a29bfe';  // Purple for Similar Papers (topic-related)
      default:
        return node.color || '#9E9E9E';  // Fallback to original color or gray
    }
  };

  // IMPROVED layout - prevent overlapping with better spacing and curved lines
  const centerX = 600;  
  const centerY = 450;  
  const radius = 350;   // Increased radius for more space

  const getNodePosition = (node, index) => {
    if (node.type === 'center') {
      return { x: centerX, y: centerY };
    }
    
    // Separate references, citations, and similar papers into distinct sections
    const refNodes = nodes.filter(n => n.type === 'reference');
    const citeNodes = nodes.filter(n => n.type === 'citation');
    const similarNodes = nodes.filter(n => n.type === 'similar');
    
    if (node.type === 'reference') {
      // References on the LEFT side (180° to 270°)
      const refIndex = refNodes.indexOf(node);
      const totalRefs = refNodes.length;
      const startAngle = Math.PI * 0.75;  // Start at 135°
      const endAngle = Math.PI * 1.25;    // End at 225°
      const angleSpan = endAngle - startAngle;
      const angle = startAngle + (angleSpan / (totalRefs + 1)) * (refIndex + 1);
      
      return {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    } else if (node.type === 'citation') {
      // Citations on the RIGHT side (270° to 360°/0° to 90°)
      const citeIndex = citeNodes.indexOf(node);
      const totalCites = citeNodes.length;
      const startAngle = -Math.PI * 0.25;  // Start at -45° (315°)
      const endAngle = Math.PI * 0.25;     // End at 45°
      const angleSpan = endAngle - startAngle;
      const angle = startAngle + (angleSpan / (totalCites + 1)) * (citeIndex + 1);
      
      return {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    } else if (node.type === 'similar') {
      // Similar papers AROUND the circle evenly distributed
      const simIndex = similarNodes.indexOf(node);
      const totalSimilar = similarNodes.length;
      const angle = (2 * Math.PI / totalSimilar) * simIndex;
      
      return {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    }
    
    // Fallback
    return { x: centerX, y: centerY };
  };

  // Helper function to create curved paths for better visual separation
  const getConnectionPath = (sourcePos, targetPos) => {
    const dx = targetPos.x - sourcePos.x;
    const dy = targetPos.y - sourcePos.y;
    const dr = Math.sqrt(dx * dx + dy * dy) * 0.5; // Curve strength
    
    return `M${sourcePos.x},${sourcePos.y} Q${centerX},${centerY} ${targetPos.x},${targetPos.y}`;
  };

  return (
    <div className="simple-visualization">
      <div className="viz-container">
        <svg width="1000" height="900" viewBox="0 0 1000 900">
          {/* Connection Lines with curved paths */}
          {links && links.map((link, index) => {
            const sourceNode = nodes.find(n => n.id === link.source);
            const targetNode = nodes.find(n => n.id === link.target);
            
            if (!sourceNode || !targetNode) return null;
            
            const sourcePos = getNodePosition(sourceNode, nodes.indexOf(sourceNode));
            const targetPos = getNodePosition(targetNode, nodes.indexOf(targetNode));
            
            // Use curved path instead of straight line
            const pathD = getConnectionPath(sourcePos, targetPos);
            
            return (
              <path
                key={index}
                d={pathD}
                stroke={link.type === 'influences' ? '#4ecdc4' : link.type === 'related' ? '#a29bfe' : '#45b7d1'}
                strokeWidth="2"
                fill="none"
                opacity="0.5"
                strokeDasharray={link.type === 'related' ? '5,5' : 'none'}  // Dashed for similarity
              />
            );
          })}
          
          {/* Paper Nodes */}
          {nodes.map((node, index) => {
            const pos = getNodePosition(node, index);
            
            return (
              <g 
                key={node.id}
                onMouseEnter={(e) => handleNodeHover(node, e)}
                onMouseLeave={handleNodeLeave}
              >
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={node.size || 18}
                  fill={getNodeColor(node)}
                  stroke="#fff"
                  strokeWidth="3"
                  onClick={() => onNodeClick && onNodeClick(node)}
                  style={{ cursor: 'pointer' }}
                  opacity="0.9"
                />
                {/* Smart label positioning based on node position relative to center */}
                <text
                  x={pos.x}
                  y={pos.y < centerY ? pos.y - (node.size || 18) - 8 : pos.y + (node.size || 18) + 18}
                  textAnchor="middle"
                  fontSize="11"
                  fill="#333"
                  fontWeight="500"
                  className="node-label"
                  style={{ pointerEvents: 'none' }}
                >
                  {node.title && node.title.length > 25 ? node.title.slice(0, 25) + '...' : node.title}  
                </text>
              </g>
            );
          })}
        </svg>

        {/* Vertical Legend on the Right */}
        <div className="viz-legend">
          <h3 className="legend-title">Legend</h3>
          <div className="legend-item">
            <div 
              className="legend-color" 
              style={{ backgroundColor: '#4CAF50' }}
            ></div>
             <div className="legend-text">
               <span>Selected Paper</span>

             </div>
            </div>
          <div className="legend-item">
            <div 
              className="legend-color" 
              style={{ backgroundColor: '#2196F3' }}
            ></div>
            <div className="legend-text">
              
              <span>Foundation Papers</span>
              <span className="legend-desc">(What this paper built upon)</span>
            </div>
          </div>
          <div className="legend-item">
            <div 
              className="legend-color" 
              style={{ backgroundColor: '#FF9800' }}
            ></div>
            <div className="legend-text">
              {/* <span className="legend-symbol">▼</span> */}
              <span>Building Papers</span>
              <span className="legend-desc">(What built upon this paper)</span>
            </div>
          </div>
          <div className="legend-item">
            <div 
              className="legend-color" 
              style={{ backgroundColor: '#a29bfe' }}
            ></div>
            <div className="legend-text">
              <span>Similar Papers</span>
              <span className="legend-desc">(Topic-related research)</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Comic-style Tooltip */}
      {hoveredNode && (
        <div 
          className="paper-tooltip comic-tooltip"
          data-type={hoveredNode.type}
          style={{
            position: 'fixed',
            left: `${tooltipPos.x}px`,
            top: `${tooltipPos.y}px`,
            transform: 'translate(-50%, -100%)',
            zIndex: 1000
          }}
        >
          <div className="tooltip-content">
            <div className="tooltip-header">
              <span className="tooltip-icon">
                {hoveredNode.type === 'reference' ? '▲' : hoveredNode.type === 'citation' ? '▼' : '●'}
              </span>
              <span className="tooltip-type">
                {hoveredNode.type === 'reference' ? 'Foundation Paper' : 
                 hoveredNode.type === 'citation' ? 'Building Paper' : 
                 'Similar Research'}
              </span>
            </div>
            
            <div className="tooltip-title">{hoveredNode.title}</div>
            
            <div className="tooltip-meta">
              {hoveredNode.year && (
                <div className="tooltip-meta-item">
                  <span className="meta-label">Year:</span>
                  <span className="meta-value">{hoveredNode.year}</span>
                </div>
              )}
              {hoveredNode.citations !== undefined && (
                <div className="tooltip-meta-item">
                  <span className="meta-label">Citations:</span>
                  <span className="meta-value">{hoveredNode.citations}</span>
                </div>
              )}
            </div>
            
            {(() => {
              const fullDetails = getFullPaperDetails(hoveredNode);
              if (fullDetails && fullDetails.authors) {
                return (
                  <div className="tooltip-authors">
                    <span className="authors-label">Authors:</span>
                    <span className="authors-text">{formatAuthors(fullDetails.authors)}</span>
                  </div>
                );
              }
              return null;
            })()}
            
            <div className="tooltip-arrow"></div>
          </div>
        </div>
      )}
      
      <div className="viz-explanation">
        <p><strong>Interactive Family Tree:</strong> Your selected paper is in the center with related papers connected around it. Click on any node to explore that paper's relationships!</p>
      </div>
    </div>
  );
};

export default SimplePaperRelationships;