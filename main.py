import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
import PyPDF2

# Load environment variables
load_dotenv()
api_key = os.getenv("AZURE_AI_API_KEY")

# Initialize OpenAI client
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=api_key
)

# Directory to save PDFs (create if it doesn’t exist)
SAVE_DIR = "uploaded_pdfs"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# Streamlit interface
st.title("BEST AND ONLY FRIEND")

# Initialize chat history and PDF content dictionary in session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "AI"}]
if "pdf_contents" not in st.session_state:
    st.session_state.pdf_contents = {}  # Dictionary to store PDF contents with filenames as keys

# PDF upload feature
uploaded_file = st.file_uploader("Upload a PDF to enhance responses", type="pdf")
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
    st.success(f"PDF '{uploaded_file.name}' uploaded and saved to {file_path}! I'll analyze all uploaded PDFs for my responses.")

# Display chat history
for message in st.session_state.messages[1:]:  # Skip system message
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Type your message here..."):
    if prompt.strip().upper() == "STOPP":
        st.warning("Program stopping...")
        st.stop()
        sys.exit(0)

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get and display AI response
    try:
        with st.spinner("Analyzing PDFs and generating response..."):
            # Combine all PDF contents for context with analysis instructions
            if st.session_state.pdf_contents:
                combined_pdf_content = "\n\n".join(
                    f"Content from {filename}:\n{content}"
                    for filename, content in st.session_state.pdf_contents.items()
                )
                # Increase context limit and add analysis instruction
                system_prompt = (
                    "You are an AI designed to analyze and compare content from multiple PDFs. "
                    "Use the following content from all uploaded PDFs to inform your response. "
                    "If the user asks for comparisons, summaries, or specific insights, analyze the PDFs accordingly.\n\n"
                    f"{combined_pdf_content[:4000]}"  # Increased to 4000 characters, adjust as needed
                )
                st.session_state.messages[0] = {"role": "system", "content": system_prompt}
            else:
                st.session_state.messages[0] = {
                    "role": "system",
                    "content": "You are an AI assistant. No PDFs have been uploaded yet."
                }
            
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state.messages,
                temperature=0.7,
                max_tokens=1500  # Increased for more detailed responses
            )
        
        response = completion.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        with st.chat_message("assistant"):
            st.markdown(response)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = [{"role": "system", "content": "AI"}]
    st.session_state.pdf_contents = {}
    st.rerun()