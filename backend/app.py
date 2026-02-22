from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from data_loader import DataLoader
from schema_analyzer import SchemaAnalyzer
from quality_engine import QualityEngine
from ai_service import AIService
import os
import json

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Global State
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

data_loader = DataLoader() # Assuming data is in ../data or defined in loader
schema_analyzer = None
quality_engine = None
ai_service = None
project_overview = {}
full_documentation = {}
validation_policy = {}

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

def _perform_init(data_dir=None, reset=True):
    """Internal helper to load data and run analysis without specific request context."""
    global schema_analyzer, quality_engine, ai_service, project_overview, full_documentation, validation_policy
    
    # ALWAYS clear full documentation and overview when new data is added
    project_overview = {}
    full_documentation = {}
    validation_policy = {}
    
    tables = data_loader.load_data(data_dir=data_dir, reset=reset)
    if not tables:
        return False
        
    schema_analyzer = SchemaAnalyzer(tables)
    schema = schema_analyzer.analyze()
    
    if ai_service is None:
        ai_service = AIService()
        
    # Strategy 1: AI-Driven Dynamic Audit Rules
    print("Generating AI validation policy...")
    validation_policy = ai_service.generate_validation_policy(schema)
    
    quality_engine = QualityEngine(tables, schema, validation_policy=validation_policy)
    quality_engine.compute_metrics()
    
    print("Generating AI project overview...")
    project_overview = ai_service.generate_project_overview(schema)
    if project_overview:
        print(f"Project Overview generated: {project_overview.get('title')}")
    else:
        print("Warning: Project Overview generation returned None. Using empty dict.")
        project_overview = {}
    return True

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handles multiple CSV file uploads and triggers processing."""
    if 'files' not in request.files:
        return jsonify({"status": "error", "message": "No files provided."}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({"status": "error", "message": "Zero files uploaded."}), 400

    # Check if we should append or clear
    append = request.form.get('append') == 'true'

    if not append:
        # Clear existing files for a fresh upload session
        import shutil
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")

    # Save new files
    for file in files:
        if file and file.filename.endswith('.csv'):
            file.save(os.path.join(UPLOAD_FOLDER, file.filename))

    # Trigger initialization on the upload folder
    try:
        success = _perform_init(UPLOAD_FOLDER, reset=not append)
        if success:
            return jsonify({
                "status": "success",
                "message": f"Successfully uploaded and {'appended' if append else 'processed'} {len(data_loader.tables)} tables.",
                "table_count": len(data_loader.tables),
                "tables": list(data_loader.tables.keys())
            })
        else:
            return jsonify({"status": "error", "message": "No tables detected in the uploaded files. Ensure they are valid .csv files."}), 400
    except Exception as e:
        print(f"Error during initialization: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Internal processing error: {str(e)}"}), 500

@app.route('/api/init', methods=['POST'])
def initialize_route():
    """Initializes the data loading and analysis process via API."""
    if _perform_init():
        return jsonify({
            "status": "success", 
            "message": f"Loaded {len(data_loader.tables)} tables.",
            "table_count": len(data_loader.tables),
            "tables": list(data_loader.tables.keys())
        })
    else:
        return jsonify({"status": "error", "message": "No data found. Please place CSV files in the 'data' folder."}), 404

@app.route('/api/full-docs', methods=['GET'])
def get_full_documentation():
    global full_documentation
    if not schema_analyzer:
        return jsonify({"error": "System not initialized."}), 400
    
    if not full_documentation:
        print("Generating Full AI Documentation...")
        full_documentation = ai_service.generate_full_documentation(schema_analyzer.schema)
        
    return jsonify(full_documentation)

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_metrics():
    if not quality_engine:
        return jsonify({"error": "System not initialized."}), 400
    
    metrics = quality_engine.metrics
    if not metrics:
        return jsonify({"avg_trust_score": 0, "total_tables": 0, "total_rows": 0})
        
    avg_score = sum(m['trust_score'] for m in metrics.values()) / len(metrics)
    total_rows = sum(len(df) for df in data_loader.tables.values())
    
    return jsonify({
        "avg_trust_score": round(avg_score, 2),
        "total_tables": len(data_loader.tables),
        "total_rows": total_rows,
        "project_info": project_overview
    })

@app.route('/api/schema', methods=['GET'])
def get_schema():
    if not schema_analyzer:
        return jsonify({"error": "System not initialized. Call /api/init first."}), 400
    return jsonify(schema_analyzer.schema)

@app.route('/api/quality/<table_name>', methods=['GET'])
def get_quality(table_name):
    if not quality_engine:
         return jsonify({"error": "System not initialized."}), 400
    
    metrics = quality_engine.metrics.get(table_name)
    if not metrics:
        return jsonify({"error": "Table not found."}), 404
        
    return jsonify(metrics)

@app.route('/api/summary/<table_name>', methods=['GET'])
def get_table_summary(table_name):
    if not ai_service or not quality_engine:
        return jsonify({"error": "AI Service not initialized."}), 400
    
    schema = schema_analyzer.schema.get(table_name)
    metrics = quality_engine.metrics.get(table_name)
    
    if not schema or not metrics:
        return jsonify({"error": "Table not found."}), 404
    
    summary = ai_service.generate_table_summary(table_name, schema, metrics)
    return jsonify(summary)

@app.route('/api/outlier-reasoning', methods=['POST'])
def get_outlier_reasoning():
    data = request.json
    table_name = data.get('table_name')
    column_name = data.get('column_name')
    row_index = data.get('row_index')
    
    if not all([table_name, column_name, row_index is not None]):
        return jsonify({"error": "Missing parameters."}), 400
        
    df = data_loader.tables.get(table_name)
    if df is None: return jsonify({"error": "Table not found."}), 404
    
    try:
        row = df.iloc[row_index].to_dict()
        value = row.get(column_name)
        reason = ai_service.reason_outliers(table_name, column_name, row, value)
        return jsonify({"reason": reason})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({"error": "No question provided."}), 400
        
    # Context Construction
    # 'schema' is the key expected by AIService.chat, not 'schemas'
    context = {
        "overview": project_overview, # Include the smart project metadata
        "schema": schema_analyzer.schema if schema_analyzer else {},
        "trust_scores": {k: v['trust_score'] for k, v in quality_engine.metrics.items()} if quality_engine else {}
    }
    
    answer = ai_service.chat(question, context)
    return jsonify({"answer": answer})

@app.route('/api/reset', methods=['POST'])
def reset_session():
    """Clears the current session and uploaded files."""
    global schema_analyzer, quality_engine, ai_service, project_overview
    
    # Clear variables
    schema_analyzer = None
    quality_engine = None
    ai_service = None
    project_overview = {}
    full_documentation = {}
    validation_policy = {}
    data_loader.tables = {}

    # Clear uploads folder
    import shutil
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
                
    return jsonify({"status": "success", "message": "Session reset successful."})

if __name__ == '__main__':
    # Startup data load disabled per user request - use Upload button in UI
    # Note: Ensure GEMINI_API_KEY is set in environment for AI features
    # try:
    #     print("Attempting startup data load...")
    #     _perform_init()
    # except Exception as e:
    #     print(f"Startup load failed (expected if no data): {e}")
        
    app.run(debug=True, port=5000)
