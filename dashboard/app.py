"""Multi-Agent Code Analysis Dashboard with Auth."""
import os
import streamlit as st
import httpx
from datetime import datetime

API_URL = os.getenv('API_URL', 'http://localhost:8000')

st.set_page_config(page_title='Multi-Agent Dashboard', layout='wide', initial_sidebar_state='expanded')

# ============ Session State ============
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'  # login, signup, dashboard
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None


def get_auth_header():
    """Get Authorization header with token."""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


# ============ Auth Pages ============

def page_signup():
    """User signup page with enhanced UI."""
    # Set up page styling
    st.set_page_config(page_title='Sign Up - Code Analysis', layout='centered')
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
        .signup-container {
            max-width: 450px;
            margin: 0 auto;
            padding: 2rem;
        }
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .auth-header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        .auth-header p {
            color: #888;
            font-size: 1rem;
        }
        .divider {
            height: 1px;
            background: #eee;
            margin: 2rem 0;
        }
        .signup-link {
            text-align: center;
            margin-top: 1.5rem;
            color: #666;
        }
        .signup-link a {
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="auth-header">
            <h1>🔐 Create Account</h1>
            <p>Join the future of code analysis</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Signup Form
    with st.form("signup_form", border=False):
        st.markdown("### Account Details")
        
        # Name input
        name = st.text_input(
            "Full Name",
            placeholder="John Doe",
            help="Your full name"
        )
        
        # Email input
        email = st.text_input(
            "Email Address",
            placeholder="you@example.com",
            help="We'll never share your email"
        )
        
        # Password input
        password = st.text_input(
            "Password",
            type="password",
            placeholder="At least 8 characters",
            help="Create a strong password with numbers and special characters"
        )
        
        # Password confirmation
        password_confirm = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Re-enter your password"
        )
        
        st.markdown("---")
        
        # Terms checkbox
        terms_agreed = st.checkbox(
            "I agree to the Terms of Service and Privacy Policy",
            value=False
        )
        
        # Submit button
        submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
        with submit_col2:
            if st.form_submit_button("🚀 Create Account", use_container_width=True):
                # Validation
                errors = []
                
                if not name or len(name.strip()) < 2:
                    errors.append("❌ Please enter a valid name (at least 2 characters)")
                
                if not email or '@' not in email:
                    errors.append("❌ Please enter a valid email address")
                
                if not password or len(password) < 8:
                    errors.append("❌ Password must be at least 8 characters")
                
                if password != password_confirm:
                    errors.append("❌ Passwords do not match")
                
                if not terms_agreed:
                    errors.append("❌ You must agree to the Terms of Service")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        resp = httpx.post(
                            f"{API_URL}/auth/signup",
                            json={"email": email, "password": password, "name": name},
                            timeout=10
                        )
                        resp.raise_for_status()
                        st.success("✅ Account created successfully! Redirecting to login...")
                        st.balloons()
                        import time
                        time.sleep(1)
                        st.session_state.page = 'login'
                        st.rerun()
                    except httpx.HTTPError as e:
                        error_msg = e.response.text if hasattr(e, 'response') else str(e)
                        if 'already exists' in error_msg.lower():
                            st.error("❌ This email is already registered. Please log in instead.")
                        else:
                            st.error(f"❌ Signup failed: {error_msg}")
    
    # Login link
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-top: 1rem;">
            <p>Already have an account? 
            <a href="#" onclick="document.querySelector('[data-testid=stButton] button:contains(\"Log in\")').click()">
            <strong style="color: #0066cc;">Log in here</strong></a></p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("← Back to Login", use_container_width=True):
            st.session_state.page = 'login'
            st.rerun()


