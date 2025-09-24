import React, { useCallback } from 'react';
import './FileUpload.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';
import { uploadDocument } from '../../services/api';

const FileUpload = () => {
  const { updateDocument } = useDocument();
  const { showError, showSuccess, showInfo } = useNotification();

  const handleFileSelect = useCallback(async (file) => {
    if (!file || file.type !== 'application/pdf') {
      showError('Please select a PDF file');
      return;
    }

    try {
      updateDocument({ 
        fileName: file.name, 
        status: 'uploading' 
      });
      
      showInfo('Processing document...');

      // Upload to backend
      const result = await uploadDocument(file);
      
      // Read file for PDF viewer
      const fileReader = new FileReader();
      fileReader.onload = (e) => {
        updateDocument({
          id: result.doc_id,
          pdfData: e.target.result,
          status: 'ready'
        });
      };
      fileReader.readAsArrayBuffer(file);

      showSuccess('Document processed successfully!');

    } catch (error) {
      console.error('Error uploading file:', error);
      showError(`Error: ${error.message}`);
      updateDocument({ status: 'error' });
    }
  }, [updateDocument, showError, showSuccess, showInfo]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
  }, []);

  const handleFileInput = useCallback((e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  return (
    <div className="file-upload">
      <div 
        className="upload-area"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => document.getElementById('fileInput').click()}
      >
        <div className="upload-content">
          <i className="fas fa-cloud-upload-alt upload-icon"></i>
          <div className="upload-text">
            Drop your PDF file here or click to browse
          </div>
          <div className="upload-subtext">
            Advanced PDF viewer with AI-powered analysis
          </div>
          <input
            type="file"
            id="fileInput"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={handleFileInput}
          />
        </div>
      </div>
    </div>
  );
};

export default FileUpload;