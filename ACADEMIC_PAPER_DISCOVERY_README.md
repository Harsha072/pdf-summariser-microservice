# 🔬 Academic Paper Discovery Engine

## Revolutionizing Research Workflow for Masters Students

The Academic Paper Discovery Engine is an AI-powered platform that helps researchers find relevant academic papers using advanced web scraping and AI analysis. Unlike common chatbot interfaces, this unique tool addresses the real pain points of academic research by saving students significant time in the literature review process.

## 🚀 Why This Project Stands Out

This project differentiates itself from common chatbot applications by focusing on:

1. **Real Academic Value**: Solves actual research workflow problems
2. **Multi-Source Intelligence**: Combines arXiv, Semantic Scholar, and Google Scholar
3. **AI-Powered Relevance**: Uses OpenAI GPT for intelligent paper ranking
4. **Research-Focused**: Built specifically for Masters/PhD students
5. **Interview-Worthy**: Unique approach that demonstrates practical AI application

## ✨ Key Features

### 🔍 Intelligent Paper Discovery
- **Multi-Source Search**: Searches arXiv, Semantic Scholar, and Google Scholar simultaneously
- **AI Research Focus extraction**: Analyzes your query/paper to extract key research topics
- **Relevance Scoring**: AI-powered ranking of papers based on your specific research needs
- **Duplicate Detection**: Intelligent removal of duplicate papers across sources

### 📄 Upload & Analyze
- **PDF Paper Upload**: Upload your existing research paper to find similar works
- **Research Gap Analysis**: Discover related papers you might have missed
- **Citation Enhancement**: Find papers that could strengthen your bibliography

### 🎯 Smart Features
- **Customizable Sources**: Choose which databases to search
- **Result Limiting**: Control number of results (5-20 papers)
- **One-Click Access**: Direct links to PDFs and paper details
- **Real-time Processing**: Fast, concurrent searches across multiple sources

## 🛠 Technology Stack

### Backend (Flask API)
- **Flask**: Web framework for API endpoints
- **OpenAI GPT-3.5**: AI analysis and relevance scoring
- **arXiv API**: Academic paper search
- **Semantic Scholar API**: Research paper database
- **BeautifulSoup**: Web scraping for additional sources
- **PyMuPDF**: PDF processing and text extraction
- **FuzzyWuzzy**: Duplicate detection algorithms

### Frontend (React)
- **React**: Modern UI framework
- **Custom CSS**: Responsive, academic-themed design
- **File Upload**: Drag-and-drop PDF functionality
- **Real-time Updates**: Live search status and results

## 📋 API Endpoints

### POST `/api/discover-papers`
Discover papers based on research query
```json
{
  "query": "machine learning for climate change prediction",
  "sources": ["arxiv", "semantic_scholar"],
  "max_results": 10
}
```

### POST `/api/upload-paper`
Upload PDF to find similar papers
- Form data with PDF file
- Returns analysis + similar papers

### POST `/api/download-paper`
Download and analyze paper from URL
```json
{
  "url": "https://arxiv.org/pdf/2301.12345.pdf"
}
```

### GET `/api/health`
Health check endpoint

### GET `/api/sources`
Get available search sources

## 🔧 Setup Instructions

### Backend Setup
1. Navigate to `flask-api/app/`
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```bash
   # Create .env file
   OPENAI_API_KEY=your_openai_api_key_here
   ```
4. Run the Flask server:
   ```bash
   python main.py
   ```

### Frontend Setup
1. Navigate to `react-frontend/`
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm start
   ```

## 📊 Usage Examples

### Research Query Discovery
```
Query: "transformer models for natural language processing sentiment analysis"

Results:
- 📄 "BERT: Pre-training of Deep Bidirectional Transformers..." (arXiv, 95% relevance)
- 📄 "RoBERTa: A Robustly Optimized BERT Pretraining Approach" (Semantic Scholar, 92% relevance)
- 📄 "DistilBERT, a distilled version of BERT..." (arXiv, 88% relevance)
```

### PDF Upload Analysis
```
Upload: Your research paper on "Deep Learning for Medical Imaging"

Analysis:
- Research Focus: Medical image classification using CNNs
- Domain: Computer Vision, Healthcare
- Keywords: deep learning, medical imaging, CNN, classification

Similar Papers Found:
- Papers using similar methodologies
- Recent advances in medical AI
- Benchmark datasets and evaluation methods
```

## 🎯 Target Users

- **Masters Students**: Literature review for thesis research
- **PhD Candidates**: Comprehensive research discovery
- **Academic Researchers**: Finding relevant recent publications
- **Research Assistants**: Efficient paper collection and analysis

## 🏆 Competitive Advantages

1. **Speed**: Find 10-20 relevant papers in seconds vs. hours of manual searching
2. **Comprehensiveness**: Multi-source approach ensures broad coverage
3. **Intelligence**: AI ranking prevents information overload
4. **User-Focused**: Built for actual academic workflows
5. **Modern Tech Stack**: Demonstrates current AI/ML capabilities

## 🔮 Future Enhancements

- **Citation Network Analysis**: Visualize paper relationships
- **Research Trend Detection**: Identify emerging topics
- **Collaboration Suggestions**: Find researchers working on similar topics
- **Bibliography Export**: Direct export to LaTeX, BibTeX
- **Research Timeline**: Track paper evolution over time

## 📝 Project Status

✅ **Completed Features:**
- Multi-source paper discovery
- AI-powered relevance scoring
- PDF upload and analysis
- Responsive React frontend
- RESTful API design

🔄 **In Progress:**
- Enhanced duplicate detection
- Citation count integration
- Advanced filtering options

🎯 **Next Steps:**
- Deploy to production
- Add more academic databases
- Implement user accounts
- Create paper recommendation engine

## 💼 Interview Highlights

This project demonstrates:
- **Full-Stack Development**: React frontend + Flask backend
- **AI Integration**: Practical use of OpenAI GPT
- **Web Scraping**: Multi-source data collection
- **API Design**: RESTful architecture
- **Problem Solving**: Addresses real academic pain points
- **Modern Technologies**: Current best practices

---

**Built for the future of academic research** 🎓✨