import requests
import streamlit as st
from dotenv import load_dotenv
import os
import json
import pandas as pd
import time
from datetime import datetime

# Load environment variables
load_dotenv()

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
        "Agent_1": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False},
        "Agent_2": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False},
        "Agent_3": {"status": "Idle", "last_active": None, "explorations_completed": 0, "full_exploration": False}
    }

# Available user statuses: "Idle", "Active", "Completed", "Failed"

def run_flow(message: str, agent_name: str = "Agent_1", history: list = None) -> dict:
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
        # You'll need to adapt this logic based on how your LangFlow indicates completion
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
    for message in st.session_state.conversation_history:
        agent_info = f" (via {message.get('user', 'Unknown user')})" #if "user" in message else ""
        if message["role"] == "user":
            st.markdown(f"<div style='color: orange'><b>You</b>:{agent_info}: {message['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"**Assistant{agent_info}:** {message['content']}")

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
    st.subheader("user Dashboard")
    
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

def main():
    st.set_page_config(page_title="FULL Multi-user Chat Interface", layout="wide")
    
    st.title("FULL Multi-user Chat Interface with Dashboard")
    
    # Create tabs for chat and dashboard
    tab1, tab2 = st.tabs(["Chat", "user Dashboard"])
    
    with tab1:
        # Chat interface
        st.subheader("Chat with FastInnovation users")
        
        # user selection
        agent_options = list(st.session_state.users.keys())
        selected_agent = st.selectbox("Select user", agent_options)
        
        # Display conversation history
        display_conversation()
        
        # User input
        message = st.text_area("Message", placeholder="Ask something...")
        
        if st.button("Send"):
            if not message.strip():
                st.error("Please enter a message")
                return
            
            # Add user message to history
            add_to_history("user", message)
            
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
        
        # Conversation management options
        col1, col2, col3 = st.columns(3)
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
    
    with tab2:
        # user dashboard
        display_agent_dashboard()
        
        # Add a section for user management
        st.subheader("user Management")
        
        # Reset user status
        col1, col2 = st.columns(2)
        with col1:
            agent_to_reset = st.selectbox("Reset user Status", 
                                         ["Select an user"] + agent_options)
            if st.button("Reset Status") and agent_to_reset != "Select an user":
                update_agent_status(agent_to_reset, "Idle")
                st.success(f"Reset {agent_to_reset} status to Idle")
                st.rerun()
                
        with col2:
            if st.button("Reset All users"):
                for user in st.session_state.users:
                    st.session_state.users[user]["status"] = "Idle"
                    st.session_state.users[user]["full_exploration"] = False
                st.success("All users reset to Idle status")
                st.rerun()
        
        # Add a new user
        st.subheader("Add New user")
        new_agent_name = st.text_input("New user Name")
        if st.button("Add user") and new_agent_name:
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
                st.error(f"user {new_agent_name} already exists")
                
        # Auto-refresh dashboard option
        if st.checkbox("Auto-refresh dashboard (every 10 seconds)"):
            st.write("Dashboard will refresh automatically...")
            time.sleep(10)
            st.rerun()

if __name__ == "__main__":
    main()