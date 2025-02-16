import json
import re
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Allowed file extensions (only code files)
ALLOWED_EXTENSIONS = {'py', 'js', 'json', 'txt', 'java', 'c', 'cpp', 'ts', 'go', 'rb'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_dependencies_from_code(content, filename):
    dependencies = set()
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'py':
        # Extract import and from statements in Python files
        imports = re.findall(r'^\s*(?:import|from)\s+([\w\.]+)', content, re.MULTILINE)
        dependencies.update(imports)
    elif ext in ['js', 'ts']:
        # For JavaScript/TypeScript, look for require() and ES6 import statements
        reqs = re.findall(r'require\(["\']([\w\-/]+)["\']\)', content)
        imports = re.findall(r'import\s+(?:[\w\{\}\*\s,]+)\s+from\s+["\']([\w\-/]+)["\']', content)
        dependencies.update(reqs)
        dependencies.update(imports)
    # Additional language-specific parsing can be added here.
    return dependencies

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    files = request.files.getlist('files[]')
    all_dependencies = set()
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            content = file.read().decode('utf-8', errors='ignore')
            # Special handling for package manager files:
            if filename == 'package.json':
                try:
                    pkg = json.loads(content)
                    if 'dependencies' in pkg:
                        all_dependencies.update(pkg['dependencies'].keys())
                    if 'devDependencies' in pkg:
                        all_dependencies.update(pkg['devDependencies'].keys())
                except Exception:
                    pass
            elif filename == 'requirements.txt':
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Strip version specifiers (e.g., "flask>=2.0")
                        lib = re.split('[<>=]', line)[0].strip()
                        if lib:
                            all_dependencies.add(lib)
            else:
                # For source code files, do basic extraction
                deps = extract_dependencies_from_code(content, filename)
                all_dependencies.update(deps)
    return jsonify({'libraries': list(all_dependencies)})

if __name__ == '__main__':
    app.run(debug=True)
