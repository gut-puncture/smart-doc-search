// Handle file upload and dependency extraction
document.getElementById('upload-form').addEventListener('submit', function(e) {
  e.preventDefault();
  const files = document.getElementById('file-input').files;
  if (files.length === 0) {
    alert("Please select at least one file.");
    return;
  }
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files[]', files[i]);
  }
  fetch('/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.libraries) {
      displayLibraries(data.libraries);
    } else {
      alert("No dependencies found.");
    }
  })
  .catch(error => {
    console.error('Error:', error);
    alert("Error extracting dependencies.");
  });
});

function displayLibraries(libraries) {
  const section = document.getElementById('dependencies-section');
  const listDiv = document.getElementById('libraries-list');
  listDiv.innerHTML = '';
  libraries.forEach(lib => {
    const checkbox = document.createElement('input');
    checkbox.type = "checkbox";
    checkbox.name = "library";
    checkbox.value = lib;
    checkbox.checked = true;
    const label = document.createElement('label');
    label.textContent = lib;
    const div = document.createElement('div');
    div.appendChild(checkbox);
    div.appendChild(label);
    listDiv.appendChild(div);
  });
  section.style.display = 'block';
}

// Handle library confirmation and documentation fetching
document.getElementById('libraries-form').addEventListener('submit', function(e) {
  e.preventDefault();
  const selectedLibraries = [];
  document.getElementsByName('library').forEach(cb => {
    if (cb.checked) {
      selectedLibraries.push(cb.value);
    }
  });
  if (selectedLibraries.length === 0) {
    alert("Please select at least one library.");
    return;
  }
  const outputOption = document.querySelector('input[name="output_option"]:checked').value;
  const serpapiKey = document.getElementById('serpapi-key').value.trim();
  const geminiKey = document.getElementById('gemini-key').value.trim();
  if (!serpapiKey || !geminiKey) {
    alert("Please enter both SERPAPI and Gemini API keys.");
    return;
  }
  // Process each library sequentially
  fetchDocumentation(selectedLibraries, serpapiKey, geminiKey, outputOption);
});

async function fetchDocumentation(libraries, serpapiKey, geminiKey, outputOption) {
  const results = {};
  for (let lib of libraries) {
    // Step 1: Use SERPAPI to search for the official documentation
    const searchQuery = encodeURIComponent(lib + " official documentation");
    const serpapiURL = `https://serpapi.com/search?engine=google&q=${searchQuery}&api_key=${serpapiKey}`;
    let serpapiResponse = await fetch(serpapiURL);
    let serpapiData = await serpapiResponse.json();
    // For simplicity, choose the first organic result
    let candidateURL = "";
    if (serpapiData && serpapiData.organic_results && serpapiData.organic_results.length > 0) {
      candidateURL = serpapiData.organic_results[0].link;
    } else {
      candidateURL = "";
    }
    if (!candidateURL) {
      results[lib] = "No documentation found.";
      continue;
    }
    // Step 2: Use Gemini API to verify and select the best URL
    const geminiPrompt = {
      "model": "gemini-2.0-flash-exp",
      "contents": `Given the following search results from SERPAPI for library "${lib}": ${JSON.stringify(serpapiData.organic_results.slice(0, 3))}. Select the most official and stable documentation URL. Only return the URL.`
    };
    let geminiURL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${geminiKey}`;
    let geminiResponse = await fetch(geminiURL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(geminiPrompt)
    });
    let geminiData = await geminiResponse.json();
    let chosenURL = candidateURL; // default if Gemini fails
    if (geminiData && geminiData.candidates && geminiData.candidates.length > 0) {
      chosenURL = geminiData.candidates[0].output.trim();
    }
    // Step 3: Fetch the documentation page content (using a free CORS proxy)
    const proxyURL = "https://api.allorigins.hexocode.repl.co/get?disableCache=true&url=" + encodeURIComponent(chosenURL);
    let pageResponse = await fetch(proxyURL);
    let pageData = await pageResponse.json();
    let htmlContent = pageData.contents;
    // Step 4: Convert HTML content to plain text, preserving headers and code blocks
    let plainText = parseHTMLToPlainText(htmlContent);
    // Step 5: Split text if it exceeds ~30k tokens (approximate by word count)
    let splitTexts = splitText(plainText, 30000);
    results[lib] = splitTexts;
  }
  displayResults(results, outputOption);
}

function parseHTMLToPlainText(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  let output = "";

  // Recursive function to process elements
  function processElement(el) {
    let text = "";
    if (el.tagName && (el.tagName.match(/^H[1-6]$/) || el.tagName === "P")) {
      text += el.textContent + "\n\n";
    } else if (el.tagName === "PRE" || el.tagName === "CODE") {
      text += "code block:\n" + el.textContent + "\n\n";
    }
    el.childNodes.forEach(child => {
      if (child.nodeType === Node.ELEMENT_NODE) {
        text += processElement(child);
      }
    });
    return text;
  }
  output = processElement(doc.body);
  return output;
}

function splitText(text, maxTokens) {
  // Approximate splitting by words (assume 1 token ~ 0.75 words)
  const words = text.split(/\s+/);
  if (words.length <= maxTokens) {
    return [text];
  }
  const chunks = [];
  for (let i = 0; i < words.length; i += maxTokens) {
    chunks.push(words.slice(i, i + maxTokens).join(" "));
  }
  return chunks;
}

function displayResults(results, outputOption) {
  const resultSection = document.getElementById('result-section');
  const outputTextArea = document.getElementById('output-text');
  const downloadLinksDiv = document.getElementById('download-links');
  downloadLinksDiv.innerHTML = "";
  let consolidatedOutput = "";
  if (outputOption === "consolidated") {
    for (let lib in results) {
      consolidatedOutput += "Documentation for " + lib + ":\n\n";
      results[lib].forEach(chunk => {
        consolidatedOutput += chunk + "\n\n";
      });
      consolidatedOutput += "-------------------------\n\n";
    }
    outputTextArea.value = consolidatedOutput;
    // Create a download link for the consolidated file
    const blob = new Blob([consolidatedOutput], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = "documentation.txt";
    link.textContent = "Download Consolidated Documentation";
    downloadLinksDiv.appendChild(link);
  } else {
    // Create separate files for each library
    for (let lib in results) {
      let libOutput = "Documentation for " + lib + ":\n\n";
      results[lib].forEach(chunk => {
        libOutput += chunk + "\n\n";
      });
      const blob = new Blob([libOutput], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = lib + "_documentation.txt";
      link.textContent = "Download " + lib + " Documentation";
      const div = document.createElement('div');
      div.appendChild(link);
      downloadLinksDiv.appendChild(div);
    }
    outputTextArea.value = "Separate files generated. Use download links below.";
  }
  resultSection.style.display = 'block';
}
