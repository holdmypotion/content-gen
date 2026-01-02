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
if "is_regenerating" not in st.session_state:
    st.session_state.is_regenerating = False

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
                title = content.get('reference_keywords', 'Unknown')
                
                if idea:
                    if '**Title:**' in idea:
                        lines = idea.split('**Title:**')[1].split('\n')
                        title = next((line.strip() for line in lines if line.strip()), title)
                    elif 'Title:' in idea:
                        lines = idea.split('Title:')[1].split('\n')
                        title = next((line.strip() for line in lines if line.strip()), title)

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
                        posts = data.get('posts') or []
                        has_posts = len(posts) > 0
                        st.write(f"**Idea Generated:** {'✅' if has_idea else '❌'}")
                        st.write(f"**Posts Generated:** {len(posts) if has_posts else '❌'}")

                    # Display idea
                    if has_idea:
                        st.subheader("💡 Idea")
                        
                        # Initialize edit state for idea
                        idea_edit_key = f"idea_edit_{selected_id}"
                        if idea_edit_key not in st.session_state:
                            st.session_state[idea_edit_key] = False
                        
                        col1, col2 = st.columns([0.90, 0.10])
                        with col1:
                            if st.session_state[idea_edit_key]:
                                # Edit mode
                                edited_idea = st.text_area(
                                        "Edit Idea",
                                        value=data.get('idea'),
                                        height=200,
                                        label_visibility="collapsed"
                                        )
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    if st.button("💾 Save Idea", key=f"save_idea_{selected_id}", use_container_width=True):
                                        try:
                                            update_response = requests.put(
                                                    f"{BACKEND_URL}/content/{selected_id}",
                                                    json={"idea": edited_idea},
                                                    timeout=10
                                            )
                                            update_response.raise_for_status()
                                            st.session_state[idea_edit_key] = False
                                            st.success("Idea saved successfully!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Failed to save: {str(e)}")
                                with col_cancel:
                                    if st.button("❌ Cancel", key=f"cancel_idea_{selected_id}", use_container_width=True):
                                        st.session_state[idea_edit_key] = False
                                        st.rerun()
                            else:
                                # View mode
                                st.markdown(data.get('idea'))
                        
                        with col2:
                            if not st.session_state[idea_edit_key]:
                                if st.button("✏️", key=f"idea_edit_btn_{selected_id}", help="Edit idea"):
                                    st.session_state[idea_edit_key] = True
                                    st.rerun()

                    # Display posts
                    if has_posts:
                        st.subheader("📝 Posts")

                        # Initialize post index state for this entry
                        post_index_key = f"post_index_{selected_id}"
                        if post_index_key not in st.session_state:
                            st.session_state[post_index_key] = len(posts) - 1

                        # Regenerate button row
                        regen_col1, regen_col2 = st.columns([0.85, 0.15])
                        with regen_col2:
                            if st.button("🔄 Regenerate Post", key=f"regen_{selected_id}", disabled=st.session_state.is_regenerating):
                                st.session_state.is_regenerating = True
                                try:
                                    regen_response = requests.post(
                                            f"{BACKEND_URL}/regenerate-post",
                                            json={
                                                "content_id": selected_id,
                                                "provider": data.get('provider', 'gemini')
                                                },
                                            timeout=30
                                            )
                                    if regen_response.status_code == 200:
                                        task_data = regen_response.json()
                                        task_id = task_data.get('task_id')

                                        with st.spinner("Regenerating post..."):
                                            max_retries = 60
                                            for attempt in range(max_retries):
                                                status_response = requests.get(
                                                        f"{BACKEND_URL}/task/{task_id}",
                                                        timeout=10
                                                        )
                                                status_data = status_response.json()

                                                if status_data['status'] == 'SUCCESS':
                                                    st.success("Post regenerated successfully!")
                                                    st.session_state[post_index_key] = len(posts)
                                                    break
                                                elif status_data['status'] == 'FAILURE':
                                                    st.error(f"Regeneration failed: {status_data.get('error')}")
                                                    break

                                                time.sleep(1)
                                            else:
                                                st.warning("Regeneration is taking longer than expected")
                                    else:
                                        st.error(f"Error: {regen_response.status_code} - {regen_response.text}")
                                except requests.exceptions.RequestException as e:
                                    st.error(f"Connection error: {str(e)}")
                                finally:
                                    st.session_state.is_regenerating = False
                                    st.rerun()

                        # Post navigation if multiple posts
                        if len(posts) > 1:
                            nav_col1, nav_col2, nav_col3 = st.columns([0.1, 0.8, 0.1])
                            with nav_col1:
                                if st.button("◀", key=f"prev_{selected_id}", disabled=st.session_state[post_index_key] == 0):
                                    st.session_state[post_index_key] -= 1
                                    st.rerun()
                            with nav_col2:
                                st.write(f"**Post {st.session_state[post_index_key] + 1} of {len(posts)}**")
                            with nav_col3:
                                if st.button("▶", key=f"next_{selected_id}", disabled=st.session_state[post_index_key] >= len(posts) - 1):
                                    st.session_state[post_index_key] += 1
                                    st.rerun()

                        current_post_index = st.session_state[post_index_key]
                        current_post = posts[current_post_index] if current_post_index < len(posts) else posts[-1]

                        # Initialize edit state for this entry
                        edit_key = f"edit_{selected_id}"
                        if edit_key not in st.session_state:
                            st.session_state[edit_key] = False

                        col1, col2, col3 = st.columns([0.90, 0.05, 0.05])
                        with col1:
                            if st.session_state[edit_key]:
                                # Edit mode
                                edited_post = st.text_area(
                                        "Edit Post",
                                        value=current_post,
                                        height=250,
                                        label_visibility="collapsed"
                                        )
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    if st.button("💾 Save", key=f"save_{selected_id}", use_container_width=True):
                                        # Update via API - update specific post in array
                                        try:
                                            updated_posts = posts.copy()
                                            updated_posts[current_post_index] = edited_post
                                            update_response = requests.put(
                                                    f"{BACKEND_URL}/content/{selected_id}",
                                                    json={"posts": updated_posts},
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
                                 st.markdown(current_post)

                        with col2:
                            if not st.session_state[edit_key]:
                                import urllib.parse
                                encoded_text = urllib.parse.quote(current_post)
                                linkedin_url = f"https://www.linkedin.com/feed/?shareActive=true&text={encoded_text}"
                                st.link_button("🔗", linkedin_url, help="Post on LinkedIn")

                        with col3:
                            if not st.session_state[edit_key]:
                                if st.button("✏️", key=f"edit_btn_{selected_id}", help="Edit post"):
                                    st.session_state[edit_key] = True
                                    st.rerun()
                    elif has_idea:
                        st.info("No posts generated yet. Click 'Regenerate Post' to generate one.")
                        if st.button("🔄 Generate Post", key=f"gen_post_{selected_id}", disabled=st.session_state.is_regenerating):
                            st.session_state.is_regenerating = True
                            try:
                                regen_response = requests.post(
                                        f"{BACKEND_URL}/regenerate-post",
                                        json={
                                            "content_id": selected_id,
                                            "provider": data.get('provider', 'gemini')
                                            },
                                        timeout=30
                                        )
                                if regen_response.status_code == 200:
                                    task_data = regen_response.json()
                                    task_id = task_data.get('task_id')

                                    with st.spinner("Generating post..."):
                                        max_retries = 60
                                        for attempt in range(max_retries):
                                            status_response = requests.get(
                                                    f"{BACKEND_URL}/task/{task_id}",
                                                    timeout=10
                                                    )
                                            status_data = status_response.json()

                                            if status_data['status'] == 'SUCCESS':
                                                st.success("Post generated successfully!")
                                                break
                                            elif status_data['status'] == 'FAILURE':
                                                st.error(f"Generation failed: {status_data.get('error')}")
                                                break

                                            time.sleep(1)
                                        else:
                                            st.warning("Generation is taking longer than expected")
                                else:
                                    st.error(f"Error: {regen_response.status_code} - {regen_response.text}")
                            except requests.exceptions.RequestException as e:
                                st.error(f"Connection error: {str(e)}")
                            finally:
                                st.session_state.is_regenerating = False
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