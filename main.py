import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
import PyPDF2
from datetime import datetime

load_dotenv() # env file
api_key = os.getenv("AZURE_AI_API_KEY")
VALID_USERNAME = os.getenv("VALID_USERNAME")
VALID_PASSWORD = os.getenv("VALID_PASSWORD")

client = OpenAI( 
    base_url="https://models.inference.ai.azure.com",
    api_key=api_key
) # connection with AI

SAVE_DIR = "uploaded_pdfs" #where to put .pdf`s`
LOG_FILE = "chat_log.txt" # chatlog
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def log_to_file(role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {role.upper()}: {content}\n")
        f.write("-" * 50 + "\n")

def read_chat_history():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "No previous chat history available."

def check_login(): #login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.title("Be friends?")
        
        username = st.text_input("Username") 
        password = st.text_input("Password", type="password")
        
        if st.button("Login"): #hidded
            if username == VALID_USERNAME and password == VALID_PASSWORD:
                st.session_state.logged_in = True
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
        return False
    return True

def main_chat():
    st.title("BEST Friend")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": "AI"}]
    if "pdf_contents" not in st.session_state:
        st.session_state.pdf_contents = {}

    uploaded_file = st.file_uploader("Upload a PDF", type="pdf")
    if uploaded_file is not None:
        file_path = os.path.join(SAVE_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            pdf_text = ""
            for page in pdf_reader.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    pdf_text += extracted_text + "\n"
            if not pdf_text:
                pdf_text = "No text could be extracted from the PDF."
            
            st.session_state.pdf_contents[uploaded_file.name] = pdf_text
            st.write(f"PDF '{uploaded_file.name}' uploaded successfully.")
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")

    for message in st.session_state.messages[1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Type your message here..."):
       if prompt.strip().upper() == "STOPP":
        st.warning("Program stopping...")
        sys.exit(0)  # Fully terminates the program

        st.session_state.messages.append({"role": "user", "content": prompt})
        log_to_file("user", prompt)
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        try:
            with st.spinner("Thinking..."):
                chat_history = read_chat_history()
                
                if st.session_state.pdf_contents:
                    combined_pdf_content = "\n\n".join(
                        f"Content from {filename}:\n{content}"
                        for filename, content in st.session_state.pdf_contents.items()
                    )
                else:
                    combined_pdf_content = "No PDFs uploaded yet."
                
                system_prompt = (
                    "You are an AI assistant that provides accurate, context-aware responses based on:\n"
                    "1. **Chat History** – Past interactions from 'chat_log.txt' to ensure continuity.\n"
                    "2. **Uploaded PDFs** – Extracted text to answer fact-based questions, summarize, or compare information.\n\n"
                    
                    "**Guidelines:**\n"
                    "- **Accuracy:** Use only the provided chat history and PDFs. No guessing.\n"
                    "- **Relevance:** Answer exactly what’s asked, focusing on summaries, comparisons, or specific sections.\n"
                    "- **Attribution:**\n"
                    "  - PDFs: Cite location (e.g., 'In [PDF_Name], page 3 states…').\n"
                    "  - Chat History: Reference past messages when relevant.\n"
                    "- **Handling Unclear Requests:** Ask for clarification if needed.\n\n"
                    
                    "**Context Available:**\n"
                    "- **Recent Chat History (~4000 chars):**\n{chat_history[-4000:]}\n"
                    "- **Extracted PDF Content (~8000 chars):**\n{combined_pdf_content[-8000:]}\n\n"
                    
                    "**Response Rules:**\n"
                    "- Do not add information beyond what’s given. If something is missing, say so.\n"
                    "- For complex tasks, organize responses with headings or bullet points.\n"
                    "- Flag any contradictions in the provided context and ask for confirmation."
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

    if st.button("Clear Chat"):
        st.session_state.messages = [{"role": "system", "content": "AI"}]
        st.write("Chat cleared in memory, but logs and PDFs are preserved.")
        st.rerun()

    if st.button("Show Full Chat Log"):
        full_log = read_chat_history()
        st.text_area("Full Chat History", full_log, height=300)

if __name__ == "__main__":
    if check_login():
        main_chat()