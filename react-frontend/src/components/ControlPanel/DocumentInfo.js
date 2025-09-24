// import React from 'react';
// import './DocumentInfo.css';
// import { useDocument } from '../../context/DocumentContext';

// const DocumentInfo = () => {
//   const { document } = useDocument();

//   return (
//     <div className="control-card document-info">
//       <div className="card-header">
//         <i className="fas fa-info-circle card-icon"></i>
//         <h2>Document Information</h2>
//       </div>
//       <div className="card-content">
//         <div className="info-grid">
//           <div className="info-item">
//             <strong>File:</strong> 
//             <span>{document.fileName || '-'}</span>
//           </div>
//           <div className="info-item">
//             <strong>Pages:</strong> 
//             <span>{document.pageCount || '-'}</span>
//           </div>
//           <div className="info-item">
//             <strong>Status:</strong> 
//             <span className={`status ${document.status}`}>
//               {document.status === 'ready' ? 'Ready' : 
//                document.status === 'uploading' ? 'Uploading...' :
//                document.status === 'processing' ? 'Processing...' :
//                document.status === 'error' ? 'Error' : '-'}
//             </span>
//           </div>
//           <div className="info-item">
//             <strong>Doc ID:</strong> 
//             <span>{document.id ? `${document.id.substring(0, 8)}...` : '-'}</span>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default DocumentInfo;