# 🎓 Scholar Quest - AI-Powered Research Discovery Platform

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![React](https://img.shields.io/badge/React-18.2.0-blue)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-green)
![Render](https://img.shields.io/badge/Render-Deployed-success)
![Vercel](https://img.shields.io/badge/Vercel-Deployed-black)

**Scholar Quest** is an intelligent research companion designed to help researchers, students, and academics discover relevant papers, understand complex research, and explore citation networks. Powered by AI and integrated with OpenAlex's vast academic database.

🔗 **Live Application**: [https://scholar-quest-three.vercel.app](https://scholar-quest-three.vercel.app)

---

## 🌟 Key Features

### 🔍 **Smart Paper Discovery**
- Search academic papers using natural language queries
- AI-powered relevance scoring for each result
- Integration with OpenAlex's 250M+ paper database
- Real-time caching for faster repeat searches

### 🤖 **AI Analysis**
- Comprehensive paper summaries with key insights
- Reading difficulty assessment (Beginner/Intermediate/Advanced)
- Estimated reading time calculation
- Impact score evaluation
- Key contributions and methodology breakdown

### 🕸️ **Citation Network Visualization**
- Interactive graph showing paper relationships
- Explore cited and citing papers visually
- Discover related research through connections
- Click nodes to explore connected papers

### 👤 **User Features**
- Firebase authentication (email/password & anonymous)
- Bookmarking system for favorite papers
- Search history tracking
- User profile with account management

### 📊 **Modern UI/UX**
- Responsive design for all devices
- Loading overlays with blur effects
- Clean, professional interface
- Circular score visualizations

---

## 🏗️ Architecture

```
┌─────────────────────┐
│  React Frontend     │
│  (Vercel)           │
│  - Homepage         │
│  - Paper Discovery  │
│  - Paper Details    │
│  - Citation Graph   │
│  - About Page       │
└──────────┬──────────┘
           │
           │ HTTPS/CORS
           │
┌──────────▼──────────┐
│  Flask Backend      │
│  (Render.com)       │
│  - Paper Search     │
│  - AI Analysis      │
│  - Graph Building   │
│  - User Auth        │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼───┐   ┌────▼────┐
│OpenAlex│   │ OpenAI  │
│  API   │   │   API   │
└────────┘   └─────────┘
```

---

## 💡 Tech Stack

### **Frontend**
- **Framework**: React 18.2.0
- **Routing**: React Router 7.9.3
- **State Management**: React Context API + Hooks
- **Styling**: Custom CSS with animations
- **Visualization**: D3.js / Vis.js for citation graphs
- **Authentication**: Firebase Auth
- **Hosting**: Vercel (Auto-deploy from GitHub)

### **Backend**
- **Framework**: Flask (Python)
- **AI**: OpenAI GPT-4 for paper analysis
- **Database**: OpenAlex API integration
- **Caching**: In-memory cache for search results
- **Authentication**: Firebase Admin SDK
- **Hosting**: Render.com (2GB RAM, $7/month)

### **External Services**
- **OpenAlex**: Academic paper database (250M+ papers)
- **OpenAI**: Natural language processing and analysis
- **Firebase**: Authentication and user management

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.9+
- OpenAI API key
- Firebase project credentials

### 1. Clone Repository
```bash
git clone https://github.com/Harsha072/scholar-quest.git
cd scholar-quest
```

### 2. Backend Setup
```bash
cd flask-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r app/requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-openai-api-key"
export FIREBASE_ADMIN_SDK_JSON='{"type":"service_account",...}'

# Run Flask server
python app/main.py
```

Backend will start at `http://localhost:5000`

### 3. Frontend Setup
```bash
cd react-frontend

# Install dependencies
npm install

# Create .env file
echo "REACT_APP_API_URL=http://localhost:5000" > .env
echo "REACT_APP_FIREBASE_API_KEY=your-firebase-api-key" >> .env
echo "REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com" >> .env
echo "REACT_APP_FIREBASE_PROJECT_ID=your-project-id" >> .env

# Start development server
npm start
```

Frontend will start at `http://localhost:3000`

---

## 📖 Usage Guide

### 🏠 **Homepage**
1. Enter a research question in natural language
2. Click "Search" or press Enter
3. View loading overlay while papers are being discovered
4. Redirected to Paper Discovery page with results

### 📚 **Paper Discovery**
- **View Results**: See relevant papers with metadata
- **Relevance Scores**: AI-calculated relevance percentage
- **View Details**: Generate comprehensive AI analysis
- **Build Graph**: Visualize citation relationships
- **Bookmark**: Save papers for later (requires sign-in)

### 📄 **Paper Details**
- **Circular Scores**: Relevance and Impact displayed visually
- **AI Analysis**: Brief and detailed summaries
- **Key Contributions**: Bullet-point highlights
- **Methodology**: Research approach overview
- **Reading Difficulty**: Beginner/Intermediate/Advanced
- **Estimated Time**: How long to read the paper

### 🕸️ **Citation Graph**
- **Interactive Nodes**: Click to explore connections
- **Color Coding**: Different colors for paper types
- **Zoom & Pan**: Navigate large graphs easily
- **Cached Data**: Fast loading on page refresh

### 👤 **User Account**
- **Sign Up**: Create account with email/password
- **Anonymous Mode**: Browse without account
- **Profile**: View account info and last sign-in
- **Sign Out**: Secure logout

---

## 🎯 API Endpoints

**Base URL**: `https://scholar-quest-backend-v2.onrender.com`

### Health Check
```bash
GET /api/health
```

### Search Papers
```bash
POST /api/discover-papers
Content-Type: application/json

{
  "query": "machine learning in healthcare",
  "max_results": 10
}
```

### Get Paper Details & Analysis
```bash
POST /api/paper-details
Content-Type: application/json

{
  "title": "Paper Title",
  "authors": ["Author 1", "Author 2"],
  "abstract": "Paper abstract...",
  "openalex_work_id": "W1234567890"
}
```

### Build Citation Graph
```bash
GET /api/paper-relationships/{paper_id}?max_connections=10
```

---

## 📁 Project Structure

```
pdf-summariser-microservice/
├── flask-api/                    # Backend (Python/Flask)
│   ├── app/
│   │   ├── main.py              # Main API routes
│   │   ├── rag_pipeline.py      # AI analysis logic
│   │   ├── simple_paper_relationships.py  # Graph building
│   │   ├── config.py            # Configuration
│   │   ├── logger_config.py     # Logging setup
│   │   └── requirements.txt     # Python dependencies
│   ├── tests/                   # Backend tests
│   └── Dockerfile
│
├── react-frontend/              # Frontend (React)
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header/          # Navigation header
│   │   │   ├── Auth/            # Authentication components
│   │   │   ├── PaperCard/       # Paper display cards
│   │   │   ├── PaperDiscovery/  # Search results page
│   │   │   └── SimplePaperRelationships/  # Citation graph
│   │   ├── pages/
│   │   │   ├── HomePage.js      # Landing page
│   │   │   ├── PaperDetails.js  # Detailed analysis
│   │   │   ├── AboutPage.js     # About Scholar Quest
│   │   │   └── SimplePaperRelationshipsPage.js
│   │   ├── context/
│   │   │   └── AuthContext.js   # Firebase auth context
│   │   ├── services/
│   │   │   └── api.js           # API client
│   │   ├── App.js               # Main app component
│   │   └── index.js             # React entry point
│   ├── package.json
│   └── README.md
│
├── docker-compose.yml           # Local development
├── docker-compose.prod.yml      # Production config
└── README.md                    # This file
```

---

## 🌐 Deployment

### Current Production Deployment

**Backend**: Render.com
- Service: `scholar-quest-backend-v2`
- URL: https://scholar-quest-backend-v2.onrender.com
- Plan: Starter (2GB RAM, $7/month)
- Auto-deploy from GitHub `feature/harsha` branch

**Frontend**: Vercel
- Project: `scholar-quest-three`
- URL: https://scholar-quest-three.vercel.app
- Plan: Hobby (Free)
- Auto-deploy from GitHub `feature/harsha` branch

### Environment Variables

**Backend (Render)**
```env
OPENAI_API_KEY=sk-proj-...
FLASK_ENV=production
FLASK_DEBUG=False
CORS_ORIGINS=https://scholar-quest-three.vercel.app
FIREBASE_ADMIN_SDK_JSON={"type":"service_account",...}
```

**Frontend (Vercel)**
```env
REACT_APP_API_URL=https://scholar-quest-backend-v2.onrender.com
REACT_APP_FIREBASE_API_KEY=...
REACT_APP_FIREBASE_AUTH_DOMAIN=...
REACT_APP_FIREBASE_PROJECT_ID=...
REACT_APP_FIREBASE_STORAGE_BUCKET=...
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=...
REACT_APP_FIREBASE_APP_ID=...
```

---

## ✨ Feature Highlights

### 🎨 **User Interface**
- Clean, modern design with purple gradient accents
- Responsive layout for mobile, tablet, and desktop
- Smooth animations and transitions
- Loading overlays with blur effects
- Circular score visualizations

### 🔐 **Authentication**
- Email/password registration and login
- Anonymous browsing mode
- Firebase integration for secure auth
- User profile with metadata
- Session persistence

### 💾 **Caching System**
- Search results cached in localStorage
- Graph data cached for quick reload
- Session-based cache management
- Automatic cache expiration

### 🎯 **Smart Features**
- AI-powered relevance scoring
- Dynamic loading messages
- Error handling with user-friendly messages
- Compact search bar in results page
- Back navigation with state preservation

---

## 🔧 Development

### Run Tests
```bash
# Backend tests
cd flask-api
pytest tests/

# Frontend tests
cd react-frontend
npm test
```

### Build for Production
```bash
# Frontend build
cd react-frontend
npm run build

# Backend (uses Dockerfile)
cd flask-api
docker build -t scholar-quest-backend .
```

### Code Quality
```bash
# Python linting
flake8 flask-api/app/

# React linting
cd react-frontend
npm run lint
```

---


## 📄 License

This project is licensed under the MIT License.

---

