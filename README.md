# AI-Powered PDF Summarizer & Q&A System (RAG Architecture)

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![LangChain](https://img.shields.io/badge/LangChain-0.1%2B-orange)
![OpenAI](https://img.shields.io/badge/OpenAI-API-yellow)
![Docker](https://img.shields.io/badge/Docker-Compose-important)

A microservice-based system that summarizes PDFs and answers questions about their content using **Retrieval-Augmented Generation (RAG)**. Deploys with Docker for production-ready scaling.

## ✨ Features
- **Document Summarization**: Generate concise summaries of uploaded PDFs.
- **Semantic Q&A**: Ask questions about the PDF content (grounded in the document).
- **Microservice Architecture**:
  - Flask API (Python) for backend processing.
  - Gradio UI for interactive demos.
  - ChromaDB for vector storage (alternatives: Pinecone, FAISS).
- **Deployment-Ready**: Docker Compose for local/dev environments.

## 🛠️ Tech Stack
- **Backend**: Python, Flask, LangChain, OpenAI API
- **Vector DB**: ChromaDB (default) / Pinecone (cloud)
- **Frontend**: Gradio
- **Infra**: Docker, Docker Compose

## 🚀 Quick Start
### Prerequisites
- Python 3.9+
- [Docker](https://www.docker.com/)
- OpenAI API key (set in `.env`)

### Run Locally
1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/pdf-summarizer-rag.git
   cd pdf-summarizer-rag