def page_login():
    """User login page with enhanced UI."""
    st.set_page_config(page_title='Log In - Code Analysis', layout='centered')
    
    # Custom CSS for authentication pages
    st.markdown("""
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .login-container {
            max-width: 450px;
            margin: 2rem auto;
            padding: 0;
        }
        .auth-card {
            background: white;
            border-radius: 12px;
            padding: 2.5rem;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
        }
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .auth-header h1 {
            font-size: 2rem;
            color: #1a1a1a;
            margin-bottom: 0.5rem;
        }
        .auth-header p {
            color: #666;
            font-size: 0.95rem;
        }
        .form-group {
            margin-bottom: 1.2rem;
        }
        .form-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #333;
            font-size: 0.95rem;
        }
        .form-group input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 0.95rem;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .btn-primary {
            width: 100%;
            padding: 0.75rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .divider {
            height: 1px;
            background: #eee;
            margin: 1.5rem 0;
            position: relative;
        }
        .divider-text {
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 0 0.5rem;
            color: #999;
            font-size: 0.85rem;
        }
        .auth-footer {
            text-align: center;
            margin-top: 1.5rem;
            color: #666;
        }
        .auth-footer a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .auth-footer a:hover {
            text-decoration: underline;
        }
        .demo-credentials {
            background: #f0f4ff;
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 1.5rem;
            border-left: 4px solid #667eea;
        }
        .demo-credentials p {
            margin: 0.3rem 0;
            font-size: 0.9rem;
            color: #333;
        }
        .demo-credentials strong {
            color: #667eea;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Main container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Header
        st.markdown("""
        <div class="auth-header">
            <h1>🚀 Welcome Back</h1>
            <p>Intelligent Code Analysis Platform</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Demo credentials info
        st.markdown("""
        <div class="demo-credentials">
            <p><strong>Demo Account:</strong></p>
            <p>Email: <code>demo@example.com</code></p>
            <p>Password: <code>demo123456</code></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login Form
        with st.form("login_form", border=False):
            email = st.text_input(
                "📧 Email Address",
                placeholder="you@example.com",
                help="Your registered email"
            )
            
            password = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Enter your password",
                help="Your account password"
            )
            
            remember_me = st.checkbox("Remember me", value=False)
            
            st.markdown("---")
            
            # Submit button
            submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
            with submit_col2:
                if st.form_submit_button("🔓 Log In", use_container_width=True):
                    if not email or not password:
                        st.error("❌ Please enter both email and password")
                    elif '@' not in email:
                        st.error("❌ Please enter a valid email address")
                    else:
                        try:
                            resp = httpx.post(
                                f"{API_URL}/auth/login",
                                json={"email": email, "password": password},
                                timeout=10
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            
                            st.session_state.token = data["access_token"]
                            st.session_state.user_id = data["user_id"]
                            st.session_state.user_email = email
                            st.session_state.user_role = data["role"]
                            
                            st.success("✅ Logged in successfully!")
                            st.balloons()
                            st.session_state.page = 'dashboard'
                            import time
                            time.sleep(0.5)
                            st.rerun()
                        
                        except httpx.HTTPError as e:
                            error_msg = e.response.text if hasattr(e, 'response') else str(e)
                            if '401' in str(e.response.status_code if hasattr(e, 'response') else ''):
                                st.error("❌ Invalid email or password. Please try again.")
                            else:
                                st.error(f"❌ Login failed: {error_msg}")
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div class="auth-footer">
            <p>Don't have an account? <a href="#">Create one now</a></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Signup button
        if st.button("📝 Create New Account", use_container_width=True):
            st.session_state.page = 'signup'
            st.rerun()


def page_dashboard():
    """Main dashboard page."""
    st.title("🚀 Multi-Agent Code Analysis Dashboard")
    
    # Sidebar: user info and logout
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user_email}**")
        st.write(f"Role: `{st.session_state.user_role}`")
        
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.token = None
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.session_state.user_role = None
            st.session_state.page = 'login'
            st.rerun()
        
        st.divider()
        
        # Tabs for project creation methods
        tab1, tab2 = st.tabs(["GitHub URL", "Upload ZIP"])
        
        with tab1:
            st.subheader("GitHub Repository")
            
            with st.form("create_project_form"):
                project_name = st.text_input("Project Name", placeholder="My Awesome Project")
                repo_url = st.text_input("GitHub URL", placeholder="https://github.com/user/repo")
                
                personas = st.multiselect(
                    "Generate docs for:",
                    options=["sde", "pm"],
                    default=["sde"],
                    help="SDE = Software Dev Engineer, PM = Product Manager"
                )
                
                description = st.text_area(
                    "Description (optional)",
                    placeholder="Brief description of the project..."
                )
                
                if st.form_submit_button("Create Project", use_container_width=True):
                    if not project_name or not repo_url:
                        st.error("Project name and repository URL are required")
                    else:
                        try:
                            resp = httpx.post(
                                f"{API_URL}/projects/",
                                json={
                                    "name": project_name,
                                    "repository_url": repo_url,
                                    "personas": personas,
                                    "description": description
                                },
                                headers=get_auth_header(),
                                timeout=10
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            st.success(f"✓ Project created! Starting analysis...")
                            st.rerun()
                        except httpx.HTTPError as e:
                            error_detail = e.response.text if hasattr(e, 'response') else str(e)
                            st.error(f"Failed to create project: {error_detail}")
        
        with tab2:
            st.subheader("Upload ZIP File")
            
            with st.form("upload_project_form"):
                zip_file = st.file_uploader("Select ZIP file", type=['zip'])
                upload_project_name = st.text_input("Project Name", placeholder="My Project", key="upload_name")
                
                upload_personas = st.multiselect(
                    "Generate docs for:",
                    options=["sde", "pm"],
                    default=["sde"],
                    key="upload_personas"
                )
                
                if st.form_submit_button("Upload & Analyze", use_container_width=True):
                    if not zip_file or not upload_project_name:
                        st.error("ZIP file and project name are required")
                    else:
                        try:
                            resp = httpx.post(
                                f"{API_URL}/projects/upload",
                                files={"file": (zip_file.name, zip_file.getvalue(), "application/zip")},
                                headers={
                                    **get_auth_header(),
                                    "name": upload_project_name,
                                    "personas": ",".join(upload_personas)
                                },
                                timeout=30
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            st.success(f"✓ Project created! Analysis starting...")
                            st.rerun()
                        except httpx.HTTPError as e:
                            error_detail = e.response.text if hasattr(e, 'response') else str(e)
                            st.error(f"Upload failed: {error_detail}")
    
    # Check if viewing project details
    if st.session_state.selected_project:
        # Show back button at the top
        col1, col2, col3 = st.columns([1, 8, 1])
        with col1:
            if st.button("← Back", use_container_width=True):
                st.session_state.selected_project = None
                st.rerun()
        
        show_project_details(st.session_state.selected_project, get_auth_header)
    else:
        show_projects_list(get_auth_header)


def show_projects_list(get_auth_header):
    """Show list of all projects."""
    st.subheader("Your Projects")
    
    # Add auto-refresh for analyzing projects
    any_analyzing = False
    
    try:
        resp = httpx.get(
            f"{API_URL}/projects/",
            headers=get_auth_header(),
            timeout=10
        )
        resp.raise_for_status()
        projects = resp.json()
        
        if not projects:
            st.info("📌 No projects yet. Create one in the sidebar to get started!")
        else:
            cols = st.columns(2)
            for i, project in enumerate(projects):
                with cols[i % 2]:
                    with st.container(border=True):
                        st.write(f"### {project['name']}")
                        st.write(f"📌 ID: `{project['project_id']}`")
                        
                        # Show repo info
                        if project['repository_url']:
                            # Check if it's a ZIP upload (starts with "Uploaded ZIP:")
                            if project['repository_url'].startswith('Uploaded ZIP:'):
                                st.write(f"📦 {project['repository_url']}")
                            else:
                                st.write(f"🔗 GitHub: {project['repository_url']}")
                        
                        st.write(f"👥 Personas: {', '.join(project['personas']).upper()}")
                        
                        # Status badge with colors
                        status = project['status']
                        if status == 'analyzing':
                            any_analyzing = True
                            progress = project.get('progress', 0.0)
                            status_msg = project.get('status_message', 'Analyzing...')
                            
                            st.info(f"⏳ Status: **{status.upper()}**")
                            st.caption(f"📊 {status_msg}")
                            st.progress(progress / 100.0, text=f"{int(progress)}%")
                        elif status == 'completed':
                            st.success(f"✓ Status: **{status.upper()}**")
                        elif status == 'failed':
                            st.error(f"✗ Status: **{status.upper()}**")
                            if project.get('error'):
                                st.caption(f"Error: {project['error']}")
                        else:
                            st.write(f"Status: **{status.upper()}**")
                        
                        st.caption(f"Created: {project['created_at'][:10]}")
                        
                        if st.button("View Details", key=f"btn_{project['project_id']}", use_container_width=True):
                            st.session_state.selected_project = project['project_id']
                            st.rerun()
            
            # Auto-refresh if any project is analyzing
            if any_analyzing:
                import time
                time.sleep(2)  # Wait 2 seconds before refresh
                st.rerun()
    
    except httpx.HTTPError as e:
        st.error(f"Failed to load projects: {e}")


def show_project_details(project_id: str, get_auth_header):
    """Show detailed analysis for a project."""
    try:
        # Get project info
        project_resp = httpx.get(
            f"{API_URL}/projects/{project_id}",
            headers=get_auth_header(),
            timeout=10
        )
        project_resp.raise_for_status()
        project = project_resp.json()
        
        st.title(f"📊 {project['name']}")
        
        # Repository Intelligence Section
        with st.expander("🔍 Repository Intelligence", expanded=True):
            try:
                meta_resp = httpx.get(
                    f"{API_URL}/analysis/{project_id}/metadata",
                    headers=get_auth_header(),
                    timeout=10
                )
                meta_resp.raise_for_status()
                metadata = meta_resp.json()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Repo Type", metadata['repo_type'].upper())
                    st.metric("Code Files", metadata['code_files'])
                
                with col2:
                    st.metric("Code Chunks", metadata['total_code_chunks'])
                    st.metric("Total Files", metadata['total_files'])
                
                with col3:
                    st.metric("Confidence", f"{metadata['confidence_score']:.0%}")
                    st.metric("Frameworks", len(metadata['frameworks']))
                
                # Frameworks and entry points
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Detected Frameworks:**")
                    for fw in metadata['frameworks']:
                        st.write(f"• {fw.upper()}")
                
                with col2:
                    st.write("**Entry Points:**")
                    for ep in metadata['entry_points'][:5]:
                        st.write(f"• {ep}")
                
                # Important Files with Types
                if metadata.get('important_files_with_types'):
                    st.write("**Important Files:**")
                    files_df_data = []
                    for file_info in metadata['important_files_with_types'][:15]:
                        files_df_data.append({
                            'File Name': file_info['name'],
                            'Type': file_info.get('type', 'unknown'),
                            'Size (KB)': file_info.get('size_kb', 0),
                            'Path': file_info.get('path', '')
                        })
                    
                    if files_df_data:
                        import pandas as pd
                        files_df = pd.DataFrame(files_df_data)
                        st.dataframe(files_df, use_container_width=True, hide_index=True)
                
                # Dependencies
                if metadata['dependencies']:
                    st.write("**Key Dependencies:**")
                    deps_cols = st.columns(2)
                    for i, (pkg, ver) in enumerate(list(metadata['dependencies'].items())[:6]):
                        with deps_cols[i % 2]:
                            st.write(f"`{pkg}` {ver}")
            
            except Exception as e:
                st.warning(f"Could not load repository metadata: {e}")
        
        # Persona-Specific Analysis Section
        personas = project.get('personas', [])
        if len(personas) >= 2 or (len(personas) == 1 and personas[0] in ['sde', 'pm']):
            st.divider()
            st.subheader("📋 Persona-Specific Insights")
            
            persona_tabs = []
            if 'sde' in personas:
                persona_tabs.append("SDE Analysis")
            if 'pm' in personas:
                persona_tabs.append("PM Analysis")
            
            if persona_tabs:
                persona_tab_objs = st.tabs(persona_tabs)
                
                # SDE Tab
                if 'sde' in personas:
                    sde_tab_index = persona_tabs.index("SDE Analysis")
                    with persona_tab_objs[sde_tab_index]:
                        try:
                            sde_resp = httpx.get(
                                f"{API_URL}/analysis/{project_id}/persona-analysis/sde",
                                headers=get_auth_header(),
                                timeout=15
                            )
                            sde_resp.raise_for_status()
                            sde_analysis = sde_resp.json()
                            
                            st.write("### 🛠️ Software Development Engineer Analysis")
                            st.write(sde_analysis.get('overview', ''))
                            
                            # Architecture
                            arch = sde_analysis.get('architecture', {})
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("**Architecture Pattern:**")
                                st.write(arch.get('architecture_pattern', 'N/A'))
                            with col2:
                                st.write("**Framework Stack:**")
                                st.write(", ".join(arch.get('frameworks', [])) or "None")
                            
                            # Technical Details
                            with st.expander("📊 Technical Details"):
                                tech = sde_analysis.get('technical_details', {})
                                st.write(f"**Language:** {tech.get('language', 'N/A')}")
                                st.write(f"**Dependencies:** {tech.get('dependencies_count', 0)}")
                                
                                metrics = tech.get('code_metrics', {})
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Files", metrics.get('total_files', 0))
                                with col2:
                                    st.metric("Code Files", metrics.get('code_files', 0))
                                with col3:
                                    st.metric("Code Chunks", metrics.get('total_chunks', 0))
                            
                            # Code Quality
                            with st.expander("✅ Code Quality"):
                                quality = sde_analysis.get('code_quality', {})
                                st.write(f"**Code Structure Rating:** {quality.get('code_structure_rating', 'N/A')}")
                                st.write(f"**Dependency Health:** {quality.get('dependency_health', 'N/A')}")
                                
                                st.write("**Suggested Improvements:**")
                                for improvement in quality.get('suggested_improvements', []):
                                    st.write(f"• {improvement}")
                            
                            # Recommendations
                            with st.expander("💡 SDE Recommendations"):
                                for i, rec in enumerate(sde_analysis.get('recommendations', []), 1):
                                    st.write(f"{i}. {rec}")
                            
                            # Key Files
                            with st.expander("📂 Key Files for SDE"):
                                key_files = sde_analysis.get('key_files', [])
                                if key_files:
                                    for f in key_files[:10]:
                                        st.write(f"• **{f.get('name', 'N/A')}** ({f.get('type', 'unknown')})")
                                else:
                                    st.write("No specific key files identified")
                        
                        except Exception as e:
                            st.error(f"Could not load SDE analysis: {e}")
                
                # PM Tab
                if 'pm' in personas:
                    pm_tab_index = persona_tabs.index("PM Analysis")
                    with persona_tab_objs[pm_tab_index]:
                        try:
                            pm_resp = httpx.get(
                                f"{API_URL}/analysis/{project_id}/persona-analysis/pm",
                                headers=get_auth_header(),
                                timeout=15
                            )
                            pm_resp.raise_for_status()
                            pm_analysis = pm_resp.json()
                            
                            st.write("### 📊 Product Manager Analysis")
                            st.write(pm_analysis.get('overview', ''))
                            
                            # Features
                            with st.expander("🎯 Identified Features"):
                                features = pm_analysis.get('features', {})
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write("**Authentication:**")
                                    auth = features.get('authentication', [])
                                    if auth:
                                        for a in auth:
                                            st.write(f"• {a}")
                                    else:
                                        st.write("None detected")
                                
                                with col2:
                                    st.write("**Data Management:**")
                                    data = features.get('data_management', [])
                                    if data:
                                        for d in data:
                                            st.write(f"• {d}")
                                    else:
                                        st.write("None detected")
                                
                                st.write("**API Endpoints:**")
                                api = features.get('api_endpoints', [])
                                if api:
                                    for a in api:
                                        st.write(f"• {a}")
                            
                            # User Flows
                            with st.expander("👥 User Flows"):
                                flows = pm_analysis.get('user_flows', {})
                                st.write("**Primary Flows:**")
                                for flow in flows.get('primary_flows', []):
                                    st.write(f"• {flow}")
                                
                                st.write("\n**Entry Mechanisms:**")
                                for ep in flows.get('entry_mechanisms', [])[:5]:
                                    st.write(f"• {ep}")
                            
                            # Business Logic
                            with st.expander("💼 Business Logic"):
                                logic = pm_analysis.get('business_logic', {})
                                st.write("**Core Functions:**")
                                for func in logic.get('core_functions', [])[:5]:
                                    st.write(f"• {func}")
                                
                                st.write("\n**Business Rules:**")
                                for rule in logic.get('business_rules', []):
                                    st.write(f"• {rule}")
                            
                            # Scalability
                            with st.expander("📈 Scalability"):
                                scale = pm_analysis.get('scalability', {})
                                st.write(f"**Rating:** {scale.get('scalability_rating', 'N/A')}")
                                
                                st.write("\n**Bottlenecks:**")
                                for b in scale.get('bottlenecks', []):
                                    st.write(f"• {b}")
                                
                                st.write("\n**Recommendations:**")
                                for rec in scale.get('recommendations', []):
                                    st.write(f"• {rec}")
                            
                            # Recommendations
                            with st.expander("💡 PM Recommendations"):
                                for i, rec in enumerate(pm_analysis.get('recommendations', []), 1):
                                    st.write(f"{i}. {rec}")
                            
                            # Stakeholders
                            with st.expander("👨‍💼 Stakeholders"):
                                st.write("**Key Stakeholders:**")
                                for stakeholder in pm_analysis.get('stakeholders', []):
                                    st.write(f"• {stakeholder}")
                        
                        except Exception as e:
                            st.error(f"Could not load PM analysis: {e}")
        
        # Code Chunks Section
        with st.expander("📦 Code Chunks", expanded=False):
            try:
                chunks_resp = httpx.get(
                    f"{API_URL}/analysis/{project_id}/chunks?limit=15",
                    headers=get_auth_header(),
                    timeout=10
                )
                chunks_resp.raise_for_status()
                chunks_data = chunks_resp.json()
                
                st.write(f"Total Chunks: **{chunks_data['total_chunks']}**")
                
                for chunk in chunks_data['chunks']:
                    with st.container(border=True):
                        st.write(f"**{chunk['name']}** ({chunk['chunk_type']})")
                        st.caption(f"{chunk['file_path']}:{chunk['start_line']}-{chunk['end_line']}")
                        with st.expander("View Code"):
                            st.code(chunk['content'], language=chunk['language'])
            
            except Exception as e:
                st.warning(f"Could not load code chunks: {e}")
        
        # Code Search Section
        with st.expander("🔎 Code Search", expanded=False):
            search_query = st.text_input(
                "Search code",
                placeholder="e.g., 'authentication', 'database', 'api endpoints'..."
            )
            
            if search_query:
                try:
                    search_resp = httpx.get(
                        f"{API_URL}/analysis/{project_id}/search",
                        params={"query": search_query, "limit": 10},
                        headers=get_auth_header(),
                        timeout=10
                    )
                    search_resp.raise_for_status()
                    search_data = search_resp.json()
                    
                    st.write(f"Found **{search_data['total_results']}** results")
                    
                    for result in search_data['results']:
                        with st.container(border=True):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**{result['name']}**")
                                st.caption(f"{result['file_path']}")
                            with col2:
                                st.write(f"**{result['relevance_score']:.0%}**")
                            
                            with st.expander("Preview"):
                                st.code(result['preview'])
                
                except Exception as e:
                    st.error(f"Search failed: {e}")
    
    except (httpx.HTTPError, Exception) as e:
        st.error(f"Failed to load project: {e}")


# ============ Main App Logic ============

if st.session_state.page == 'login':
    page_login()
elif st.session_state.page == 'signup':
    page_signup()
elif st.session_state.page == 'dashboard':
    page_dashboard()

