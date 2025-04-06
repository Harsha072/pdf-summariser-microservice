from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from summarise import summarize_pdf
import os
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()

app = Flask(__name__)
api = Api(app)

class SummarizePDF(Resource):
    def post(self):
        # Check if a file is uploaded
        if 'file' not in request.files:
            return {"error": "No file provided"}, 400
        
        pdf_file = request.files['file']
        
        # Validate file type
        if not pdf_file.filename.lower().endswith('.pdf'):
            return {"error": "Only PDF files are supported"}, 400
        
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_path = temp_file.name
            pdf_file.save(temp_path)
        
        try:
            # Generate summary
            summary = summarize_pdf(temp_path)
            
            # Ensure the summary is a string (not a Response object)
            if hasattr(summary, 'data'):
                # If it's a Response object, decode it
                summary = summary.data.decode('utf-8')
            
            return {"summary": summary}, 200
        except Exception as e:
            return {"error": str(e)}, 500
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

# Add the resource to the API
api.add_resource(SummarizePDF, '/summarize')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)