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
            # Load titles from all files
            file_options = {}
            for f in db_files:
                try:
                    with open(f, 'r') as file:
                        data = json.load(file)
                        # Extract title from idea field if available
                        idea = data.get('idea', '')
                        if idea and '**Title:**' in idea:
                            title = idea.split('**Title:**')[1].split('\n')[0].strip()
                        else:
                            title = data.get('reference_keywords', f.name)
                        file_options[title] = f.name
                except:
                    file_options[f.name] = f.name
            
            # Create a selectbox with titles instead of filenames
            selected_title = st.selectbox("Select an entry:", list(file_options.keys()))
            selected_file = file_options[selected_title]
            
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
                    st.write(f"**Provider:** {data.get('provider', 'N/A')}")
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
                    
                    # Initialize edit state for this file
                    edit_key = f"edit_{selected_file}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False
                    
                    col1, col2 = st.columns([0.95, 0.05])
                    with col1:
                        if st.session_state[edit_key]:
                            # Edit mode
                            edited_post = st.text_area(
                                "Edit Post",
                                value=data.get('post'),
                                height=250,
                                label_visibility="collapsed"
                            )
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.button("💾 Save", key=f"save_{selected_file}", use_container_width=True):
                                    # Update the data
                                    data['post'] = edited_post
                                    # Save back to file
                                    try:
                                        with open(file_path, 'w') as f:
                                            json.dump(data, f, indent=2)
                                        st.session_state[edit_key] = False
                                        st.success("Post saved successfully!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Failed to save: {str(e)}")
                            with col_cancel:
                                if st.button("❌ Cancel", key=f"cancel_{selected_file}", use_container_width=True):
                                    st.session_state[edit_key] = False
                                    st.rerun()
                        else:
                            # View mode
                            st.write(data.get('post'))
                    
                    with col2:
                        if not st.session_state[edit_key]:
                            if st.button("✏️", key=f"edit_btn_{selected_file}", help="Edit post"):
                                st.session_state[edit_key] = True
                                st.rerun()
    
    except Exception as e:
        st.error(f"Error reading entries: {str(e)}")

# TAB 2: Generate new content
with tab2:
    st.header("Generate New Content")

    # Provider selection
    provider = st.selectbox("Select Provider", ["gemini", "gpt"])

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
                    f"{BACKEND_URL}/generate",
                    json={
                        "reference_keywords": reference_keywords,
                        "provider": provider
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    task_data = response.json()
                    task_id = task_data.get('task_id')

                    # Poll for completion
                    with st.spinner(f"Generating content with {provider}..."):
                        max_retries = 60
                        for attempt in range(max_retries):
                            status_response = requests.get(
                                f"{BACKEND_URL}/task/{task_id}",
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
                    st.error(f"Error: {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {str(e)}")
            finally:
                st.session_state.is_generating = False

# Footer
st.divider()
st.caption(f"Content Generator • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
