# Dependency Documentation Fetcher

This MVP web app lets you upload multiple code files, extracts all dependencies (from source code and package manager files like `package.json` and `requirements.txt`), and then fetches the official documentation for each dependency using SERPAPI and the Gemini API. The output is produced as plain text (with headers and code blocks preserved) and can be delivered as one consolidated file or as separate files per library. If the documentation exceeds ~30k tokens, it is automatically split into parts.

## Features
- **Multiple File Upload:** Upload several code files at once. Non-code or binary files are automatically filtered out.
- **Deep Dependency Analysis:** Custom parsing of `package.json`, `requirements.txt`, and source code (Python, JavaScript/TypeScript, etc.) extracts all libraries used.
- **Preview & Confirmation:** View detected libraries as checkboxes so you can deselect any you don’t want processed.
- **API Integration:**
  - **SERPAPI:** Searches for official documentation pages.
  - **Gemini API:** Using the "gemini-2.0-flash-exp" model and robust prompt instructions, it verifies and selects the most official and stable documentation URL.
  - **Security:** API keys for SERPAPI and Gemini are entered via dedicated fields in the UI and never leave your device.
- **Documentation Formatting:** Fetched documentation is converted to plain text, preserving headers and exact code blocks (marked with “code block”) while stripping out HTML.
- **Output Splitting:** If documentation exceeds ~30k tokens, the output is automatically split.
- **Output Options:** Choose to generate one consolidated text file or separate files per library.

## Tech Stack
- **Frontend:** HTML, CSS, and JavaScript.
- **Backend:** Python (Flask).

## Files
- `app.py`: Flask backend for file upload and dependency extraction.
- `templates/index.html`: The UI for file upload, dependency preview, API key entry, and output display.
- `static/style.css`: Styling for the UI.
- `static/main.js`: JavaScript handling file uploads, API integration, documentation processing, and download link generation.
- `requirements.txt`: Python dependencies.
- `README.md`: This documentation.

## Running Locally
1. **Clone the Repository:**
   ```bash
   git clone <repository_url>
   cd <repository_directory>
