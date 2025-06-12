#!/usr/bin/env python3
#!/usr/bin/env python3
import streamlit as st
from ask_osiris import answer_question

# --- Google Cloud Auth Setup ---
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from vertexai import aiplatform  # If you're using Vertex AI (optional)
import os

# Load credentials from Streamlit secrets
creds_info = st.secrets["google_credentials"]
creds = service_account.Credentials.from_service_account_info(creds_info)
creds.refresh(Request())

# Optional: Initialize Vertex AI client (if used inside `answer_question`)
aiplatform.init(
    credentials=creds,
    project=creds_info["project_id"],
    location="us-central1"  # Or whatever region you're using
)

# --- Page Config ---
st.set_page_config(
    page_title="Ask Osiris",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# --- Initialize session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False

# --- Refined Modern UI CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

/* Reset and Base Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #0a0c1b;
    color: #f8fafc;
    line-height: 1.5;
}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0a0c1b 0%, #1a1f35 100%);
    background-attachment: fixed;
}

[data-testid="stHeader"] {
    display: none;
}

.main .block-container {
    padding: 0;
    max-width: none;
}

/* Fix for empty containers */
.element-container:empty {
    display: none;
}

/* Subtle Background Pattern */
body::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: 
        radial-gradient(circle at 15% 85%, rgba(76, 0, 255, 0.05) 0%, transparent 25%),
        radial-gradient(circle at 85% 15%, rgba(0, 183, 255, 0.05) 0%, transparent 25%);
    pointer-events: none;
    z-index: -1;
}

/* Main Layout */
.app-container {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    max-width: 1000px;
    margin: 0 auto;
    background: rgba(18, 21, 40, 0.7);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-left: 1px solid rgba(255, 255, 255, 0.08);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}

/* Header */
.app-header {
    padding: 1.75rem 2rem;
    background: rgba(18, 21, 40, 0.8);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    position: sticky;
    top: 0;
    z-index: 100;
}

.app-header::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, 
        rgba(76, 0, 255, 0), 
        rgba(76, 0, 255, 0.3), 
        rgba(0, 183, 255, 0.3), 
        rgba(76, 0, 255, 0));
}

.app-title {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
}

.app-title-text {
    font-size: 1.75rem;
    font-weight: 700;
    background: linear-gradient(135deg, #f8fafc 0%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
}

.app-title-icon {
    font-size: 1.75rem;
    background: linear-gradient(135deg, #4c00ff 0%, #00b7ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.app-subtitle {
    font-size: 0.95rem;
    color: #94a3b8;
    font-weight: 400;
    max-width: 600px;
}

/* Messages Area */
.messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem 0;
    scroll-behavior: smooth;
}

.messages-container::-webkit-scrollbar {
    width: 6px;
}

.messages-container::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.15);
}

/* Message Styles */
.message-row {
    padding: 0.5rem 1.5rem;
    margin-bottom: 0.75rem;
    display: flex;
    flex-direction: column;
}

.message-row.user {
    align-items: flex-end;
}

.message-row.assistant {
    align-items: flex-start;
}

.message-bubble {
    padding: 1rem 1.25rem;
    border-radius: 1rem;
    max-width: 80%;
    position: relative;
    transition: transform 0.2s ease;
}

.message-bubble:hover {
    transform: translateY(-1px);
}

.message-bubble.user {
    background: linear-gradient(135deg, rgba(76, 0, 255, 0.15) 0%, rgba(0, 183, 255, 0.15) 100%);
    border: 1px solid rgba(76, 0, 255, 0.2);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 4px 15px rgba(76, 0, 255, 0.1);
}

.message-bubble.assistant {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.message-label {
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.message-label.user {
    color: #94a3b8;
}

.message-label.assistant {
    color: #94a3b8;
}

.message-content {
    font-size: 0.95rem;
    line-height: 1.6;
    color: #f8fafc;
}

/* Loading State */
.loading-container {
    padding: 0.5rem 1.5rem;
    margin-bottom: 0.75rem;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
}

.loading-bubble {
    padding: 1rem 1.25rem;
    border-radius: 1rem;
    max-width: 80%;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    position: relative;
    overflow: hidden;
}

.loading-bubble::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 50%;
    height: 100%;
    background: linear-gradient(90deg, 
        transparent, 
        rgba(255, 255, 255, 0.05), 
        transparent);
    animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
    0% { left: -100%; }
    100% { left: 100%; }
}

.loading-content {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: #94a3b8;
}

.loading-dots {
    display: inline-flex;
    gap: 4px;
}

.loading-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #94a3b8;
    animation: pulse 1.4s ease-in-out infinite;
}

.loading-dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes pulse {
    0%, 80%, 100% { opacity: 0.4; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1); }
}

/* Empty State */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 4rem 2rem;
    height: 100%;
    min-height: 300px;
}

