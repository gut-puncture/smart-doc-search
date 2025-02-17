import requests
import json

# Replace with your actual SERPAPI key
SERPAPI_KEY = "cbf80ce581c8639a57533f645730cb00bc9c43051dfcb9f487bc24dca3a50265"
query = "flask official documentation"
url = f"https://serpapi.com/search?engine=google&q={requests.utils.quote(query)}&api_key={SERPAPI_KEY}"

response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    print("SERPAPI Response:")
    print(json.dumps(data, indent=2))
else:
    print("SERPAPI error:", response.status_code, response.text)
