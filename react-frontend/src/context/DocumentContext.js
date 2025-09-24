import React, { createContext, useContext, useState, useCallback } from 'react';

const DocumentContext = createContext();

export const useDocument = () => {
  const context = useContext(DocumentContext);
  if (!context) {
    throw new Error('useDocument must be used within a DocumentProvider');
  }
  return context;
};

export const DocumentProvider = ({ children }) => {
  const [document, setDocument] = useState({
    id: null,
    fileName: '',
    pageCount: 0,
    status: 'none', // 'none', 'uploading', 'processing', 'ready', 'error'
    pdfData: null,
    currentPage: 1,
    zoom: 1.2,
    totalPages: 0
  });

  const [summary, setSummary] = useState({
    content: '',
    loading: false,
    error: null
  });

  const [qa, setQa] = useState({
    question: '',
    answer: '',
    loading: false,
    error: null
  });

  const updateDocument = useCallback((updates) => {
    setDocument(prev => ({ ...prev, ...updates }));
  }, []);

  const updateSummary = useCallback((updates) => {
    setSummary(prev => ({ ...prev, ...updates }));
  }, []);

  const updateQa = useCallback((updates) => {
    setQa(prev => ({ ...prev, ...updates }));
  }, []);

  const clearDocument = useCallback(() => {
    setDocument({
      id: null,
      fileName: '',
      pageCount: 0,
      status: 'none',
      pdfData: null,
      currentPage: 1,
      zoom: 1.2,
      totalPages: 0
    });
    setSummary({ content: '', loading: false, error: null });
    setQa({ question: '', answer: '', loading: false, error: null });
  }, []);

  const value = {
    document,
    summary,
    qa,
    updateDocument,
    updateSummary,
    updateQa,
    clearDocument
  };

  return (
    <DocumentContext.Provider value={value}>
      {children}
    </DocumentContext.Provider>
  );
};