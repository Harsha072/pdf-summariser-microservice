#!/usr/bin/env python3
"""
PDF AI Assistant - Startup Script
Easily start the Flask backend and choose between interfaces
"""

import subprocess
import sys
import os
import time
import threading
import requests
from pathlib import Path

def start_backend():
    """Start the Flask backend server"""
    print("🚀 Starting Flask Backend...")
    backend_path = Path("flask-api/app")
    print(backend_path)
    if not backend_path.exists():
        print("❌ Flask backend not found! Make sure you're in the project root directory.")
        sys.exit(1)
    
    # Start Flask backend
    env = os.environ.copy()
    env['FLASK_APP'] = 'main.py'
    env['FLASK_ENV'] = 'development'
    
    backend_process = subprocess.Popen([
        sys.executable, '-m', 'flask', 'run', 
        '--host=0.0.0.0', '--port=5000'
    ], cwd=backend_path, env=env)
    
    # Wait for backend to start
    print("⏳ Waiting for backend to start...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get("http://localhost:5000/", timeout=2)
            if response.status_code == 200:
                print("✅ Flask backend is running at http://localhost:5000")
                break
        except:
            time.sleep(1)
    else:
        print("⚠️ Backend might not have started properly, but continuing...")
    
    return backend_process

def start_frontend():
    """Open the HTML frontend interface"""
    print("� Opening HTML Frontend Interface...")
    html_path = Path("frontend/index.html").resolve()
    
    if not html_path.exists():
        print("❌ Frontend interface not found!")
        sys.exit(1)
    
    import webbrowser
    file_url = f"file:///{html_path}"
    print(f"🎨 Opening frontend: {file_url}")
    webbrowser.open(file_url)
    
    print("✅ Frontend interface opened in your default browser")
    print("💡 Professional HTML + JavaScript interface with advanced PDF.js integration")
    
    return None  # No process to track for HTML interface

def show_menu():
    """Show the startup menu"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           📄 PDF AI Assistant                                ║
║                      Choose your interface option                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  1. 🚀 Full Stack (Flask Backend + HTML Frontend)                          ║
║     - Complete solution with professional PDF viewer                    ║
║     - Advanced HTML + JavaScript interface with PDF.js                  ║
║                                                                              ║
║  2. 🖥️  Backend Only (Flask API Server)                                      ║
║     - Just the API server for custom frontend development                   ║
║     - Use with the HTML interface or your own frontend                      ║
║                                                                              ║
║  3. 🌐 Open HTML Frontend                                                   ║
║     - Professional PDF viewer with PDF.js integration                   ║
║     - Modern responsive interface with advanced features                ║
║                                                                              ║
║  4. 📖 API Documentation                                                     ║
║     - View available endpoints and usage examples                           ║
║                                                                              ║
║  5. 🛠️  Development Info                                                     ║
║     - Project structure and development tips                                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

def show_api_docs():
    """Show API documentation"""
    print("""
📖 API DOCUMENTATION
═══════════════════════════════════════════════════════════════════════════════

🔗 Base URL: http://localhost:5000

📌 ENDPOINTS:

1. POST /upload
   - Upload PDF document for processing
   - Body: multipart/form-data with 'file' field
   - Returns: {"doc_id": "uuid", "message": "success message"}

2. POST /summarize  
   - Generate document summary
   - Body: {"doc_id": "uuid"}
   - Returns: {"answer": "summary text"}

3. POST /ask
   - Ask questions about document
   - Body: {"doc_id": "uuid", "question": "your question"}
   - Returns: {
       "answer": "AI response", 
       "sources": [
         {
           "filename": "document.pdf",
           "page": 5,
           "section_heading": "Introduction", 
           "snippet": "relevant text quote",
           "doc_id": "uuid",
           "chunk_id": "chunk_uuid"
         }
       ]
     }

4. POST /save
   - Save analysis results
   - Body: {"doc_id": "uuid", "content": "content to save"}
   - Returns: {"message": "saved successfully"}

💡 CURL EXAMPLES:

# Upload document
curl -X POST -F "file=@document.pdf" http://localhost:5000/upload

# Ask question  
curl -X POST -H "Content-Type: application/json" \\
  -d '{"doc_id":"your-doc-id","question":"What are the main findings?"}' \\
  http://localhost:5000/ask

═══════════════════════════════════════════════════════════════════════════════
    """)

def show_dev_info():
    """Show development information"""
    print("""
🛠️  DEVELOPMENT INFO
═══════════════════════════════════════════════════════════════════════════════

📁 PROJECT STRUCTURE:
├── flask-api/              # Flask backend API
│   ├── app/
│   │   ├── main.py         # Main Flask application
│   │   ├── retriever.py    # Document processing & retrieval
│   │   ├── summarise.py    # AI summarization logic
│   │   └── requirements.txt
│   └── Dockerfile
├── frontend/               # Pure HTML + JavaScript interface  
│   └── index.html          # Professional PDF viewer with PDF.js
├── chroma_db/              # Vector database storage
└── docker-compose.yml      # Container orchestration

🔧 KEY FEATURES:
✅ PDF document upload and processing
✅ AI-powered summarization using OpenAI GPT
✅ Question-answering with detailed source attribution  
✅ ChromaDB vector storage for fast retrieval
✅ Section heading detection and page number tracking
✅ Professional PDF viewer with PDF.js integration
✅ Modern responsive HTML + JavaScript interface
✅ No Python frontend dependencies - pure web technologies

🚀 DEPLOYMENT OPTIONS:
• Local development: python start_app.py
• Docker: docker-compose up
• Cloud platforms: Render, Railway, Google Cloud Run

💡 TECH STACK:
• Backend: Flask, ChromaDB, OpenAI API, PyPDF2
• Frontend: Pure HTML + CSS + JavaScript with PDF.js
• Vector DB: ChromaDB with sentence transformers
• AI: OpenAI GPT-3.5/4 for summarization and Q&A
• No Python frontend dependencies - standard web technologies

═══════════════════════════════════════════════════════════════════════════════
    """)

def main():
    """Main application entry point"""
    os.chdir(Path(__file__).parent)  # Change to project directory
    
    while True:
        show_menu()
        
        try:
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == '1':
                # Full stack
                backend_process = start_backend()
                time.sleep(3)  # Give backend time to fully start
                start_frontend()  # Open frontend in browser
                
                print("\n🎉 Full stack is running!")
                print("🌐 Frontend Interface: Opened in your browser")
                print("🔗 Flask Backend: http://localhost:5000")
                print("\n💡 Press Ctrl+C to stop the backend service")
                
                try:
                    # Wait for backend process
                    backend_process.wait()
                except KeyboardInterrupt:
                    print("\n🛑 Shutting down backend...")
                    backend_process.terminate()
                    print("✅ Backend stopped")
                    break
                    
            elif choice == '2':
                # Backend only
                backend_process = start_backend()
                print("\n🔗 Backend running at http://localhost:5000")
                print("💡 Press Ctrl+C to stop")
                
                try:
                    backend_process.wait()
                except KeyboardInterrupt:
                    print("\n🛑 Shutting down backend...")
                    backend_process.terminate()
                    print("✅ Backend stopped")
                    break
                    
            elif choice == '3':
                # Frontend interface
                start_frontend()
                input("\n📍 Press Enter to return to menu...")
                
            elif choice == '4':
                # API docs
                show_api_docs()
                input("\n📍 Press Enter to return to menu...")
                
            elif choice == '5':
                # Dev info
                show_dev_info()
                input("\n📍 Press Enter to return to menu...")
                
            else:
                print("❌ Invalid choice. Please select 1-5.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()