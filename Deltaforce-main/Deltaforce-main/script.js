document.addEventListener('DOMContentLoaded', () => {
    const chatDisplay = document.getElementById('chat-display');
    const textInput = document.getElementById('text-input');
    const micButton = document.getElementById('mic-button');
    const sendButton = document.getElementById('send-button');
    const sqlQueryDisplay = document.getElementById('sql-query-display');
    const dataTableDisplay = document.getElementById('data-table-display');

    // --- Speech Recognition Setup ---
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = (event) => {
            const speechResult = event.results[0][0].transcript;
            appendMessage('user', `You (voice): ${speechResult}`);
            textInput.value = speechResult; // Populate text input for potential editing
            // Automatically send to backend after speech recognition
            processUserInput(speechResult);
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            appendMessage('system', `Speech recognition error: ${event.error}`);
        };

        recognition.onspeechend = () => {
            recognition.stop();
            micButton.textContent = '🎤';
            micButton.disabled = false;
        };

        micButton.addEventListener('click', () => {
            if (recognition && !micButton.disabled) {
                try {
                    recognition.start();
                    micButton.textContent = '...'; // Indicate listening
                    micButton.disabled = true;
                    appendMessage('system', 'Listening...');
                } catch (e) {
                    console.error("Error starting recognition: ", e);
                    appendMessage('system', 'Could not start voice recognition. Is microphone access granted?');
                    micButton.textContent = '🎤';
                    micButton.disabled = false;
                }
            } else {
                appendMessage('system', 'Speech recognition not available or already active.');
            }
        });

    } else {
        micButton.disabled = true;
        micButton.textContent = '🚫';
        appendMessage('system', 'Speech recognition not supported by your browser.');
        console.warn('Speech Recognition API not supported.');
    }

    // --- Text Input Handling ---
    sendButton.addEventListener('click', () => {
        const message = textInput.value.trim();
        if (message) {
            appendMessage('user', `You: ${message}`);
            processUserInput(message);
            textInput.value = '';
        }
    });

    textInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendButton.click();
        }
    });

    // --- Helper Functions ---
    function appendMessage(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        messageElement.textContent = message;
        chatDisplay.appendChild(messageElement);
        chatDisplay.scrollTop = chatDisplay.scrollHeight; // Scroll to bottom
    }

    async function processUserInput(text) {
        // Placeholder for backend communication
        appendMessage('system', `Processing: "${text}"...`);
        sqlQueryDisplay.textContent = "-- Generating SQL... --";
        dataTableDisplay.innerHTML = "-- Fetching data... --";

        // Simulate backend processing (will be replaced with actual fetch call)
        try {
            const response = await fetch('/process_query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query_text: text }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({detail: "Unknown error"}));
                throw new Error(`Backend error: ${response.status} ${response.statusText}. ${errorData.detail || ''}`);
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({detail: "Unknown error"})); // Try to parse error
                // Display backend-returned error or a generic one
                const backendError = errorData.error || `Backend error: ${response.status} ${response.statusText}. ${errorData.detail || ''}`;
                appendMessage('system', `Error: ${backendError}`);
                sqlQueryDisplay.textContent = errorData.sql_query || "-- Error generating SQL --"; // Display SQL if available even on error
                dataTableDisplay.innerHTML = errorData.error ? `<p class="error-message">${errorData.error}</p>` : "-- Error fetching data --";
                return; // Stop further processing
            }

            const data = await response.json();
            if(data.error) { // Handle errors reported in a 200 OK response's JSON payload
                appendMessage('system', `DB Error: ${data.error}`);
                sqlQueryDisplay.textContent = data.sql_query || "-- SQL query with error --";
                dataTableDisplay.innerHTML = `<p class="error-message">Database Error: ${data.error}</p>`;
            } else {
                displayResults(data.sql_query, data.result_table);
            }

        } catch (error) { // Catch network errors or issues with fetch itself
            console.error('Error processing user input:', error);
            appendMessage('system', `Error: ${error.message}`);
            sqlQueryDisplay.textContent = "-- Error generating SQL --";
            dataTableDisplay.innerHTML = "-- Error fetching data --";
        }
    }

    function displayResults(sqlQuery, tableData) {
        sqlQueryDisplay.textContent = sqlQuery || "-- No SQL query generated --";

        dataTableDisplay.innerHTML = ''; // Clear previous table or message

        if (tableData && tableData.length > 0) {
            // Check if the first item indicates a non-SELECT status message
            if (tableData.length === 1 && tableData[0].status && tableData[0].rows_affected !== undefined) {
                 dataTableDisplay.innerHTML = `Query executed successfully. Status: ${tableData[0].status}, Rows affected: ${tableData[0].rows_affected}.`;
                 return;
            }

            const table = document.createElement('table');
            const thead = document.createElement('thead');
            const tbody = document.createElement('tbody');
            const headerRow = document.createElement('tr');

            // Create headers from the keys of the first object
            Object.keys(tableData[0]).forEach(key => {
                const th = document.createElement('th');
                th.textContent = key;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);

            // Create rows
            tableData.forEach(rowData => {
                const tr = document.createElement('tr');
                Object.values(rowData).forEach(value => {
                    const td = document.createElement('td');
                    td.textContent = (value === null || value === undefined) ? "" : value; // Handle null/undefined
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            dataTableDisplay.appendChild(table);
        } else if (sqlQuery && (!tableData || tableData.length === 0) && !sqlQuery.startsWith("-- Placeholder:") && !sqlQueryDisplay.textContent.includes("error") && !sqlQueryDisplay.textContent.includes("Error")) {
            // If a valid SQL query was likely executed but returned no rows (e.g., SELECT with no matches)
            dataTableDisplay.innerHTML = "-- Query executed successfully. No data returned. --";
        } else if (sqlQuery.startsWith("-- Placeholder:")) {
            dataTableDisplay.innerHTML = "-- No data to display (NLP model could not generate a query). --";
        }
        else {
             // This case handles when sqlQuery might indicate an error already displayed by processUserInput or other scenarios
            if (!dataTableDisplay.innerHTML.includes("Error")) { // Avoid overwriting specific error messages
                dataTableDisplay.innerHTML = "-- No data to display --";
            }
        }
    }

    // Initial message
    appendMessage('system', 'Hello! How can I help you today? Type or use the microphone.');
});
