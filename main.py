import streamlit as st  # Import Streamlit library for building the web-based UI
from openai import OpenAI  # Import OpenAI library to interact with the GPT-4o model
from dotenv import load_dotenv  # Import dotenv to load environment variables from a .env file
import os  # Import os for file and directory operations
import sys  # Import sys for system-level operations like exiting the program
import PyPDF2  # Import PyPDF2 to read and extract text from PDF files
from datetime import datetime  # Import datetime to timestamp chat logs

# Load environment variables from a .env file (e.g., API keys)
load_dotenv()
api_key = os.getenv("AZURE_AI_API_KEY")  # Retrieve the Azure AI API key from environment variables

# Initialize the OpenAI client with Azure-specific settings
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",  # Set the base URL for Azure AI inference
    api_key=api_key  # Pass the API key for authentication
)

# Define constants for file storage
SAVE_DIR = "uploaded_pdfs"  # Directory name where uploaded PDFs will be saved
LOG_FILE = "chat_log.txt"  # File name for storing chat history
if not os.path.exists(SAVE_DIR):  # Check if the PDF save directory exists
    os.makedirs(SAVE_DIR)  # Create the directory if it doesn't exist

# Function to log messages to a text file
def log_to_file(role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get current date and time as a formatted string
    with open(LOG_FILE, "a", encoding="utf-8") as f:  # Open the log file in append mode with UTF-8 encoding
        f.write(f"[{timestamp}] {role.upper()}: {content}\n")  # Write the role (e.g., USER/ASSISTANT) and message with timestamp
        f.write("-" * 50 + "\n")  # Add a separator line for readability

# Function to read the entire chat history from the log file
def read_chat_history():
    if os.path.exists(LOG_FILE):  # Check if the log file exists
        with open(LOG_FILE, "r", encoding="utf-8") as f:  # Open the log file in read mode with UTF-8 encoding
            return f.read()  # Return the full contents of the file as a string
    return "No previous chat history available."  # Return a default message if the file doesn't exist

# Set up the Streamlit interface
st.title("BEST AND ONLY FRIEND")  # Display a title at the top of the web page

# Initialize session state variables to store chat history and PDF contents
if "messages" not in st.session_state:  # Check if the messages key exists in session state
    st.session_state.messages = [{"role": "system", "content": "AI"}]  # Initialize with a system message
if "pdf_contents" not in st.session_state:  # Check if the pdf_contents key exists in session state
    st.session_state.pdf_contents = {}  # Initialize as an empty dictionary to store PDF content

# Add a PDF upload feature to the UI
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")  # Create a file uploader widget for PDFs
if uploaded_file is not None:  # Check if a file has been uploaded
    # Save the uploaded PDF to disk
    file_path = os.path.join(SAVE_DIR, uploaded_file.name)  # Construct the full file path for saving
    with open(file_path, "wb") as f:  # Open the file in binary write mode
        f.write(uploaded_file.getbuffer())  # Write the uploaded file's binary data to disk
    
    # Extract text from the PDF
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)  # Create a PDF reader object for the uploaded file
        pdf_text = ""  # Initialize an empty string to store extracted text
        for page in pdf_reader.pages:  # Loop through each page in the PDF
            extracted_text = page.extract_text()  # Attempt to extract text from the page
            if extracted_text:  # Check if text was extracted successfully
                pdf_text += extracted_text + "\n"  # Append the text with a newline
        if not pdf_text:  # Check if no text was extracted from the PDF
            pdf_text = "No text could be extracted from the PDF."  # Set a fallback message
        
        # Store the extracted text in session state
        st.session_state.pdf_contents[uploaded_file.name] = pdf_text  # Use the filename as the key
        st.write(f"PDF '{uploaded_file.name}' uploaded successfully.")  # Display a success message
    except Exception as e:  # Catch any errors during PDF processing
        st.error(f"Error processing PDF: {str(e)}")  # Display an error message

# Display the current chat history (in-memory messages only)
for message in st.session_state.messages[1:]:  # Loop through messages, skipping the system message
    with st.chat_message(message["role"]):  # Create a chat bubble for the message based on role (user/assistant)
        st.markdown(message["content"])  # Render the message content as markdown

