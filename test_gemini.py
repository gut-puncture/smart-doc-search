import requests
import json

# Replace with your actual Gemini API key
GEMINI_KEY = <key>
# Example payload with a sample SERPAPI result for Flask documentation
payload = {
    "contents": [
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        'Given the following SERPAPI results for library "flask": '
                        '[{"position": 1, "title": "Welcome to Flask — Flask Documentation (3.1.x)", "link": "https://flask.palletsprojects.com/"},'
                        ' {"position": 2, "title": "Flask Intro — Python Beginners documentation - Read the Docs", "link": "https://python-adv-web-apps.readthedocs.io/en/latest/flask.html"},'
                        ' {"position": 3, "title": "Welcome to Flask — Flask 0.13.dev documentation", "link": "https://azcv.readthedocs.io/"}]. '
                        "Select the most official and stable documentation URL. Only return the URL. Always return a URL."
                    )
                }
            ]
        }
    ]
}

gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_KEY}"
headers = {"Content-Type": "application/json"}
response = requests.post(gemini_url, json=payload, headers=headers)

if response.status_code == 200:
    data = response.json()
    print("Gemini Response:")
    print(json.dumps(data, indent=2))
else:
    print("Gemini API error:", response.status_code, response.text)
