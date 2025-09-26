import React, { useCallback } from 'react';
import './FileUpload.css';
import { useDocument } from '../../context/DocumentContext';
import { useNotification } from '../../context/NotificationContext';
import { uploadDocument, pollProcessingStatus } from '../../services/api';
import ProgressBar from '../ProgressBar/ProgressBar';

const FileUpload = () => {
  const { document: documentState, updateDocument } = useDocument();
  const { showError, showSuccess, showInfo } = useNotification();

  const handleFileSelect = useCallback(async (file) => {
    if (!file || file.type !== 'application/pdf') {
      showError('Please select a PDF file');
      return;
    }

    try {
      // Start upload process
      updateDocument({ 
        fileName: file.name, 
        status: 'uploading',
        progress: 0,
        progressMessage: 'Starting upload...'
      });
      
      showInfo('Uploading document...');

      // Upload to backend (now returns immediately)
      const uploadResult = await uploadDocument(file);
      
      if (uploadResult.status !== 'accepted') {
        throw new Error('Upload was not accepted by server');
      }

      const docId = uploadResult.doc_id;
      
      // Update status to processing
      updateDocument({
        id: docId,
        status: 'processing',
        progress: 5,
        progressMessage: 'Upload complete, processing started...'
      });

      showInfo('Processing document - this may take a moment...');

      // Read file for PDF viewer while processing happens
      const fileReader = new FileReader();
      fileReader.onload = (e) => {
        updateDocument({
          pdfData: e.target.result
        });
      };
      fileReader.readAsArrayBuffer(file);

      // Start polling for processing status
      const finalStatus = await pollProcessingStatus(
        docId,
        (status) => {
          // Update progress during processing
          updateDocument({
            progress: status.progress || 0,
            progressMessage: status.message || 'Processing...',
            processingStatus: status
          });
        },
        300000 // 5 minute timeout
      );

      // Processing completed successfully
      updateDocument({
        status: 'ready',
        progress: 100,
        progressMessage: 'Processing complete!',
        processingStatus: finalStatus
      });

      showSuccess('Document processed successfully!');

    } catch (error) {
      console.error('Error processing file:', error);
      showError(`Error: ${error.message}`);
      updateDocument({ 
        status: 'error',
        progressMessage: `Error: ${error.message}`,
        processingStatus: null
      });
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
      
      {/* Progress Bar */}
      {(documentState.status === 'uploading' || documentState.status === 'processing') && (
        <ProgressBar 
          progress={documentState.progress} 
          message={documentState.progressMessage}
          className={documentState.status}
        />
      )}
    </div>
  );
};

export default FileUpload;