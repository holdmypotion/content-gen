import streamlit as st
import requests
import time
from datetime import datetime
import urllib.parse
import json
import base64

# Page configuration
st.set_page_config(
    page_title="Content Generator",
    page_icon="✍️",
    layout="wide"
)

# Backend API endpoint
BACKEND_URL = "http://backend:8000"

# Initialize session state
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False
if "is_regenerating" not in st.session_state:
    st.session_state.is_regenerating = False


def load_auth_from_local_storage():
    """Load authentication from browser local storage via query params."""
    try:
        query_params = st.query_params
        if "token" in query_params and st.session_state.token is None:
            st.session_state.token = query_params["token"]
        if "user" in query_params and st.session_state.user is None:
            encoded_user = query_params["user"]
            st.session_state.user = json.loads(base64.b64decode(encoded_user).decode())
    except:
        pass


def save_auth_to_local_storage():
    """Save authentication to browser local storage via query params."""
    try:
        if st.session_state.token:
            st.query_params["token"] = st.session_state.token
        if st.session_state.user:
            encoded_user = base64.b64encode(
                json.dumps(st.session_state.user).encode()
            ).decode()
            st.query_params["user"] = encoded_user
    except:
        pass


def clear_auth_local_storage():
    """Clear authentication from local storage."""
    try:
        if "token" in st.query_params:
            del st.query_params["token"]
        if "user" in st.query_params:
            del st.query_params["user"]
    except:
        pass


