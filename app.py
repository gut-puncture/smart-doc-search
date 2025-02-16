import json
import re
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Allowed file extensions (only code files)
ALLOWED_EXTENSIONS = {'py', 'js', 'json', 'txt', 'java', 'c', 'cpp', 'ts', 'go', 'rb'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_dependencies_from_code(content, filename):
    dependencies = set()
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'py':
        # Robust extraction for Python: capture both "import" and "from" statements,
        # handling multiple modules per line.
        pattern1 = r'^\s*import\s+([\w\.]+(?:\s*,\s*[\w\.]+)*)'
        pattern2 = r'^\s*from\s+([\w\.]+)\s+import'
        matches1 = re.findall(pattern1, content, re.MULTILINE)
        matches2 = re.findall(pattern2, content, re.MULTILINE)
        for match in matches1:
            for mod in match.split(','):
                mod = mod.strip().split('.')[0]
                if mod:
                    dependencies.add(mod)
        for match in matches2:
            mod = match.strip().split('.')[0]
            if mod:
                dependencies.add(mod)
    elif ext in ['js', 'ts']:
        # Robust extraction for JavaScript/TypeScript:
        # handle require(), ES6 import, and dynamic import()
        pattern_require = r'require\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        pattern_import = r'import\s+(?:[\w\{\}\*\s,]+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        pattern_dynamic = r'import\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        matches_require = re.findall(pattern_require, content)
        matches_import = re.findall(pattern_import, content)
        matches_dynamic = re.findall(pattern_dynamic, content)
        dependencies.update(matches_require)
        dependencies.update(matches_import)
        dependencies.update(matches_dynamic)
    elif ext == 'rb':
        # Ruby: require statements
        pattern_rb = r'require\s+[\'"]([^\'"]+)[\'"]'
        matches = re.findall(pattern_rb, content)
        dependencies.update(matches)
    elif ext == 'go':
        # Go: import statements (single-line and grouped)
        pattern_go_single = r'import\s+[\'"]([^\'"]+)[\'"]'
        pattern_go_group = r'import\s*\(\s*([^)]*)\)'
        matches_single = re.findall(pattern_go_single, content)
        dependencies.update(matches_single)
        matches_group = re.findall(pattern_go_group, content, re.MULTILINE | re.DOTALL)
        for group in matches_group:
            for line in group.splitlines():
                line = line.strip().strip('"')
                if line:
                    dependencies.add(line)
    elif ext == 'java':
        # Java: import statements (returning the base package as dependency)
        pattern_java = r'import\s+([\w\.]+);'
        matches = re.findall(pattern_java, content)
        for match in matches:
            dependencies.add(match.split('.')[0])
    # Additional language-specific extraction rules can be added here if needed.
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
            try:
                content = file.read().decode('utf-8', errors='ignore')
            except Exception as e:
                app.logger.error(f"Error reading {filename}: {e}")
                continue
            # Special handling for package manager files:
            if filename == 'package.json':
                try:
                    pkg = json.loads(content)
                    if 'dependencies' in pkg:
                        all_dependencies.update(pkg['dependencies'].keys())
                    if 'devDependencies' in pkg:
                        all_dependencies.update(pkg['devDependencies'].keys())
                except Exception as e:
                    app.logger.error(f"Error parsing {filename}: {e}")
            elif filename == 'requirements.txt':
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Strip version specifiers (e.g., "flask>=2.0")
                        lib = re.split('[<>=]', line)[0].strip()
                        if lib:
                            all_dependencies.add(lib)
            else:
                # For source code files, use our robust dependency extraction
                deps = extract_dependencies_from_code(content, filename)
                all_dependencies.update(deps)
    return jsonify({'libraries': list(all_dependencies)})

if __name__ == '__main__':
    app.run(debug=True)
