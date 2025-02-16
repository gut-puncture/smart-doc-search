// File upload and dependency extraction remains the same
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
  console.log("Uploading files for dependency extraction...");
  fetch('/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    console.log("Server response for dependencies:", data);
    if (data.libraries && data.libraries.length > 0) {
      displayLibraries(data.libraries);
    } else {
      alert("No dependencies found.");
    }
  })
  .catch(error => {
    console.error('Error during file upload:', error);
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
    div.className = "checkbox-item";
    div.appendChild(checkbox);
    div.appendChild(label);
    listDiv.appendChild(div);
  });
  section.style.display = 'block';
}

// Now, documentation fetching is handled by the Flask endpoint /fetch_docs
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
  console.log("Fetching documentation for libraries:", selectedLibraries);
  fetchDocumentation(selectedLibraries, serpapiKey, geminiKey, outputOption);
});

async function fetchDocumentation(libraries, serpapiKey, geminiKey, outputOption) {
  try {
    const payload = {
      libraries: libraries,
      serpapiKey: serpapiKey,
      geminiKey: geminiKey
    };
    console.log("Sending payload to /fetch_docs:", payload);
    const response = await fetch('/fetch_docs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    const results = await response.json();
    console.log("Received documentation results:", results);
    displayResults(results, outputOption);
  } catch (error) {
    console.error("Error fetching documentation:", error);
    alert("Error fetching documentation.");
  }
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
    const blob = new Blob([consolidatedOutput], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = "documentation.txt";
    link.textContent = "Download Consolidated Documentation";
    downloadLinksDiv.appendChild(link);
  } else {
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
