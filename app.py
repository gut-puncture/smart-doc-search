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
        pattern_rb = r'require\s+[\'"]([^\'"]+)[\'"]'
        matches_rb = re.findall(pattern_rb, content)
        dependencies.update(matches_rb)
        pattern_gem = r'gem\s+install\s+([\w\-]+)'
        matches_gem = re.findall(pattern_gem, content)
        dependencies.update(matches_gem)
    elif ext == 'go':
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
        pattern_java = r'import\s+([\w\.]+);'
        matches_java = re.findall(pattern_java, content)
        for match in matches_java:
            dependencies.add(match.split('.')[0])
    else:
        pattern_generic = r'(?:pip|npm|gem)\s+install\s+([\w\-]+)'
        matches_generic = re.findall(pattern_generic, content)
        dependencies.update(matches_generic)
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
            app.logger.info(f"SERPAPI data for {lib}:\n{json.dumps(serpapi_data, indent=2)}")
            organic_results = serpapi_data.get("organic_results", [])
            if not organic_results:
                results[lib] = ["No documentation found via SERPAPI."]
                continue

            # Take the top 3 results and include additional info (position, title, link)
            filtered_results = []
            for res in organic_results[:3]:
                filtered_results.append({
                    "position": res.get("position"),
                    "title": res.get("title"),
                    "link": res.get("link")
                })
            results_json = json.dumps(filtered_results)
            gemini_payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    f"Given the following SERPAPI results for library \"{lib}\": {results_json}. "
                                    "Select the most official and stable documentation URL. Only return the URL. You must always return a URL or the program breaks."
                                )
                            }
                        ]
                    }
                ]
            }
            app.logger.info(f"Gemini payload for {lib}:\n{json.dumps(gemini_payload, indent=2)}")
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={geminiKey}"
            app.logger.info(f"Calling Gemini API for {lib} with payload: {gemini_payload}")
            gemini_resp = requests.post(gemini_url, json=gemini_payload, headers={'Content-Type': 'application/json'})
            if gemini_resp.status_code != 200:
                error_body = gemini_resp.text
                app.logger.error(f"Gemini API error for {lib}: {gemini_resp.status_code}. Response: {error_body}")
                results[lib] = [f"Gemini API error: {gemini_resp.status_code}. Response: {error_body}"]
                continue
            gemini_data = gemini_resp.json()
            app.logger.info(f"Gemini response for {lib}:\n{json.dumps(gemini_data, indent=2)}")
            candidates = gemini_data.get("candidates", [])
            chosen_url = ""
            if candidates:
                chosen_url = candidates[0].get("output", "").strip()
            app.logger.info(f"Chosen URL from Gemini for {lib}: '{chosen_url}'")
            if not chosen_url:
            # Fallback to the first SERPAPI result's link
                if filtered_results and filtered_results[0].get("link"):
                    fallback_url = filtered_results[0]["link"]
                    app.logger.warning(f"Gemini returned no valid URL for {lib}; falling back to SERPAPI link: {fallback_url}")
                    chosen_url = fallback_url
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
            app.logger.error(f"Error processing library {lib}: {str(e)}")
            results[lib] = [f"Error processing library: {str(e)}"]
    return jsonify(results)

#temporary debug endpoint
@app.route('/debug_gemini', methods=['GET'])
def debug_gemini():
    lib = "flask"
    test_results = [
        {"position": 1, "title": "Welcome to Flask — Flask Documentation (3.1.x)", "link": "https://flask.palletsprojects.com/"},
        {"position": 2, "title": "Flask Intro — Python Beginners documentation - Read the Docs", "link": "https://python-adv-web-apps.readthedocs.io/en/latest/flask.html"},
        {"position": 3, "title": "Welcome to Flask — Flask 0.13.dev documentation", "link": "https://azcv.readthedocs.io/"}
    ]
    results_json = json.dumps(test_results)
    gemini_payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"Given the following SERPAPI results for library \"{lib}\": {results_json}. "
                            "Select the most official and stable documentation URL. Only return the URL. Always return a URL."
                        )
                    }
                ]
            }
        ]
    }
    app.logger.info(f"Debug Gemini payload for {lib}:\n{json.dumps(gemini_payload, indent=2)}")
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=YOUR_GEMINI_API_KEY"
    headers = {'Content-Type': 'application/json'}
    resp = requests.post(gemini_url, json=gemini_payload, headers=headers)
    app.logger.info(f"Debug Gemini response for {lib}:\n{resp.text}")
    return resp.text, resp.status_code


if __name__ == '__main__':
    app.run(debug=True)
