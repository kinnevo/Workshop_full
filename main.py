import requests
import streamlit as st
from dotenv import load_dotenv
import os
import json
import pandas as pd
import time
from datetime import datetime
import sqlite3  # Add this import for SQLite database

# Load environment variables
load_dotenv()

# Database setup
def init_db():
    """Initialize the SQLite database with necessary tables."""
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            conversation_name TEXT,
            conversation_data TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Function to save conversation to database
def save_to_database(user_id, conversation_data, conversation_name=None):
    """
    Save a conversation to the SQLite database.
    
    Args:
        user_id: The ID of the user
        conversation_data: The conversation data in JSON format
        conversation_name: Optional name for the conversation
    
    Returns:
        The ID of the saved conversation
    """
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute(
        'INSERT INTO conversations (user_id, conversation_name, conversation_data) VALUES (?, ?, ?)',
        (user_id, conversation_name, json.dumps(conversation_data))
    )
    conversation_id = c.lastrowid
    conn.commit()
    conn.close()
    return conversation_id

# Function to retrieve conversations from database
def get_conversations(user_id=None):
    """
    Retrieve conversations from the database.
    
    Args:
        user_id: Optional filter by user ID
    
    Returns:
        List of conversation records
    """
    conn = sqlite3.connect('conversations.db')
    conn.row_factory = sqlite3.Row  # Enable row factory to get dict-like objects
    c = conn.cursor()
    
    if user_id:
        c.execute('SELECT * FROM conversations WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
    else:
        c.execute('SELECT * FROM conversations ORDER BY timestamp DESC')
    
    rows = c.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result

# Function to retrieve a specific conversation by ID
def get_conversation_by_id(conversation_id):
    """
    Retrieve a specific conversation from the database.
    
    Args:
        conversation_id: The ID of the conversation to retrieve
    
    Returns:
        The conversation data as a dict
    """
    conn = sqlite3.connect('conversations.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
    row = c.fetchone()
    result = dict(row) if row else None
    conn.close()
    return result

# Continue with your existing code...
# LangFlow connection settings
BASE_API_URL = "http://34.59.108.214:7860/"
FLOW_ID = "657a335f-2a96-413b-b14e-8d1b312ff304"
APPLICATION_TOKEN = os.environ.get("OPENAI_API_KEY")
ENDPOINT = "657a335f-2a96-413b-b14e-8d1b312ff304"  # The endpoint name of the flow

# Initialize session state for conversation memory and user tracking
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Initialize user tracking
if 'users' not in st.session_state:
    st.session_state.users = {
        "User_1": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False},
        "User_2": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False},
        "User_3": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False},
        "User_4": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False},
        "User_5": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False}
    }

# The rest of your existing functions...
def run_flow(message: str, agent_name: str = "User_1", history: list = None) -> dict:
    """
    Run the LangFlow with the given message and conversation history.
    
    Args:
        message: The current user message
        agent_name: The name of the user to use
        history: Optional list of previous conversation messages
    
    Returns:
        The response from LangFlow
    """
    api_url = f"{BASE_API_URL}/api/v1/run/{ENDPOINT}"
    
    # Update user status
    update_agent_status(agent_name, "Active")
    
    # Include conversation history if available
    if history and len(history) > 0:
        # Format history in the way LangFlow expects it
        formatted_history = json.dumps(history)
        
        payload = {
            "input_value": message,
            "output_type": "chat",
            "input_type": "chat",
            "conversation_history": formatted_history,
            "user": agent_name,  # Pass the user name to LangFlow
            "session_id": agent_name
        }
    else:
        payload = {
            "input_value": message,
            "output_type": "chat",
            "input_type": "chat",
            "user": agent_name,  # Pass the user name to LangFlow
            "session_id": agent_name
        }

    headers = {"Authorization": f"Bearer {APPLICATION_TOKEN}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response_data = response.json()
        
        # Check if exploration was completed based on response
        if "full_exploration_completed" in response_data or "exploration_status" in response_data:
            exploration_completed = response_data.get("full_exploration_completed", False)
            if exploration_completed:
                update_agent_exploration(agent_name, True)
            
        # Update user status to completed
        update_agent_status(agent_name, "Completed")
        
        # Increment exploration counter
        increment_agent_exploration(agent_name)
        
        return response_data
    except Exception as e:
        # Update user status to failed in case of error
        update_agent_status(agent_name, "Failed")
        raise e

def add_to_history(role: str, content: str, user: str = None):
    """Add a message to the conversation history."""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user
    }
    
    st.session_state.conversation_history.append(message)

