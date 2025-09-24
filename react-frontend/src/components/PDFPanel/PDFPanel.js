import React from 'react';
import './PDFPanel.css';
import FileUpload from './FileUpload';
import PDFViewer from './PDFViewer';
import { useDocument } from '../../context/DocumentContext';

const PDFPanel = () => {
  const { document } = useDocument();

  return (
    <div className="pdf-panel">
      {document.status === 'none' ? (
        <FileUpload />
      ) : (
        <PDFViewer />
      )}
    </div>
  );
};

export default PDFPanel;