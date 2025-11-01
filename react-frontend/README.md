# PDF Summarizer - React Frontend

A modern React-based frontend for the AI-Powered PDF Document Analyzer microservice.

## 🚀 Features

- **Modern React Architecture**: Built with React 18, hooks, and context API
- **Professional UI/UX**: Clean, responsive design with smooth animations
- **PDF.js Integration**: High-quality PDF viewing with zoom and navigation
- **Real-time Notifications**: Toast notifications for user feedback
- **AI-Powered Analysis**: Document summarization and Q&A with source citations
- **Responsive Design**: Optimized for desktop and mobile devices
- **CORS-Ready**: Seamless communication with Flask backend

## 🏗️ Architecture

### Component Structure
```
src/
├── components/
│   ├── Header/              # Application header with status
│   ├── PDFPanel/           # PDF upload and viewer
│   │   ├── FileUpload.js   # Drag & drop file upload
│   │   └── PDFViewer.js    # PDF.js integration
│   ├── ControlPanel/       # AI analysis controls
│   │   ├── DocumentInfo.js # Document metadata
│   │   ├── SummaryTab.js   # Summary generation
│   │   └── QATab.js        # Question & answer
│   ├── Notification/       # Toast notifications
│   └── common/            # Reusable components
│       ├── LoadingSpinner.js
│       └── CopyButton.js
├── context/               # React contexts
│   ├── DocumentContext.js # Document state management
│   └── NotificationContext.js # Notification system
├── services/             # API integration
│   └── api.js           # Backend communication
└── App.js               # Main application component
```

### State Management
- **DocumentContext**: Manages PDF document state, current page, zoom, etc.
- **NotificationContext**: Handles toast notifications and user feedback
- **React Hooks**: useState, useEffect, useCallback for component state

## 📦 Installation

### Prerequisites
- Node.js 16+ and npm
- Flask backend running on http://localhost:5000

### Setup
```bash
# Navigate to React frontend directory
cd react-frontend

# Install dependencies
npm install

# Start development server
npm start
```

The application will open at http://localhost:3000

## 🔧 Development Scripts

```bash
# Start development server with hot reload
npm start

# Build for production
npm build

# Run tests
npm test

# Serve production build locally
npm run serve
```

## 🌐 Backend Integration

### API Endpoints
The React app communicates with these Flask backend endpoints:

- `POST /upload` - Upload PDF document
- `POST /summary` - Generate AI summary
- `POST /question` - Ask questions about document
- `GET /health` - Backend health check

### CORS Configuration
The backend must have CORS enabled for cross-origin requests:

```python
from flask_cors import CORS
CORS(app, origins="*", methods=['GET', 'POST', 'OPTIONS'])
```

## 📱 Usage

1. **Upload Document**: Drag & drop or click to select PDF file
2. **View PDF**: Navigate pages, zoom in/out, view document metadata
3. **Generate Summary**: Click "Generate Summary" for AI-powered analysis
4. **Ask Questions**: Enter questions in Q&A tab for detailed answers
5. **Copy Results**: Use copy button to save summaries/answers

## 🎨 Styling

- **CSS Custom Properties**: Consistent theming with CSS variables
- **Component-Scoped CSS**: Each component has its own stylesheet
- **Responsive Design**: Mobile-first approach with media queries
- **Modern Animations**: Smooth transitions and loading states

## 🔧 Configuration

### Environment Variables
Create `.env` file in the root:

```env
REACT_APP_API_URL=http://localhost:5000
```

### Build Configuration
The app uses Create React App configuration with:
- Proxy setup for API calls
- FontAwesome icons via CDN
- PDF.js worker configuration

## 🚀 Deployment

### Production Build
```bash
npm run build
```

### Serve Static Files
```bash
# Using serve (recommended)
npm run serve

# Or use any static file server
npx serve -s build -l 3001
```

### Docker Deployment
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
RUN npm install -g serve
EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
```

## 🧪 Testing

The application includes:
- Component unit tests
- Integration tests for API calls
- End-to-end testing capabilities

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Generate coverage report
npm test -- --coverage
```

## 🔄 Migration from Vanilla JS

This React version replaces the previous vanilla JavaScript frontend with:

### ✅ Improvements
- **Better State Management**: React contexts vs global variables
- **Component Reusability**: Modular, reusable components
- **Type Safety**: Better development experience
- **Performance**: Virtual DOM and React optimizations
- **Maintainability**: Clear component boundaries and data flow

### 🔄 Feature Parity
- ✅ PDF upload and viewing
- ✅ AI summary generation
- ✅ Question & answer functionality
- ✅ Real-time notifications
- ✅ Responsive design
- ✅ CORS support

## 📚 Dependencies

### Core Dependencies
- `react` & `react-dom`: Core React framework
- `pdfjs-dist`: PDF.js for document rendering
- `axios`: HTTP client (alternative to fetch)

### Development Dependencies
- `react-scripts`: Create React App build tools
- `@testing-library/*`: Testing utilities
- `serve`: Production static file server

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Follow React best practices and coding standards
4. Add tests for new functionality
5. Submit pull request with detailed description

## 📄 License

This project is part of the PDF Summarizer microservice suite.

---

**Version**: 2.0.0  
**Framework**: React 18  
**Build Tool**: Create React App  
**Styling**: CSS3 with custom properties  
**Icons**: FontAwesome 6.4.0