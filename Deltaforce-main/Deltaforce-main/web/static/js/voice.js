// Voice functionality for CCTNS Copilot Engine
let recognition;
let isListening = false;

function initializeVoice() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onstart = function() {
            isListening = true;
            updateVoiceButton();
            document.getElementById('voiceStatus').textContent = '🎤 Listening... Speak now!';
        };
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById('queryText').value = transcript;
            document.getElementById('voiceStatus').textContent = `Heard: "${transcript}"`;
            
            // Auto-process the query
            setTimeout(() => {
                processTextQuery();
            }, 1000);
        };
        
        recognition.onend = function() {
            isListening = false;
            updateVoiceButton();
            if (document.getElementById('voiceStatus').textContent.includes('Listening')) {
                document.getElementById('voiceStatus').textContent = '';
            }
        };
        
        recognition.onerror = function(event) {
            isListening = false;
            updateVoiceButton();
            document.getElementById('voiceStatus').textContent = `❌ Error: ${event.error}`;
        };
    } else {
        document.getElementById('voiceBtn').disabled = true;
        document.getElementById('voiceStatus').textContent = '❌ Voice recognition not supported';
    }
}

function toggleVoice() {
    if (!recognition) {
        alert('Voice recognition not available');
        return;
    }
    
    if (isListening) {
        recognition.stop();
    } else {
        const language = document.getElementById('languageSelect').value;
        recognition.lang = getLanguageCode(language);
        recognition.start();
    }
}

function getLanguageCode(lang) {
    const codes = {
        'te': 'te-IN',  // Telugu
        'en': 'en-IN',  // Indian English
        'hi': 'hi-IN'   // Hindi
    };
    return codes[lang] || 'en-IN';
}

function updateVoiceButton() {
    const btn = document.getElementById('voiceBtn');
    const icon = document.getElementById('voiceIcon');
    const text = document.getElementById('voiceText');
    
    if (isListening) {
        btn.classList.add('listening');
        icon.textContent = '🔴';
        text.textContent = 'Stop Listening';
    } else {
        btn.classList.remove('listening');
        icon.textContent = '🎤';
        text.textContent = 'Start Voice Query';
    }
}

// Initialize voice on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeVoice();
});