.empty-state-icon {
    font-size: 3rem;
    margin-bottom: 1.5rem;
    background: linear-gradient(135deg, #4c00ff 0%, #00b7ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.empty-state-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: #f8fafc;
    margin-bottom: 0.75rem;
}

.empty-state-subtitle {
    font-size: 0.95rem;
    color: #94a3b8;
    max-width: 450px;
    line-height: 1.6;
}

/* Input Area */
.input-area {
    padding: 1.5rem 2rem;
    background: rgba(18, 21, 40, 0.8);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    position: sticky;
    bottom: 0;
    z-index: 100;
}

.input-area::before {
    content: '';
    position: absolute;
    top: -1px;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, 
        rgba(76, 0, 255, 0), 
        rgba(76, 0, 255, 0.3), 
        rgba(0, 183, 255, 0.3), 
        rgba(76, 0, 255, 0));
}

.stChatInputContainer {
    background: rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    margin: 0 !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1) !important;
    transition: all 0.2s ease !important;
}

.stChatInputContainer:focus-within {
    border-color: rgba(76, 0, 255, 0.3) !important;
    box-shadow: 0 4px 20px rgba(76, 0, 255, 0.1) !important;
}

.stChatInputContainer textarea {
    background: transparent !important;
    color: #f8fafc !important;
    border: none !important;
    font-size: 0.95rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    padding: 0.875rem 1rem !important;
}

.stChatInputContainer textarea::placeholder {
    color: #64748b !important;
}

/* Hide Streamlit elements */
footer, #MainMenu, header, .stDeployButton, [data-testid="stDecoration"] {
    display: none !important;
}

/* Responsive Design */
@media (max-width: 768px) {
    .app-container {
        border-left: none;
        border-right: none;
    }
    
    .app-header, .input-area {
        padding: 1.25rem 1rem;
    }
    
    .message-row {
        padding: 0.5rem 1rem;
    }
    
    .message-bubble {
        max-width: 85%;
    }
    
    .app-title-text {
        font-size: 1.5rem;
    }
    
    .app-subtitle {
        font-size: 0.875rem;
    }
}
</style>
""", unsafe_allow_html=True)

# --- Build the UI structure ---
st.markdown('<div class="app-container">', unsafe_allow_html=True)

# Header
st.markdown("""
<div class="app-header">
    <div class="app-title">
        <span class="app-title-icon">🤖</span>
        <span class="app-title-text">Ask Osiris</span>
    </div>
    <div class="app-subtitle">
        AI assistant for product analytics transcripts with speaker context and timestamps
    </div>
</div>
""", unsafe_allow_html=True)

# Messages container
st.markdown('<div class="messages-container" id="messages-container">', unsafe_allow_html=True)

# Show empty state or messages
if not st.session_state.messages and not st.session_state.is_loading:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">💬</div>
        <div class="empty-state-title">Start a conversation with Osiris</div>
        <div class="empty-state-subtitle">
            Ask questions about your product analytics transcripts to get insights with speaker attribution and timestamps.
        </div>
    </div>
    """, unsafe_allow_html=True)

# Display existing messages
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    row_class = "user" if role == "user" else "assistant"
    bubble_class = "user" if role == "user" else "assistant"
    label = "You" if role == "user" else "Osiris"
    
    st.markdown(f"""
    <div class="message-row {row_class}">
        <div class="message-label {row_class}">{label}</div>
        <div class="message-bubble {bubble_class}">
            <div class="message-content">{content}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Show loading state if needed
if st.session_state.is_loading:
    st.markdown("""
    <div class="loading-container">
        <div class="message-label assistant">Osiris</div>
        <div class="loading-bubble">
            <div class="loading-content">
                <span>Analyzing your question</span>
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input area
st.markdown('<div class="input-area">', unsafe_allow_html=True)
prompt = st.chat_input("Ask about your analytics data...")
st.markdown('</div>', unsafe_allow_html=True)

# Close main container
st.markdown('</div>', unsafe_allow_html=True)

# Handle user input
if prompt and not st.session_state.is_loading:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.is_loading = True
    st.rerun()

# Handle AI response
if st.session_state.is_loading and st.session_state.messages:
    try:
        # Pass the full conversation (excluding loading state)
        conversation = [
            m for m in st.session_state.messages if m["role"] in ("user", "assistant")
        ]
        answer = answer_question(conversation)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.session_state.is_loading = False
        st.rerun()
        
    except Exception as e:
        # Handle errors gracefully
        error_message = "I'm having trouble processing your request. Please try again."
        st.session_state.messages.append({"role": "assistant", "content": error_message})
        st.session_state.is_loading = False
        st.rerun()

# Auto-scroll to bottom
if st.session_state.messages or st.session_state.is_loading:
    st.markdown("""
    <script>
    function scrollToBottom() {
        var container = document.getElementById('messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }
    
    scrollToBottom();
    setTimeout(scrollToBottom, 100);
    </script>
    """, unsafe_allow_html=True)