# Handle user input from the chat box
if prompt := st.chat_input("Type your message here..."):  # Capture user input from the chat input field
    if prompt.strip().upper() == "STOPP":  # Check if the user typed "STOPP" (case-insensitive)
        st.warning("Program stopping...")  # Display a warning message
        st.stop()  # Stop the Streamlit app
        sys.exit(0)  # Exit the Python process

    # Add the user's message to the chat history and log it
    st.session_state.messages.append({"role": "user", "content": prompt})  # Add the user message to session state
    log_to_file("user", prompt)  # Log the user message to the chat log file
    
    # Display the user's message in the chat UI
    with st.chat_message("user"):  # Create a chat bubble for the user
        st.markdown(prompt)  # Render the user's message as markdown
    
    # Generate and display the AI's response
    try:
        with st.spinner("Thinking..."):  # Show a loading spinner while processing
            # Retrieve the full chat history from the log file
            chat_history = read_chat_history()  # Call the function to read chat_log.txt
            
            # Combine all uploaded PDF contents for context
            if st.session_state.pdf_contents:  # Check if there are any PDFs in session state
                combined_pdf_content = "\n\n".join(  # Join PDF contents with double newlines
                    f"Content from {filename}:\n{content}"  # Format each PDF's content with its filename
                    for filename, content in st.session_state.pdf_contents.items()  # Iterate over PDF dictionary
                )
            else:
                combined_pdf_content = "No PDFs uploaded yet."  # Default message if no PDFs exist
            
            # Define the system prompt for RAG (Retrieval-Augmented Generation)
            system_prompt = (
                "You are an AI designed to assist users by leveraging past conversations and uploaded PDF content. "  # AI role description
                "Use the chat history from 'chat_log.txt' and the content of uploaded PDFs to provide informed, context-aware responses. "  # Instruction for context usage
                "If the user requests summaries, comparisons, or insights, analyze the available data accordingly. "  # Guidance for specific tasks
                "Always prioritize accuracy and relevance based on the provided context.\n\n"  # Emphasis on quality
                f"Previous Chat History (from chat_log.txt):\n{chat_history[-4000:]}\n\n"  # Include last 4000 chars of chat history
                f"PDF Content (from uploaded_pdfs):\n{combined_pdf_content[-6000:]}"  # Include last 6000 chars of PDF content
            )
            st.session_state.messages[0] = {"role": "system", "content": system_prompt}  # Update the system message with the prompt
            
            # Call the OpenAI API to generate a response
            completion = client.chat.completions.create(
                model="gpt-4o",  # Specify the GPT-4o model
                messages=st.session_state.messages,  # Pass the full message history (system + user messages)
                temperature=0.7,  # Set creativity level (0-1, 0.7 is moderately creative)
                max_tokens=1500  # Limit the response length to 1500 tokens
            )
        
        response = completion.choices[0].message.content  # Extract the AI's response from the API result
        st.session_state.messages.append({"role": "assistant", "content": response})  # Add the response to session state
        log_to_file("assistant", response)  # Log the AI's response to the chat log file
        
        with st.chat_message("assistant"):  # Create a chat bubble for the assistant
            st.markdown(response)  # Render the AI's response as markdown

    except Exception as e:  # Catch any errors during API call or processing
        st.error(f"An error occurred: {str(e)}")  # Display an error message

# Add a button to clear the in-memory chat history
if st.button("Clear Chat"):  # Check if the "Clear Chat" button is clicked
    st.session_state.messages = [{"role": "system", "content": "AI"}]  # Reset in-memory messages to just the system message
    st.write("Chat cleared in memory, but logs and PDFs are preserved.")  # Inform the user that logs/PDFs remain
    st.rerun()  # Rerun the app to refresh the UI

# Add a button to display the full chat log
if st.button("Show Full Chat Log"):  # Check if the "Show Full Chat Log" button is clicked
    full_log = read_chat_history()  # Retrieve the entire chat history from the log file
    st.text_area("Full Chat History", full_log, height=300)  # Display the log in a scrollable text area