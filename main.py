import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
import PyPDF2
from datetime import datetime

# Load environment variables
load_dotenv()
api_key = os.getenv("AZURE_AI_API_KEY")

# Initialize OpenAI client
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=api_key
)

# Directory to save PDFs and log file
SAVE_DIR = "uploaded_pdfs"
LOG_FILE = "chat_log.txt"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Function to log messages to a .txt file
def log_to_file(role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {role.upper()}: {content}\n")
        f.write("-" * 50 + "\n")

# Function to read chat history from the log file
def read_chat_history():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "No previous chat history available."

# Streamlit interface
st.title("BEST AND ONLY FRIEND")

# Initialize chat history and PDF content dictionary in session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "AI"}]
if "pdf_contents" not in st.session_state:
    st.session_state.pdf_contents = {}

# PDF upload feature
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")
if uploaded_file is not None:
    # Save the PDF to disk
    file_path = os.path.join(SAVE_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Read PDF content
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        pdf_text = ""
        for page in pdf_reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                pdf_text += extracted_text + "\n"
        if not pdf_text:
            pdf_text = "No text could be extracted from the PDF."
        
        # Store PDF content in session state with filename as key
        st.session_state.pdf_contents[uploaded_file.name] = pdf_text
        st.write(f"PDF '{uploaded_file.name}' uploaded successfully.")
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")

# Display chat history (only in-memory messages)
for message in st.session_state.messages[1:]:  # Skip system message
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Type your message here..."):
    if prompt.strip().upper() == "STOPP":
        st.warning("Program stopping...")
        st.stop()
        sys.exit(0)

    # Add user message to history and log it
    st.session_state.messages.append({"role": "user", "content": prompt})
    log_to_file("user", prompt)
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get and display AI response
    try:
        with st.spinner("Thinking..."):
            # Read previous chat history from the log file
            chat_history = read_chat_history()
            
            # Combine PDF contents for context
            if st.session_state.pdf_contents:
                combined_pdf_content = "\n\n".join(
                    f"Content from {filename}:\n{content}"
                    for filename, content in st.session_state.pdf_contents.items()
                )
            else:
                combined_pdf_content = "No PDFs uploaded yet."
            
            # Enhanced system prompt for RAG
            system_prompt = (
                "You are an AI designed to assist users by leveraging past conversations and uploaded PDF content. "
                "Use the chat history from 'chat_log.txt' and the content of uploaded PDFs to provide informed, context-aware responses. "
                "If the user requests summaries, comparisons, or insights, analyze the available data accordingly. "
                "Always prioritize accuracy and relevance based on the provided context.\n\n"
                f"Previous Chat History (from chat_log.txt):\n{chat_history[-4000:]}\n\n"  # Use last 4000 chars for recency
                f"PDF Content (from uploaded_pdfs):\n{combined_pdf_content[-6000:]}"  # Use last 6000 chars
            )
            st.session_state.messages[0] = {"role": "system", "content": system_prompt}
            
            # Call the OpenAI API
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state.messages,
                temperature=0.7,
                max_tokens=1500
            )
        
        response = completion.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": response})
        log_to_file("assistant", response)
        
        with st.chat_message("assistant"):
            st.markdown(response)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Clear chat button (resets in-memory messages but keeps logs and PDFs)
if st.button("Clear Chat"):
    st.session_state.messages = [{"role": "system", "content": "AI"}]  # Reset in-memory messages only
    st.write("Chat cleared in memory, but logs and PDFs are preserved.")
    st.rerun()

# Optional: Display full chat log on demand
if st.button("Show Full Chat Log"):
    full_log = read_chat_history()
    st.text_area("Full Chat History", full_log, height=300)