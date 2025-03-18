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
    return ""

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
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    pdf_text = ""
    for page in pdf_reader.pages:
        pdf_text += page.extract_text() or ""
    
    # Store PDF content in session state with filename as key
    st.session_state.pdf_contents[uploaded_file.name] = pdf_text
    st.write(f"PDF '{uploaded_file.name}' uploaded.")

# Display chat history
for message in st.session_state.messages[1:]:
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
        with st.spinner("Analyzing PDFs and generating response..."):
            # Read previous chat history from the log file
            chat_history = read_chat_history()
            
            # Combine PDF contents and chat history for context
            if st.session_state.pdf_contents:
                combined_pdf_content = "\n\n".join(
                    f"Content from {filename}:\n{content}"
                    for filename, content in st.session_state.pdf_contents.items()
                )
            else:
                combined_pdf_content = "No PDFs uploaded yet."
            
            system_prompt = (
                "You are an AI designed to analyze and compare content from multiple PDFs and past conversations. "
                "Use the following content from all uploaded PDFs and previous chat history to inform your response. "
                "If the user asks for comparisons, summaries, or specific insights, analyze the PDFs and chat history accordingly.\n\n"
                f"Previous Chat History:\n{chat_history[:2000]}\n\n"  # Limit chat history to 2000 chars
                f"PDF Content:\n{combined_pdf_content[:4000]}"  # Limit PDF content to 4000 chars
            )
            st.session_state.messages[0] = {"role": "system", "content": system_prompt}
            
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

# Clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = [{"role": "system", "content": "AI"}]
    st.session_state.pdf_contents = {}
    st.rerun()