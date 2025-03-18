import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
import PyPDF2  # NEW: For reading PDF files

# Load environment variables
load_dotenv()
api_key = os.getenv("AZURE_AI_API_KEY")

# Initialize OpenAI client
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=api_key
)

# Streamlit interface
st.title("BEST AND ONLY FRIEND")

# Initialize chat history and PDF content in session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "AI"}]
if "pdf_content" not in st.session_state:
    st.session_state.pdf_content = ""

# PDF upload feature
uploaded_file = st.file_uploader("Upload a PDF to enhance responses", type="pdf")
if uploaded_file is not None:
    # Read PDF content
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    pdf_text = ""
    for page in pdf_reader.pages:
        pdf_text += page.extract_text() or ""
    st.session_state.pdf_content = pdf_text
    st.success("PDF uploaded successfully! I'll use its content to inform my responses.")

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
        with st.spinner("Thinking..."):
            # Include PDF content in the system message if available
            if st.session_state.pdf_content:
                st.session_state.messages[0] = {
                    "role": "system",
                    "content": f"AI with PDF context: {st.session_state.pdf_content[:2000]}"  # Limit to avoid token overflow
                }
            
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state.messages,
                temperature=0.7,
                max_tokens=1000
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
    st.session_state.pdf_content = ""  # Reset PDF content too
    st.rerun()