def display_conversation():
    """Display the conversation history in the Streamlit UI."""
    # Create scrollable container
    scroll_container = st.container()
    
    # Wrap the messages in an expander to create scrollable area
    with scroll_container:
        st.markdown("""
            <style>
                .stMarkdown {
                    max-height: 400px;
                    overflow-y: auto;
                    border: 1px solid #ccc;
                    padding: 10px;
                    border-radius: 5px;
                }
            </style>
        """, unsafe_allow_html=True)
        
        chat_container = st.empty()
        chat_content = ""
        
        # Build message content
        for message in st.session_state.conversation_history:
            agent_info = f" (via {message.get('user', 'Unknown user')})" if "user" in message else ""
            if message["role"] == "user":
                chat_content += f"<div style='color: orange'><b>You</b>{agent_info}: {message['content']}</div><br>"
            else:
                chat_content += f"<div><b>Assistant{agent_info}:</b> {message['content']}</div><br>"
        
        # Display all messages in the container
        chat_container.markdown(chat_content, unsafe_allow_html=True)

def update_agent_status(agent_name: str, status: str):
    """Update the status of an user."""
    if agent_name in st.session_state.users:
        st.session_state.users[agent_name]["status"] = status
        st.session_state.users[agent_name]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def update_agent_exploration(agent_name: str, full_exploration: bool):
    """Update the full exploration status of an user."""
    if agent_name in st.session_state.users:
        st.session_state.users[agent_name]["full_exploration"] = full_exploration

def increment_agent_exploration(agent_name: str):
    """Increment the explorations completed counter for an user."""
    if agent_name in st.session_state.users:
        st.session_state.users[agent_name]["explorations_completed"] += 1

def display_agent_dashboard():
    """Display a dashboard of user statuses."""
    st.subheader("User Dashboard")
    
    # Convert user data to DataFrame for display
    agent_data = []
    for agent_name, agent_info in st.session_state.users.items():
        agent_data.append({
            "user": agent_name,
            "Status": agent_info["status"],
            "Last Active": agent_info["last_active"] or "Never",
            "Explorations": agent_info["explorations_completed"],
            "Full Exploration": "Yes" if agent_info["full_exploration"] else "No"
        })
    
    df = pd.DataFrame(agent_data)
    
    # Apply styling based on status
    def color_status(val):
        if val == "Active":
            return "background-color: #FFEB3B"  # Yellow
        elif val == "Completed":
            return "background-color: #4CAF50"  # Green
        elif val == "Failed":
            return "background-color: #F44336"  # Red
        else:
            return ""
    
    # Apply styling based on full exploration
    def color_exploration(val):
        if val == "Yes":
            return "background-color: #4CAF50"  # Green
        else:
            return ""
    
    # Display the styled DataFrame
    st.dataframe(df.style.applymap(color_status, subset=["Status"])
                      .applymap(color_exploration, subset=["Full Exploration"]))
    
    # Add metrics for quick overview
    col1, col2, col3 = st.columns(3)
    with col1:
        active_agents = sum(1 for user in st.session_state.users.values() if user["status"] == "Active")
        st.metric("Active users", active_agents)
    
    with col2:
        total_explorations = sum(user["explorations_completed"] for user in st.session_state.users.values())
        st.metric("Total Explorations", total_explorations)
        
    with col3:
        full_explorations = sum(1 for user in st.session_state.users.values() if user["full_exploration"])
        st.metric("Full Explorations", full_explorations)

