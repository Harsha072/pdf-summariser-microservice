// Citation Network API Service
const API_BASE_URL = 'http://localhost:5000';

class CitationNetworkAPI {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async buildNetwork(params) {
    try {
      const response = await fetch(`${this.baseURL}/api/citation-network/build`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params)
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to build citation network');
      }

      return data;
    } catch (error) {
      console.error('Citation network build error:', error);
      throw error;
    }
  }

  async getPaperInfluence(paperId) {
    try {
      const response = await fetch(`${this.baseURL}/api/citation-network/paper-influence/${encodeURIComponent(paperId)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to get paper influence');
      }

      return data;
    } catch (error) {
      console.error('Paper influence analysis error:', error);
      throw error;
    }
  }

  async getResearchPathways(params) {
    try {
      const queryParams = new URLSearchParams(params);
      const response = await fetch(`${this.baseURL}/api/citation-network/research-pathways?${queryParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to get research pathways');
      }

      return data;
    } catch (error) {
      console.error('Research pathways error:', error);
      throw error;
    }
  }

  async buildCollaborationNetwork(params) {
    try {
      const response = await fetch(`${this.baseURL}/api/citation-network/collaboration`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params)
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to build collaboration network');
      }

      return data;
    } catch (error) {
      console.error('Collaboration network error:', error);
      throw error;
    }
  }

  async getCacheStats() {
    try {
      const response = await fetch(`${this.baseURL}/api/citation-network/cache-stats`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to get cache stats');
      }

      return data;
    } catch (error) {
      console.error('Cache stats error:', error);
      throw error;
    }
  }

  async clearCache() {
    try {
      const response = await fetch(`${this.baseURL}/api/citation-network/clear-cache`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to clear cache');
      }

      return data;
    } catch (error) {
      console.error('Clear cache error:', error);
      throw error;
    }
  }

  // Helper method for progressive network building with real-time updates
  async buildNetworkProgressive(params, onProgress) {
    try {
      // Start the network building process
      const initialResponse = await this.buildNetwork(params);
      
      if (initialResponse.success) {
        // If building is complete, return immediately
        if (onProgress) {
          onProgress({ stage: 'Complete', progress: 100 });
        }
        return initialResponse;
      }

      // If building is in progress, poll for updates
      if (initialResponse.building_id) {
        return this.pollBuildProgress(initialResponse.building_id, onProgress);
      }

      throw new Error('Network building failed to start');
    } catch (error) {
      console.error('Progressive network build error:', error);
      throw error;
    }
  }

  async pollBuildProgress(buildingId, onProgress) {
    const pollInterval = 2000; // Poll every 2 seconds
    const maxPolls = 150; // Max 5 minutes (150 * 2s)
    let pollCount = 0;

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          pollCount++;
          
          if (pollCount > maxPolls) {
            reject(new Error('Network building timeout'));
            return;
          }

          const response = await fetch(`${this.baseURL}/api/citation-network/build-status/${buildingId}`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            }
          });

          const data = await response.json();
          
          if (!response.ok) {
            reject(new Error(data.error || 'Failed to check build status'));
            return;
          }

          // Update progress
          if (onProgress && data.progress) {
            onProgress({
              stage: data.progress.stage || 'Building...',
              progress: data.progress.percentage || 0
            });
          }

          // Check if complete
          if (data.status === 'complete') {
            resolve(data.result);
          } else if (data.status === 'failed') {
            reject(new Error(data.error || 'Network building failed'));
          } else {
            // Continue polling
            setTimeout(poll, pollInterval);
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }

  // Export network data for external use
  async exportNetwork(networkData, format = 'json') {
    try {
      const blob = new Blob([JSON.stringify(networkData, null, 2)], {
        type: format === 'json' ? 'application/json' : 'text/plain'
      });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `citation-network.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      return { success: true };
    } catch (error) {
      console.error('Network export error:', error);
      throw error;
    }
  }

  // Share network view (generate shareable link)
  async shareNetwork(networkData, viewSettings) {
    try {
      // In a real implementation, this would upload to a sharing service
      // For now, we'll create a local data URL
      const shareData = {
        network: networkData,
        settings: viewSettings,
        timestamp: new Date().toISOString()
      };
      
      const dataStr = JSON.stringify(shareData);
      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
      
      // Copy to clipboard if available
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(window.location.href + '#shared=' + btoa(dataStr));
        return { success: true, message: 'Share link copied to clipboard!' };
      }
      
      return { success: true, shareUrl: dataUri };
    } catch (error) {
      console.error('Network share error:', error);
      throw error;
    }
  }
}

// Create and export singleton instance
export const citationNetworkAPI = new CitationNetworkAPI();
export default citationNetworkAPI;