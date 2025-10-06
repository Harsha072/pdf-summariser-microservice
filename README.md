# 🎓 Academic Citation Extractor - For Masters Students

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![React](https://img.shields.io/badge/React-18%2B-blue)
![OpenAI](https://img.shields.io/badge/OpenAI-API-green)
![Docker](https://img.shields.io/badge/Docker-Compose-important)
![PDF.js](https://img.shields.io/badge/PDF.js-3.11%2B-red)

A specialized **AI-powered tool** designed for **Masters students** to automatically **extract and format academic citations** from research papers. Save hours of manual work by automatically detecting references and exporting them in standard academic formats.

## 🌟 Key Features

- **� Automatic Citation Detection**: Advanced pattern matching to find academic references
- **🎯 Multiple Citation Formats**: Export in APA, MLA, Harvard, and BibTeX formats
- **🔍 Smart Pattern Recognition**: Detects author-date citations, DOIs, URLs, and journal references
- **📄 PDF Processing**: Upload research papers and extract citations automatically
- **� Export Options**: Download formatted citations or copy to clipboard
- **🎓 Masters Student Focus**: Designed specifically for dissertation and thesis work
- **📱 Modern Interface**: Responsive React frontend with intuitive design
- **⚡ Fast Processing**: ChromaDB vector database for efficient document analysis

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   HTML Frontend │────│   Flask API      │────│   ChromaDB      │
│   (JavaScript)  │    │   (Python)       │    │   (Vector DB)   │
│   + PDF.js      │    │   + OpenAI       │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 💡 Tech Stack
- **Frontend**: Pure HTML + CSS + JavaScript with PDF.js
- **Backend**: Flask (Python) with OpenAI integration  
- **Database**: ChromaDB vector database
- **AI**: OpenAI GPT-3.5/4 for analysis
- **Document Processing**: PyPDF2, sentence transformers

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ 
- OpenAI API key
- Modern web browser

### 1. Clone and Setup
```bash
git clone https://github.com/Harsha072/pdf-summariser-microservice.git
cd "pdf-summariser - microservice"
```

### 2. Install Backend Dependencies
```bash
cd flask-api/app
pip install -r requirements.txt
```

### 3. Set Environment Variables
```bash
# Create .env file or set environment variable
export OPENAI_API_KEY="your-api-key-here"
```

### 4. Start the Application
```bash
# Return to project root and run startup script
cd ../..
python start_app.py
```

**Choose Option 1** for full stack (Backend + Frontend)

## 📖 Usage

### 🌐 Web Interface
1. **Upload PDF**: Drag and drop or click to browse
2. **View Document**: Professional PDF viewer with navigation
3. **Generate Summary**: AI-powered comprehensive analysis
4. **Ask Questions**: Get answers with source citations
5. **Navigate**: Use keyboard arrows or toolbar controls

### 🔗 API Endpoints

**Base URL**: `http://localhost:5000`

#### Upload Document
```bash
curl -X POST -F "file=@document.pdf" http://localhost:5000/upload
```
**Response**: `{"doc_id": "uuid", "message": "success"}`

#### Generate Summary  
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"doc_id":"your-doc-id"}' \
  http://localhost:5000/summarize
```

#### Ask Question
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"doc_id":"your-doc-id","question":"What are the main findings?"}' \
  http://localhost:5000/ask
```

**Response includes**:
```json
{
  "answer": "AI-generated response",
  "sources": [
    {
      "filename": "document.pdf",
      "page": 5,
      "section_heading": "Results",
      "snippet": "relevant quote from document"
    }
  ]
}
```

## 🎯 Interface Options

### 1. 🌐 **HTML + JavaScript Interface** (Recommended)
- **Location**: `frontend/index.html`
- **Features**: Professional PDF viewer, responsive design, advanced controls
- **Best for**: Production use, professional document analysis

### 2. 🔗 **API Only** 
- **Access**: `http://localhost:5000`
- **Features**: RESTful endpoints for custom integrations
- **Best for**: Custom applications, mobile apps, third-party integrations

## 🔧 Configuration

### Environment Variables
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `BACKEND_URL`: API base URL (default: `http://localhost:5000`)

### Customization
- **Frontend**: Edit `frontend/index.html` for UI changes
- **Backend**: Modify `flask-api/app/main.py` for API changes  
- **AI Settings**: Update `flask-api/app/summarise.py` for model configuration

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Backend API: http://localhost:5000
# Frontend: Open frontend/index.html in browser
```

## 📁 Project Structure

```
pdf-summariser-microservice/
├── flask-api/              # Python Flask backend
│   ├── app/
│   │   ├── main.py         # Main API endpoints
│   │   ├── retriever.py    # Document processing  
│   │   ├── summarise.py    # AI logic
│   │   └── requirements.txt
│   └── Dockerfile
├── frontend/               # HTML + JavaScript interface
│   └── index.html          # Professional PDF viewer
├── chroma_db/              # Vector database storage
├── start_app.py            # Easy startup script
└── docker-compose.yml      # Container orchestration
```

## ✨ Features Deep Dive

### 🎨 Professional PDF Viewer
- **PDF.js Integration**: Industry-standard PDF rendering
- **Navigation Controls**: Previous/next, page jumping, zoom
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Keyboard Shortcuts**: Arrow keys for page navigation

### 🤖 AI-Powered Analysis  
- **Smart Summarization**: Contextual document summaries
- **Question Answering**: Natural language queries
- **Source Attribution**: Exact page and section references
- **Context Awareness**: Understands document structure

### ⚡ Performance Features
- **Vector Database**: Fast semantic search with ChromaDB
- **Efficient Chunking**: Optimized text processing
- **Caching**: Reduced processing time for repeat queries
- **Streaming**: Progressive loading for large documents

## 🌐 Deployment Options

### Local Development
```bash
python start_app.py  # Interactive menu
```

### Docker (Recommended for Production)
```bash
docker-compose up --build
```

### Cloud Platforms
- **Render**: Connect GitHub repo for auto-deploy
- **Railway**: One-click deployment
- **Google Cloud Run**: Container-based scaling
- **AWS ECS**: Enterprise container deployment

## 🔍 Troubleshooting

### Common Issues

**Backend Connection Failed**
- Ensure Flask server is running on port 5000
- Check OpenAI API key is set correctly
- Verify Python dependencies are installed

**PDF Not Loading**
- Check file is valid PDF format
- Ensure browser supports PDF.js
- Try refreshing the page

**AI Responses Empty**
- Verify OpenAI API key has credits
- Check document was processed successfully
- Review network console for errors

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **PDF.js** for professional PDF rendering
- **OpenAI** for powerful language models
- **ChromaDB** for efficient vector storage
- **Flask** for robust API framework

---

**⭐ If this project helped you, please consider giving it a star!**