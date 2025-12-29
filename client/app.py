import streamlit as st
import requests
import time
from datetime import datetime

# Page configuration
st.set_page_config(
        page_title="Content Generator",
        page_icon="✍️",
        layout="wide"
        )

st.title("Content Generator")

# Backend API endpoint
BACKEND_URL = "http://backend:8000"  # Use service name in Docker network

# Initialize session state
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False

# Create tabs
tab1, tab2 = st.tabs(["📚 Browse Entries", "✨ Generate New"])

# TAB 1: Browse entries
with tab1:
    col1, col2 = st.columns([0.95, 0.05])
    with col1:
        st.header("Generated Entries")
    with col2:
        if st.button("🔄", help="Refresh entries"):
            st.rerun()

    # Fetch contents from MongoDB via API
    try:
        response = requests.get(f"{BACKEND_URL}/contents?skip=0&limit=100", timeout=10)
        response.raise_for_status()
        contents = response.json()

        if not contents:
            st.info("No generated entries found yet.")
        else:
            # Create title to ID mapping
            entry_options = {}
            for content in contents:
                # Extract title from idea field if available
                idea = content.get('idea', '')
                if idea and '**Title:**' in idea:
                    lines = idea.split('**Title:**')[1].split('\n')
                    title = next((line.strip() for line in lines if line.strip()), content.get('reference_keywords', 'Unknown'))
                else:
                    title = content.get('reference_keywords', 'Unknown')

                content_id = content.get('_id') or content.get('id')
                if content_id:
                    entry_options[title] = content_id

            if not entry_options:
                st.warning("No entries with valid IDs found.")
            else:
                # Create a selectbox with titles instead of IDs
                selected_title = st.selectbox("Select an entry:", list(entry_options.keys()))
                selected_id = entry_options.get(selected_title)

                if selected_id:
                    # Fetch the specific content
                    content_response = requests.get(f"{BACKEND_URL}/content/{selected_id}", timeout=10)
                    content_response.raise_for_status()
                    data = content_response.json()

                    # Display entry details
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        st.subheader("📋 Entry Info")
                        entry_id = data.get('_id') or data.get('id')
                        st.write(f"**ID:** {entry_id}")
                        st.write(f"**Created:** {data.get('timestamp', 'N/A')}")
                        st.write(f"**Provider:** {data.get('provider', 'N/A')}")

                        # Input Prompt with modal
                        prompt_text = data.get('reference_keywords', 'N/A')
                        col_prompt, col_view = st.columns([0.85, 0.15])
                        with col_prompt:
                            # Truncate for display
                            display_text = (prompt_text[:50] + "...") if len(prompt_text) > 50 else prompt_text
                            st.write(f"**Input Prompt:** {display_text}")
                        with col_view:
                            if st.button("👁️", key=f"view_prompt_{selected_id}", help="View full input prompt"):
                                st.session_state[f"show_prompt_modal_{selected_id}"] = True

                        # Modal for full prompt
                        if st.session_state.get(f"show_prompt_modal_{selected_id}", False):
                            with st.expander("📝 Full Input Prompt", expanded=True):
                                st.text(prompt_text)
                                if st.button("Close", key=f"close_prompt_{selected_id}", use_container_width=True):
                                    st.session_state[f"show_prompt_modal_{selected_id}"] = False
                                    st.rerun()

                    with col2:
                        st.subheader("📊 Status")
                        has_idea = 'idea' in data and data['idea']
                        has_post = 'post' in data and data['post']
                        st.write(f"**Idea Generated:** {'✅' if has_idea else '❌'}")
                        st.write(f"**Post Generated:** {'✅' if has_post else '❌'}")

                    # Display idea
                    if has_idea:
                        st.subheader("💡 Idea")
                        st.write(data.get('idea'))

                    # Display post
                    if has_post:
                        st.subheader("📝 Post")

                        # Initialize edit state for this entry
                        edit_key = f"edit_{selected_id}"
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
                                    if st.button("💾 Save", key=f"save_{selected_id}", use_container_width=True):
                                        # Update via API
                                        try:
                                            update_response = requests.put(
                                                    f"{BACKEND_URL}/content/{selected_id}",
                                                    json={"post": edited_post},
                                                    timeout=10
                                                    )
                                            update_response.raise_for_status()
                                            st.session_state[edit_key] = False
                                            st.success("Post saved successfully!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Failed to save: {str(e)}")
                                with col_cancel:
                                    if st.button("❌ Cancel", key=f"cancel_{selected_id}", use_container_width=True):
                                        st.session_state[edit_key] = False
                                        st.rerun()
                            else:
                                # View mode
                                st.write(data.get('post'))

                        with col2:
                            if not st.session_state[edit_key]:
                                if st.button("✏️", key=f"edit_btn_{selected_id}", help="Edit post"):
                                    st.session_state[edit_key] = True
                                    st.rerun()

    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {str(e)}")
    except Exception as e:
        st.error(f"Error reading entries: {str(e)}")

# TAB 2: Generate new content
with tab2:
    st.header("Generate New Content")

    # Provider selection
    provider = st.selectbox("Select Provider", ["gpt", "gemini"])

    # Input for input prompt
    reference_keywords = st.text_area(
            "Input Prompt",
            placeholder="Enter your input prompt, keywords, or webpage links...",
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
