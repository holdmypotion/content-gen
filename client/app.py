import streamlit as st
import requests
import time
import json
import os
from datetime import datetime
from pathlib import Path

# Page configuration
st.set_page_config(
        page_title="Content Generator",
        page_icon="✍️",
        layout="wide"
        )

st.title("Content Generator")

# Backend API endpoint
BACKEND_URL = "http://backend:8000"  # Use service name in Docker network
DB_PATH = "/app/db"  # Path inside container (but we'll fetch from backend if needed)

# Initialize session state
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    api_url = st.text_input("Backend URL", value=BACKEND_URL)

# Create tabs
tab1, tab2 = st.tabs(["📚 Browse Entries", "✨ Generate New"])

# TAB 1: Browse entries
with tab1:
    st.header("Generated Entries")
    
    # Try to read JSON files from db directory
    try:
        db_files = sorted(
            Path(DB_PATH).glob("content_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if not db_files:
            st.info("No generated entries found yet.")
        else:
            # Create a selectbox to choose which entry to view
            file_names = [f.name for f in db_files]
            selected_file = st.selectbox("Select an entry:", file_names)
            
            if selected_file:
                file_path = Path(DB_PATH) / selected_file
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Display entry details
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("📋 Entry Info")
                    st.write(f"**File:** {selected_file}")
                    st.write(f"**Created:** {data.get('timestamp', 'N/A')}")
                    st.write(f"**Keywords:** {data.get('reference_keywords', 'N/A')}")
                
                with col2:
                    st.subheader("📊 Status")
                    has_idea = 'idea' in data
                    has_post = 'post' in data
                    st.write(f"**Idea Generated:** {'✅' if has_idea else '❌'}")
                    st.write(f"**Post Generated:** {'✅' if has_post else '❌'}")
                
                # Display idea
                if has_idea:
                    st.subheader("💡 Idea")
                    st.write(data.get('idea'))
                
                # Display post
                if has_post:
                    st.subheader("📝 Post")
                    st.write(data.get('post'))
    
    except Exception as e:
        st.error(f"Error reading entries: {str(e)}")

# TAB 2: Generate new content
with tab2:
    st.header("Generate New Content")
    
    # Input for reference keywords
    reference_keywords = st.text_area(
            "Reference Keywords",
            placeholder="Enter keywords or reference topics separated by commas or newlines...",
            height=120
            )
    
    # Generate button
    if st.button("🚀 Generate Content", use_container_width=True, disabled=st.session_state.is_generating):
        if not reference_keywords.strip():
            st.error("Please enter at least one reference keyword")
        else:
            st.session_state.is_generating = True
            try:
                # Initiate generation
                response = requests.post(
                        f"{api_url}/generate",
                        json={"reference_keywords": reference_keywords},
                        timeout=30
                        )

                if response.status_code == 200:
                    task_data = response.json()
                    task_id = task_data.get('task_id')

                    # Poll for completion
                    with st.spinner("Generating content..."):
                        max_retries = 60
                        for attempt in range(max_retries):
                            status_response = requests.get(
                                    f"{api_url}/task/{task_id}",
                                    timeout=10
                                    )
                            status_data = status_response.json()

                            if status_data['status'] == 'SUCCESS':
                                st.success("Content generated successfully! Check the 'Browse Entries' tab to view it.")
                                break
                            elif status_data['status'] == 'FAILURE':
                                st.error(f"Generation failed: {status_data.get('error')}")
                                break

                            time.sleep(1)
                        else:
                            st.warning("Generation is taking longer than expected")
                else:
                    st.error(f"Error: {response.status_code}")

            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {str(e)}")
            finally:
                st.session_state.is_generating = False

# Footer
st.divider()
st.caption(f"Content Generator • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