def get_auth_headers():
    """Get authorization headers with token."""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def show_auth_page():
    """Display login/signup page."""
    st.title("Content Generator")
    
    tab1 = st.tabs(["Login"])[0]
    # tab2 = st.tabs(["Sign Up"])[0]  # Sign up disabled
    
    with tab1:
        st.subheader("Login")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form", clear_on_submit=False):
                email_or_username = st.text_input("Email or Username")
                password = st.text_input("Password", type="password")
                
                submitted = st.form_submit_button("Login", use_container_width=True)
                
                if submitted:
                    if not email_or_username or not password:
                        st.error("Please fill in all fields")
                    else:
                        try:
                            response = requests.post(
                                f"{BACKEND_URL}/auth/login",
                                json={
                                    "email_or_username": email_or_username,
                                    "password": password
                                },
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                st.session_state.token = data["access_token"]
                                st.session_state.user = data["user"]
                                save_auth_to_local_storage()
                                st.success("Logged in successfully!")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Invalid credentials")
                        except Exception as e:
                            st.error(f"Login error: {str(e)}")
    
    # with tab2:
    #     st.subheader("Create Account")
    #     col1, col2, col3 = st.columns([1, 2, 1])
    #     with col2:
    #         with st.form("signup_form", clear_on_submit=False):
    #             email = st.text_input("Email")
    #             username = st.text_input("Username (alphanumeric, min 3 chars)")
    #             password = st.text_input("Password (min 6 chars)", type="password")
    #             password_confirm = st.text_input("Confirm Password", type="password")
    #             
    #             submitted = st.form_submit_button("Sign Up", use_container_width=True)
    #             
    #             if submitted:
    #                 if not all([email, username, password, password_confirm]):
    #                     st.error("Please fill in all fields")
    #                 elif password != password_confirm:
    #                     st.error("Passwords don't match")
    #                 else:
    #                     try:
    #                         response = requests.post(
    #                             f"{BACKEND_URL}/auth/signup",
    #                             json={
    #                                 "email": email,
    #                                 "username": username,
    #                                 "password": password
    #                             },
    #                             timeout=10
    #                         )
    #                         
    #                         if response.status_code == 200:
    #                             data = response.json()
    #                             st.session_state.token = data["access_token"]
    #                             st.session_state.user = data["user"]
    #                             save_auth_to_local_storage()
    #                             st.success("Account created and logged in!")
    #                             time.sleep(0.5)
    #                             st.rerun()
    #                         else:
    #                             error_detail = response.json().get("detail", "Signup failed")
    #                             st.error(f"Signup error: {error_detail}")
    #                     except Exception as e:
    #                         st.error(f"Signup error: {str(e)}")


def show_main_app():
    """Display main application."""
    # Header with user info
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.title("Content Generator")
    with col2:
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.user = None
            clear_auth_local_storage()
            st.rerun()
    
    st.caption(f"Logged in as: {st.session_state.user['username']}")
    
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
        
        # Fetch contents from backend
        try:
            response = requests.get(
                f"{BACKEND_URL}/contents?skip=0&limit=100",
                headers=get_auth_headers(),
                timeout=10
            )
            response.raise_for_status()
            contents = response.json()
            
            if not contents:
                st.info("No generated entries found yet.")
            else:
                # Create title to ID mapping
                entry_options = {}
                for content in contents:
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
                    selected_title = st.selectbox("Select an entry:", list(entry_options.keys()))
                    selected_id = entry_options.get(selected_title)
                    
                    if selected_id:
                        # Fetch the specific content
                        content_response = requests.get(
                            f"{BACKEND_URL}/content/{selected_id}",
                            headers=get_auth_headers(),
                            timeout=10
                        )
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
                            
                            if st.button("🗑️ Delete Entry", key=f"delete_entry_{selected_id}"):
                                try:
                                    delete_response = requests.delete(
                                        f"{BACKEND_URL}/content/{selected_id}",
                                        headers=get_auth_headers(),
                                        timeout=10
                                    )
                                    delete_response.raise_for_status()
                                    st.success("Entry deleted successfully!")
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to delete entry: {str(e)}")
                            
                            # Input Prompt with modal
                            prompt_text = data.get('reference_keywords', 'N/A')
                            col_prompt, col_view = st.columns([0.85, 0.15])
                            with col_prompt:
                                display_text = (prompt_text[:50] + "...") if len(prompt_text) > 50 else prompt_text
                                st.write(f"**Input Prompt:** {display_text}")
                            with col_view:
                                if st.button("👁️", key=f"view_prompt_{selected_id}", help="View full input prompt"):
                                    st.session_state[f"show_prompt_modal_{selected_id}"] = True
                            
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
                            
                            idea_edit_key = f"idea_edit_{selected_id}"
                            if idea_edit_key not in st.session_state:
                                st.session_state[idea_edit_key] = False
                            
                            col1, col2 = st.columns([0.90, 0.10])
                            with col1:
                                if st.session_state[idea_edit_key]:
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
                                                    headers=get_auth_headers(),
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
                                    st.markdown(data.get('idea'))
                            
                            with col2:
                                if not st.session_state[idea_edit_key]:
                                    if st.button("✏️", key=f"idea_edit_btn_{selected_id}", help="Edit idea"):
                                        st.session_state[idea_edit_key] = True
                                        st.rerun()
                        
                        # Display posts
                        if has_posts:
                            st.subheader("📝 Posts")
                            
                            post_index_key = f"post_index_{selected_id}"
                            if post_index_key not in st.session_state:
                                st.session_state[post_index_key] = len(posts) - 1
                            
                            # Regenerate button
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
                                            headers=get_auth_headers(),
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
                                                        headers=get_auth_headers(),
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
                            
                            # Post navigation
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
                            
                            edit_key = f"edit_{selected_id}"
                            if edit_key not in st.session_state:
                                st.session_state[edit_key] = False
                            
                            col1, col2, col3, col4 = st.columns([0.90, 0.05, 0.025, 0.025])
                            with col1:
                                if st.session_state[edit_key]:
                                    edited_post = st.text_area(
                                        "Edit Post",
                                        value=current_post,
                                        height=250,
                                        label_visibility="collapsed"
                                    )
                                    col_save, col_cancel = st.columns(2)
                                    with col_save:
                                        if st.button("💾 Save", key=f"save_{selected_id}", use_container_width=True):
                                            try:
                                                updated_posts = posts.copy()
                                                updated_posts[current_post_index] = edited_post
                                                update_response = requests.put(
                                                    f"{BACKEND_URL}/content/{selected_id}",
                                                    json={"posts": updated_posts},
                                                    headers=get_auth_headers(),
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
                                    st.markdown(current_post)
                            
                            with col2:
                                if not st.session_state[edit_key]:
                                    encoded_text = urllib.parse.quote(current_post)
                                    linkedin_url = f"https://www.linkedin.com/feed/?shareActive=true&text={encoded_text}"
                                    st.link_button("🔗", linkedin_url, help="Post on LinkedIn")
                            
                            with col3:
                                if not st.session_state[edit_key]:
                                    if st.button("✏️", key=f"edit_btn_{selected_id}", help="Edit post"):
                                        st.session_state[edit_key] = True
                                        st.rerun()
                            
                            with col4:
                                if not st.session_state[edit_key]:
                                    if st.button("🗑️", key=f"delete_btn_{selected_id}", help="Delete post"):
                                        try:
                                            updated_posts = posts.copy()
                                            updated_posts.pop(current_post_index)
                                            update_response = requests.put(
                                                f"{BACKEND_URL}/content/{selected_id}",
                                                json={"posts": updated_posts},
                                                headers=get_auth_headers(),
                                                timeout=10
                                            )
                                            update_response.raise_for_status()
                                            st.success("Post deleted successfully!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Failed to delete: {str(e)}")
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
                                        headers=get_auth_headers(),
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
                                                    headers=get_auth_headers(),
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
        
        with st.form("generate_form", clear_on_submit=False):
            provider = st.selectbox("Select Provider", ["gpt", "gemini"])
            
            reference_keywords = st.text_area(
                "Input Prompt",
                placeholder="Enter your input prompt, keywords, or webpage links...",
                height=120
            )
            
            submitted = st.form_submit_button("🚀 Generate Content", use_container_width=True, disabled=st.session_state.is_generating)
            
            if submitted:
                if not reference_keywords.strip():
                    st.error("Please enter at least one reference keyword")
                else:
                    st.session_state.is_generating = True
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/generate",
                            json={
                                "reference_keywords": reference_keywords,
                                "provider": provider
                            },
                            headers=get_auth_headers(),
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            task_data = response.json()
                            task_id = task_data.get('task_id')
                            
                            with st.spinner(f"Generating content with {provider}..."):
                                max_retries = 60
                                for attempt in range(max_retries):
                                    status_response = requests.get(
                                        f"{BACKEND_URL}/task/{task_id}",
                                        headers=get_auth_headers(),
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


# Load auth from local storage on app startup
load_auth_from_local_storage()

# Main app logic
if st.session_state.token is None:
    show_auth_page()
else:
    show_main_app()
