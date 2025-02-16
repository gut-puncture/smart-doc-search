import json
import re
import logging
import requests
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Allowed file extensions for text-based code files
ALLOWED_EXTENSIONS = {'py', 'js', 'json', 'txt', 'java', 'c', 'cpp', 'ts', 'go', 'rb'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_dependencies_from_code(content, filename):
    dependencies = set()
    ext = filename.rsplit('.', 1)[1].lower()

    if ext == 'py':
        # Robust Python extraction: imports and pip install commands
        pattern_import = r'^\s*import\s+([\w\.]+(?:\s*,\s*[\w\.]+)*)'
        pattern_from = r'^\s*from\s+([\w\.]+)\s+import'
        matches_import = re.findall(pattern_import, content, re.MULTILINE)
        matches_from = re.findall(pattern_from, content, re.MULTILINE)
        for match in matches_import:
            for mod in match.split(','):
                mod = mod.strip().split('.')[0]
                if mod:
                    dependencies.add(mod)
        for match in matches_from:
            mod = match.strip().split('.')[0]
            if mod:
                dependencies.add(mod)
        pattern_pip = r'(?:!pip\s+install|pip\s+install)\s+([\w\-]+)'
        matches_pip = re.findall(pattern_pip, content)
        dependencies.update(matches_pip)
    elif ext in ['js', 'ts']:
        # Robust JavaScript/TypeScript extraction: require/import/dynamic import and npm install commands
        pattern_require = r'require\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        pattern_import = r'import\s+(?:[\w\{\}\*\s,]+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        pattern_dynamic = r'import\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        matches_require = re.findall(pattern_require, content)
        matches_import = re.findall(pattern_import, content)
        matches_dynamic = re.findall(pattern_dynamic, content)
        dependencies.update(matches_require)
        dependencies.update(matches_import)
        dependencies.update(matches_dynamic)
        pattern_npm = r'npm\s+install\s+([\w\-]+)'
        matches_npm = re.findall(pattern_npm, content)
        dependencies.update(matches_npm)
    elif ext == 'rb':
        # Ruby: require and gem install commands
        pattern_rb = r'require\s+[\'"]([^\'"]+)[\'"]'
        matches_rb = re.findall(pattern_rb, content)
        dependencies.update(matches_rb)
        pattern_gem = r'gem\s+install\s+([\w\-]+)'
        matches_gem = re.findall(pattern_gem, content)
        dependencies.update(matches_gem)
    elif ext == 'go':
        # Go: handle single and grouped import statements
        pattern_go_single = r'import\s+[\'"]([^\'"]+)[\'"]'
        pattern_go_group = r'import\s*\(\s*([^)]*)\)'
        matches_go_single = re.findall(pattern_go_single, content)
        dependencies.update(matches_go_single)
        matches_go_group = re.findall(pattern_go_group, content, re.MULTILINE | re.DOTALL)
        for group in matches_go_group:
            for line in group.splitlines():
                line = line.strip().strip('"')
                if line:
                    dependencies.add(line)
    elif ext == 'java':
        # Java: capture import statements and return the base package as dependency
        pattern_java = r'import\s+([\w\.]+);'
        matches_java = re.findall(pattern_java, content)
        for match in matches_java:
            dependencies.add(match.split('.')[0])
    else:
        # For any other text-based file, use a generic pattern
        pattern_generic = r'(?:pip|npm|gem)\s+install\s+([\w\-]+)'
        matches_generic = re.findall(pattern_generic, content)
        dependencies.update(matches_generic)
    # Additional generic extraction: catch any "install <package>" patterns
    pattern_generic2 = r'install\s+([\w\-]+)'
    matches_generic2 = re.findall(pattern_generic2, content)
    dependencies.update(matches_generic2)
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
                        lib = re.split('[<>=]', line)[0].strip()
                        if lib:
                            all_dependencies.add(lib)
            else:
                deps = extract_dependencies_from_code(content, filename)
                all_dependencies.update(deps)
    app.logger.info("Extracted dependencies: " + str(all_dependencies))
    return jsonify({'libraries': list(all_dependencies)})

def process_element(elem):
    text = ""
    if elem.name:
        tag = elem.name.lower()
        if tag in ['h1','h2','h3','h4','h5','h6']:
            text += elem.get_text(strip=True).upper() + "\n\n"
        elif tag == 'p':
            text += elem.get_text(strip=True) + "\n\n"
        elif tag in ['pre', 'code']:
            text += "code block:\n" + elem.get_text() + "\n\n"
        else:
            for child in elem.children:
                text += process_element(child)
    elif elem.string:
        text += elem.string.strip() + " "
    return text

def html_to_plain_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.body if soup.body else soup
    return process_element(body)

def split_text(text, max_words):
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i:i+max_words]))
    return chunks

@app.route('/fetch_docs', methods=['POST'])
def fetch_docs():
    data = request.get_json()
    libraries = data.get("libraries", [])
    serpapiKey = data.get("serpapiKey")
    geminiKey = data.get("geminiKey")
    results = {}
    for lib in libraries:
        try:
            app.logger.info(f"Processing library: {lib}")
            search_query = f"{lib} official documentation"
            serpapi_url = f"https://serpapi.com/search?engine=google&q={requests.utils.quote(search_query)}&api_key={serpapiKey}"
            app.logger.info(f"SERPAPI URL for {lib}: {serpapi_url}")
            serpapi_resp = requests.get(serpapi_url)
            if serpapi_resp.status_code != 200:
                results[lib] = [f"SERPAPI error: {serpapi_resp.status_code}"]
                continue
            serpapi_data = serpapi_resp.json()
            organic_results = serpapi_data.get("organic_results", [])
            if not organic_results:
                results[lib] = ["No documentation found via SERPAPI."]
                continue
            gemini_prompt = {
                "model": "gemini-2.0-flash-exp",
                "contents": f"Given the following SERPAPI results for library \"{lib}\": {organic_results}. Select the most official and stable documentation URL. Only return the URL."
            }
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={geminiKey}"
            app.logger.info(f"Calling Gemini API for {lib} with payload: {gemini_prompt}")
            gemini_resp = requests.post(gemini_url, json=gemini_prompt, headers={'Content-Type': 'application/json'})
            if gemini_resp.status_code != 200:
                results[lib] = [f"Gemini API error: {gemini_resp.status_code}"]
                continue
            gemini_data = gemini_resp.json()
            candidates = gemini_data.get("candidates", [])
            chosen_url = ""
            if candidates:
                chosen_url = candidates[0].get("output", "").strip()
            if not chosen_url:
                results[lib] = ["No valid documentation URL returned by Gemini."]
                continue
            app.logger.info(f"Chosen URL for {lib}: {chosen_url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            page_resp = requests.get(chosen_url, headers=headers)
            if page_resp.status_code != 200:
                results[lib] = [f"Error fetching page: {page_resp.status_code}"]
                continue
            html_content = page_resp.text
            plain_text = html_to_plain_text(html_content)
            chunks = split_text(plain_text, 30000)
            results[lib] = chunks
        except Exception as e:
            results[lib] = [f"Error processing library: {str(e)}"]
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
