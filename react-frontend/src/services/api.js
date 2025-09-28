const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async makeRequest(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultOptions = {
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
      },
      ...options
    };

    try {
      const response = await fetch(url, defaultOptions);
      console.log("getting response ",response)
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Network error' }));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
    
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseURL}/upload`, {
      method: 'POST',
      mode: 'cors',
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Upload failed' }));
      throw new Error(errorData.error || 'Upload failed');
    }

    return await response.json();
  }

  async getProcessingStatus(docId) {
    return this.makeRequest(`/status/${docId}`, {
      method: 'GET'
    });
  }

  async getAllProcessingStatuses() {
    return this.makeRequest('/status', {
      method: 'GET'
    });
  }

  async pollProcessingStatus(docId, onProgress, maxWaitTime = 300000) {
    const startTime = Date.now();
    const pollInterval = 1000; // Poll every 1 second

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          if (Date.now() - startTime > maxWaitTime) {
            reject(new Error('Processing timeout'));
            return;
          }

          const status = await this.getProcessingStatus(docId);
          
          if (onProgress) {
            onProgress(status);
          }

          if (status.status === 'completed') {
            resolve(status);
          } else if (status.status === 'failed') {
            reject(new Error(status.message || 'Processing failed'));
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

  async generateSummary(docId) {
    return this.makeRequest('/summary', {
      method: 'POST',
      body: JSON.stringify({ doc_id: docId })
    });
  }

  async askQuestion(docId, question) {
    return this.makeRequest('/question', {
      method: 'POST',
      body: JSON.stringify({ 
        doc_id: docId, 
        question: question 
      })
    });
  }

  async askAcademicQuestion(docId, question, questionType = 'general') {
    return this.makeRequest('/academic-question', {
      method: 'POST',
      body: JSON.stringify({ 
        doc_id: docId, 
        question: question,
        type: questionType
      })
    });
  }

  async analyzePaper(docId) {
    return this.makeRequest(`/analyze-paper/${docId}`, {
      method: 'POST'
    });
  }

  async generateResearchQuestions(docId) {
    return this.makeRequest(`/research-questions/${docId}`, {
      method: 'POST'
    });
  }

  async explainConcept(docId, concept) {
    return this.makeRequest('/explain-concept', {
      method: 'POST',
      body: JSON.stringify({ 
        doc_id: docId, 
        concept: concept 
      })
    });
  }

  async getSectionSummary(docId, section = 'introduction') {
    return this.makeRequest(`/section-summary/${docId}`, {
      method: 'POST',
      body: JSON.stringify({ 
        section: section 
      })
    });
  }

  async checkHealth() {
    return this.makeRequest('/health');
  }

  async askWithQuotes(docId, question) {
    return this.makeRequest('/ask-with-quotes', {
      method: 'POST',
      body: JSON.stringify({
        doc_id: docId,
        question: question
      })
    });
  }
}

// Create singleton instance
const apiClient = new ApiClient();

// Export individual functions for convenience
export const uploadDocument = (file) => apiClient.uploadDocument(file);
export const generateSummary = (docId) => apiClient.generateSummary(docId);
export const askQuestion = (docId, question) => apiClient.askQuestion(docId, question);
export const askAcademicQuestion = (docId, question, questionType) => 
  apiClient.askAcademicQuestion(docId, question, questionType);
export const analyzePaper = (docId) => apiClient.analyzePaper(docId);
export const generateResearchQuestions = (docId) => apiClient.generateResearchQuestions(docId);
export const explainConcept = (docId, concept) => apiClient.explainConcept(docId, concept);
export const getSectionSummary = (docId, section) => apiClient.getSectionSummary(docId, section);
export const checkHealth = () => apiClient.checkHealth();
export const askWithQuotes = (docId, question) => apiClient.askWithQuotes(docId, question);
export const getProcessingStatus = (docId) => apiClient.getProcessingStatus(docId);
export const getAllProcessingStatuses = () => apiClient.getAllProcessingStatuses();
export const pollProcessingStatus = (docId, onProgress, maxWaitTime) => 
  apiClient.pollProcessingStatus(docId, onProgress, maxWaitTime);

export default apiClient;