import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys  # NEW: Added for program exit

# Load environment variables
load_dotenv()
api_key = os.getenv("AZURE_AI_API_KEY")

# Initialize OpenAI client
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=api_key
)

# Streamlit interface
st.title("Chat Assistant - Powered by GPT-4o")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are Grok 3, a helpful AI assistant built by xAI."}
    ]

# Display chat history
for message in st.session_state.messages[1:]:  # Skip system message
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Type your message here..."):
    # NEW: Check for stop command
    if prompt.strip().upper() == "STOP_PROGRAM":
        st.warning("Program stopping...")
        st.stop()  # Stops the Streamlit execution
        sys.exit(0)  # Ensures complete program termination
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get and display AI response
    try:
        with st.spinner("Thinking..."):
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
    st.session_state.messages = [
        {"role": "system", "content": "You are Grok 3, a helpful AI assistant built by xAI."}
    ]
    st.rerun()