# Update your main function
def main():
    st.set_page_config(page_title="FULL Multi-user Chat Interface", layout="wide")
    
    st.title("FULL Multi-user Chat Interface with Dashboard")
    
    # Create tabs for chat, dashboard, and conversation history
    tab1, tab2, tab3 = st.tabs(["Chat", "User Dashboard", "Conversation History"])
    
    with tab1:
        # Chat interface
        st.subheader("Chat with FastInnovation users")
        
        # User selection
        agent_options = list(st.session_state.users.keys())
        selected_agent = st.selectbox("Select user", agent_options)
        
        # User input
        message = st.text_area("Message", placeholder="Ask something...")
        
        if st.button("Send"):
            if not message.strip():
                st.error("Please enter a message")
                return
            
            # Add user message to history
            add_to_history("user", message, selected_agent)
            
            try:
                with st.spinner(f"Running flow with {selected_agent}..."):
                    # Pass the conversation history to LangFlow with the selected user
                    response = run_flow(
                        message,
                        agent_name=selected_agent,
                        history=st.session_state.conversation_history[:-1]  # Exclude the current message
                    )
                    
                    # Extract the response text
                    response_text = response["outputs"][0]["outputs"][0]["results"]["message"]["text"]
                    
                    # Add bot response to history with user info
                    add_to_history("assistant", response_text, selected_agent)
                    
                    # Force a rerun to update the display
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.error("Response: " + str(response) if 'response' in locals() else "No response received")
                
                # Update user status to failed
                update_agent_status(selected_agent, "Failed")

        # Display conversation history
        display_conversation()
        
        # Conversation management options
        col1, col2, col3, col4 = st.columns(4)  # Add a column for the save to DB button
        with col1:
            # Add option to clear conversation
            if st.button("Clear Conversation"):
                st.session_state.conversation_history = []
                st.rerun()
                
        with col2:
            if st.button("Init a new conversation"):
                st.session_state.conversation_history = []
                # st.rerun()

        with col3:
            # Save conversation as downloadable file
            if st.button("Download Conversation"):
                # Convert conversation history to JSON string
                json_str = json.dumps(st.session_state.conversation_history, indent=2)
                
                # Create a download button for the JSON file
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name="conversation.json",
                    mime="application/json"
                )
                
        with col4:
            # Add a new button to save conversation to database
            conversation_name = st.text_input("Conversation Name (optional)")
            if st.button("Save to Database"):
                if len(st.session_state.conversation_history) > 0:
                    # Save conversation to database
                    conversation_id = save_to_database(
                        selected_agent, 
                        st.session_state.conversation_history,
                        conversation_name
                    )
                    st.success(f"Conversation saved to database with ID: {conversation_id}")
                else:
                    st.warning("No conversation to save")
    
    with tab2:
        # User dashboard
        display_agent_dashboard()
        
        # Add a section for user management
        st.subheader("User Management")
        
        # Reset user status
        col1, col2 = st.columns(2)
        with col1:
            agent_to_reset = st.selectbox("Reset User Status", 
                                         ["Select a user"] + agent_options)
            if st.button("Reset Status") and agent_to_reset != "Select a user":
                update_agent_status(agent_to_reset, "Idle")
                st.success(f"Reset {agent_to_reset} status to Idle")
                st.rerun()
                
        with col2:
            if st.button("Reset All Users"):
                for user in st.session_state.users:
                    st.session_state.users[user]["status"] = "Idle"
                    st.session_state.users[user]["full_exploration"] = False
                st.success("All users reset to Idle status")
                st.rerun()
        
        # Add a new user
        st.subheader("Add New User")
        new_agent_name = st.text_input("New User Name")
        if st.button("Add User") and new_agent_name:
            if new_agent_name not in st.session_state.users:
                st.session_state.users[new_agent_name] = {
                    "status": "Idle", 
                    "last_active": None, 
                    "explorations_completed": 0, 
                    "full_exploration": False
                }
                st.success(f"Added new user: {new_agent_name}")
                st.rerun()
            else:
                st.error(f"User {new_agent_name} already exists")
                
        # Auto-refresh dashboard option
        if st.checkbox("Auto-refresh dashboard (every 10 seconds)"):
            st.write("Dashboard will refresh automatically...")
            time.sleep(10)
            st.rerun()
    
    # New tab for conversation history
    with tab3:
        st.subheader("Conversation History")
        
        # Filter options
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_user = st.selectbox(
                "Filter by User", 
                ["All Users"] + agent_options
            )
        
        # Get conversations from database
        if filter_user == "All Users":
            conversations = get_conversations()
        else:
            conversations = get_conversations(filter_user)
        
        # Display conversations in an expandable table
        if not conversations:
            st.info("No saved conversations found")
        else:
            # Create a dataframe for display
            conv_data = []
            for conv in conversations:
                # Parse the conversation data to count messages
                conv_json = json.loads(conv["conversation_data"])
                num_messages = len(conv_json)
                
                # Get first and last message timestamps
                first_msg_time = conv_json[0]["timestamp"] if num_messages > 0 else "N/A"
                last_msg_time = conv_json[-1]["timestamp"] if num_messages > 0 else "N/A"
                
                conv_data.append({
                    "ID": conv["id"],
                    "User": conv["user_id"],
                    "Name": conv["conversation_name"] or f"Conversation {conv['id']}",
                    "Messages": num_messages,
                    "Started": first_msg_time,
                    "Last Message": last_msg_time,
                    "Saved": conv["timestamp"]
                })
            
            # Convert to dataframe
            conv_df = pd.DataFrame(conv_data)
            
            # Create expandable view of conversations
            for _, row in conv_df.iterrows():
                with st.expander(f"{row['Name']} - User: {row['User']} - {row['Messages']} messages"):
                    # Get the full conversation
                    full_conv = get_conversation_by_id(row["ID"])
                    if full_conv:
                        conv_data = json.loads(full_conv["conversation_data"])
                        
                        # Display the conversation
                        st.subheader(f"Conversation: {row['Name']}")
                        st.write(f"User: {row['User']}")
                        st.write(f"Saved: {row['Saved']}")
                        
                        # Display messages
                        for msg in conv_data:
                            user_name = msg.get("user", "Unknown")
                            if msg["role"] == "user":
                                st.markdown(f"**👤 User** ({user_name}): {msg['content']}")
                            else:
                                st.markdown(f"**🤖 Assistant** ({user_name}): {msg['content']}")
                        
                        # Add options to load this conversation into the chat
                        if st.button(f"Load Conversation {row['ID']} into Chat", key=f"load_{row['ID']}"):
                            st.session_state.conversation_history = conv_data
                            st.success(f"Loaded conversation {row['ID']} into chat")
                            st.rerun()
                        
                        # Option to download this specific conversation
                        json_str = json.dumps(conv_data, indent=2)
                        st.download_button(
                            label=f"Download Conversation {row['ID']}",
                            data=json_str,
                            file_name=f"conversation_{row['ID']}.json",
                            mime="application/json",
                            key=f"download_{row['ID']}"
                        )
                        
                        # Option to delete this conversation
                        if st.button(f"Delete Conversation {row['ID']}", key=f"delete_{row['ID']}"):
                            delete_conversation(row["ID"])
                            st.success(f"Deleted conversation {row['ID']}")
                            st.rerun()

# Add a function to delete conversations
def delete_conversation(conversation_id):
    """
    Delete a conversation from the database.
    
    Args:
        conversation_id: The ID of the conversation to delete
    """
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()