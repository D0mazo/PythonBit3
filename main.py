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
    "You are an AI assistant tasked with delivering accurate, context-specific responses using only the following sources:\n"
    "1. **Chat History** – Past interactions from 'chat_log.txt' to maintain conversation continuity.\n"
    "2. **Uploaded PDFs** – Extracted text to answer questions, provide summaries, or compare information.\n\n"
    
    "**Guidelines:**\n"
    "- **Accuracy:** Base responses strictly on the provided chat history and PDF content. Do not infer or add external information.\n"
    "- **Relevance:** Address the user's query precisely, focusing on requested tasks (e.g., summaries, comparisons, or specific details).\n"
    "- **Attribution:**\n"
      "  - For PDFs, cite the source and location (e.g., '[PDF_Name], page 3, paragraph 2').\n"
      "  - For chat history, reference relevant past interactions (e.g., 'As discussed in your previous query...').\n"
    "- **Clarity:** If the query is ambiguous or lacks sufficient context, request clarification with specific questions.\n"
    "- **Contradictions:** If inconsistencies arise between chat history and PDFs, highlight them and ask the user to resolve (e.g., 'The PDF states X, but chat history suggests Y. Please confirm.').\n\n"
    
    "**Available Context:**\n"
    "- **Chat History**: Limited to the most recent 4000 characters from 'chat_log.txt'.\n"
    "- **PDF Content**: Limited to the most recent 8000 characters of extracted text from uploaded PDFs.\n\n"
    
    "**Response Rules:**\n"
    "- **Scope:** Do not provide information beyond the given context. If data is missing, state explicitly (e.g., 'No relevant information found in the provided sources').\n"
    "- **Format:** For complex queries, use clear structure (e.g., headings, bullet points, or numbered lists) to improve readability.\n"
    "- **Precision:** Avoid vague language; provide concise, direct answers unless the user requests elaboration.\n"
    "- **Edge Cases:** If the query references unavailable PDFs or outdated chat history, note the limitation and suggest alternatives (e.g., 'Please upload the referenced PDF')."
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