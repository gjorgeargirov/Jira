import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import re
import calendar
import time

# Import modules
from database import (
    init_db, add_task, get_tasks, get_subtasks, 
    update_task, update_task_status, delete_task, 
    get_cached_tasks
)
from utils import (
    get_status_color, get_priority_color,
    calculate_due_status, get_urgency_class,
    create_calendar_view
)
from analytics import generate_analytics
from validation import validate_task_input, sanitize_input, validate_labels
from auth import (
    login_required, logout_user, get_all_users, 
    get_user, update_user, delete_user, register_user,
    get_current_user_profile, update_current_user_profile
)

# Add this at the top of your app.py file, after imports
if 'button_actions' not in st.session_state:
    st.session_state.button_actions = {}

def perform_action(action_id, action_fn, *args, **kwargs):
    """Perform an action exactly once per session."""
    # Check if this specific action has already been performed
    if action_id not in st.session_state.button_actions:
        # Mark action as in progress to prevent duplicate execution
        st.session_state.button_actions[action_id] = True
        
        # Perform the action
        action_fn(*args, **kwargs)
        
        # Clear the cache
        st.cache_data.clear()
        
        # Refresh the UI
        st.rerun()

# Define specific actions
def move_task(task_id, new_status):
    """Move a task to a new status."""
    action_id = f"move_{task_id}_{new_status}_{int(time.time())}"
    perform_action(action_id, update_task_status, task_id, new_status)

def remove_task(task_id):
    """Delete a task."""
    action_id = f"delete_{task_id}_{int(time.time())}"
    perform_action(action_id, delete_task, task_id)

# Add this function at the beginning of your app.py file, right after the imports
def delete_task_with_refresh(task_id):
    """Delete a task and refresh the page."""
    delete_task(task_id)
    st.cache_data.clear()
    st.rerun()

# Disable caching for task data to ensure we always get fresh data
@st.cache_data(ttl=1)  # Very short TTL to essentially disable caching
def get_fresh_tasks():
    """Get uncached task data to ensure we see the latest updates"""
    return get_tasks()

# Set page configuration
st.set_page_config(
    page_title="Task Manager Pro",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load external CSS
def load_css(css_file):
    with open(css_file, 'r') as f:
        return f.read()

# Apply CSS
st.markdown(f"<style>{load_css('style.css')}</style>", unsafe_allow_html=True)

# Load JavaScript from external file
def load_js(js_file):
    with open(js_file, 'r') as f:
        return f.read()

# Check if static directory exists, create if not
if not os.path.exists('static'):
    os.makedirs('static')
    
# Create scripts.js if it doesn't exist, but without keyboard shortcuts
js_file_path = 'static/scripts.js'
if not os.path.exists(js_file_path):
    with open(js_file_path, 'w') as f:
        f.write("""
// Application scripts
document.addEventListener('DOMContentLoaded', function() {
    console.log('Task Manager application loaded');
    // No keyboard shortcuts - removed as per user preference
});
        """)

# Apply JavaScript
st.markdown(f"<script>{load_js('static/scripts.js')}</script>", unsafe_allow_html=True)

# Initialize the database
init_db()

# Handle authentication first
if not login_required():
    st.stop()  # Stop execution if not authenticated

# Main application
st.markdown(f"""
    <h3 style="font-size: 24px; margin-bottom: 20px; color: #3a4f63;">
        Welcome to Task Manager Pro
        <span style="font-size: 18px; color: #6c757d; margin-left: 8px;">Hi, {st.session_state.username}!</span>
    </h3>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Add user profile card at the top for visibility
    st.markdown(f"""
        <div style="background-color: #f8f9fa; border-radius: 10px; padding: 12px; margin-bottom: 20px; border-left: 4px solid #4CAF50;">
            <div style="display: flex; align-items: center;">
                <div style="background-color: #4CAF50; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-size: 16px; font-weight: bold;">
                    {st.session_state.username[0].upper()}
                </div>
                <div>
                    <div style="font-weight: bold; font-size: 16px;">{st.session_state.username}</div>
                    <div style="font-size: 12px; color: #666;">Logged in</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Profile action buttons
    profile_col1, profile_col2 = st.columns(2)
    with profile_col1:
        if st.button("👤 My Profile", use_container_width=True, key="profile_top_btn", help="Edit your profile settings"):
            if 'show_profile' not in st.session_state:
                st.session_state.show_profile = False
            st.session_state.show_profile = not st.session_state.show_profile
            st.rerun()
    with profile_col2:
        if st.button("🚪 Logout", use_container_width=True, key="logout_top_btn"):
            logout_user()
    
    # Now add the Task Management header AFTER the profile section
    st.markdown("""
        <div style="display: flex; align-items: center; margin: 1.5rem 0 1rem 0;">
            <img src="https://img.icons8.com/color/48/000000/task.png" width="32" style="margin-right: 0.5rem;">
            <h2 style="margin: 0; font-size: 1.5rem;">Task Management</h2>
        </div>
        <hr style="margin-bottom: 1.5rem;">
    """, unsafe_allow_html=True)
    
    # Determine if we're editing or adding
    is_editing = 'editing_task' in st.session_state and st.session_state.editing_task
    
    # Initialize task form visibility state if not exists
    if 'show_task_form' not in st.session_state:
        st.session_state.show_task_form = True  # Default to expanded
    
    # Create a header with toggle button for the Add/Edit Task form
    form_title = "✏️ Edit Task" if is_editing else "✨ Add New Task"
    
    # Form header with toggle button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"<div style='font-size: 1.1rem; font-weight: 600;'>{form_title}</div>", unsafe_allow_html=True)
    with col2:
        toggle_icon = "▼" if st.session_state.show_task_form else "▶"
        if st.button(toggle_icon, key="toggle_task_form"):
            st.session_state.show_task_form = not st.session_state.show_task_form
            st.rerun()
    
    # Only show the form if not collapsed
    if st.session_state.show_task_form:
        # Get current task if editing
        current_task = None
        if is_editing:
            tasks_df = get_fresh_tasks()
            task_matches = tasks_df[tasks_df['id'] == st.session_state.editing_task]
            if not task_matches.empty:
                current_task = task_matches.iloc[0]
            else:
                st.error("Task not found!")
                st.session_state.editing_task = None
                st.rerun()
        
        with st.form("task_form", clear_on_submit=not is_editing):
            # Task Information
            st.markdown('<div style="font-weight: 500; margin-bottom: 0.5rem;">Basic Information</div>', unsafe_allow_html=True)
            
            new_title = st.text_input(
                "Title*", 
                value=current_task['title'] if current_task is not None else "",
                help="Enter a concise task title"
            )
            
            # Add parent task selection for subtasks
            all_tasks = get_fresh_tasks()
            if not all_tasks.empty:
                parent_tasks = all_tasks[all_tasks['parent_id'].isna() & (all_tasks['id'] != st.session_state.get('editing_task', -1))][['id', 'title']]
                
                parent_id = None
                if len(parent_tasks) > 0:
                    parent_options = ["None"] + parent_tasks['title'].tolist()
                    current_parent = "None"
                    if current_task is not None and not pd.isna(current_task.get('parent_id')):
                        parent_match = parent_tasks[parent_tasks['id'] == current_task['parent_id']]
                        if not parent_match.empty:
                            current_parent = parent_match.iloc[0]['title']
                    
                    parent_task = st.selectbox(
                        "Parent Task (optional)",
                        parent_options,
                        index=parent_options.index(current_parent) if current_parent in parent_options else 0,
                        help="Link this task to a parent task"
                    )
                    if parent_task != "None":
                        parent_id = parent_tasks[parent_tasks['title'] == parent_task]['id'].iloc[0]
            
            new_description = st.text_area(
                "Description", 
                value=current_task['description'] if current_task is not None else "",
                height=120,
                help="Provide details about the task"
            )
            
            st.markdown('<div style="margin: 1rem 0 0.5rem 0; font-weight: 500;">Task Details</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                new_priority = st.selectbox(
                    "Priority",
                    ["Critical", "High", "Medium", "Low"],
                    index=["Critical", "High", "Medium", "Low"].index(
                        current_task['priority']) if current_task is not None else 1,
                    help="Set the importance level"
                )
            
            with col2:
                new_status = st.selectbox(
                    "Status",
                    ["To Do", "In Progress", "Done", "Blocked"],
                    index=["To Do", "In Progress", "Done", "Blocked"].index(
                        current_task['status']) if current_task is not None else 0,
                    help="Current status of the task"
                )
            
            st.markdown('<div style="margin: 1rem 0 0.5rem 0; font-weight: 500;">Due Date & Time</div>', unsafe_allow_html=True)
            
            date_col, time_col = st.columns(2)
            with date_col:
                default_date = None
                if current_task is not None and current_task['due_date']:
                    try:
                        default_date = datetime.strptime(current_task['due_date'], '%Y-%m-%d').date()
                    except:
                        default_date = datetime.now().date() + timedelta(days=1)
                else:
                    default_date = datetime.now().date() + timedelta(days=1)
                
                new_due_date = st.date_input(
                    "Due Date",
                    value=default_date,
                    help="When is this task due"
                )
            
            with time_col:
                default_time = "09:00"
                if current_task is not None and current_task.get('due_time'):
                    default_time = current_task['due_time']
                
                new_due_time = st.time_input(
                    "Due Time", 
                    value=datetime.strptime(default_time, '%H:%M').time(),
                    help="Optional time deadline"
                )
            
            st.markdown('<div style="margin: 1rem 0 0.5rem 0; font-weight: 500;">Additional Details</div>', unsafe_allow_html=True)
            
            new_labels = st.text_input(
                "Labels (comma-separated)",
                value=current_task.get('labels', '') if current_task is not None else "",
                help="Add tags like 'frontend,bug,design'"
            )
            
            # Add file upload support
            uploaded_files = st.file_uploader(
                "Attach Files", 
                accept_multiple_files=True,
                help="Attach relevant documents"
            )
            
            # Submit button with different text based on edit/add mode
            submit_label = "💾 Update Task" if is_editing else "💾 Add Task"
            submit_button = st.form_submit_button(
                submit_label, 
                use_container_width=True,
                type="primary"
            )
            
            if submit_button:
                if not new_title:
                    st.error("⚠️ Task title is required!")
                else:
                    attachments = None
                    if uploaded_files:
                        attachments = [
                            {"name": file.name, "type": file.type, "size": file.size}
                            for file in uploaded_files
                        ]
                    
                    # Format the due date and time properly
                    due_date_str = new_due_date.strftime('%Y-%m-%d')
                    due_time_str = new_due_time.strftime('%H:%M')
                    
                    if is_editing:
                        try:
                            # Add debugging information
                            st.info(f"Updating task {current_task['id']}...")
                            st.write(f"New title: {new_title}")
                            st.write(f"New status: {new_status}")
                            st.write(f"New priority: {new_priority}")
                            st.write(f"New due date: {due_date_str}")
                            
                            # Make sure values are properly formatted
                            task_id = int(current_task['id'])
                            
                            # Execute the update
                            update_task(
                                task_id,
                                new_title,
                                new_description,
                                new_status,
                                new_priority,
                                due_date_str,
                                due_time_str,
                                new_labels
                            )
                            st.success("✅ Task updated successfully!")
                            
                            # Force a clear refresh of the data
                            st.cache_data.clear()
                            
                            # Clear the editing state and rerun the app
                            st.session_state.editing_task = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating task: {str(e)}")
                            st.error("Please check the task data and try again.")
                    else:
                        add_task(
                            new_title,
                            new_description,
                            new_status,
                            new_priority,
                            due_date_str,
                            due_time_str,
                            new_labels
                        )
                        st.success("✅ Task added successfully!")
                    st.rerun()
        
        # Cancel button for editing mode
        if is_editing:
            if st.button("❌ Cancel Editing", use_container_width=True):
                st.session_state.editing_task = None
                st.rerun()
    
    # Add quick navigation options
    st.markdown('<div style="margin: 1.5rem 0 0.5rem 0; font-weight: 500;">Quick Navigation</div>', unsafe_allow_html=True)
    
    quick_filters = st.radio(
        "Filter Tasks",
        ["All Tasks", "Due Today", "Overdue", "High Priority", "Completed"],
        index=0,
        horizontal=False,
        label_visibility="collapsed"
    )
    
    # Initialize analytics visibility in session state if not exists
    if 'show_analytics' not in st.session_state:
        st.session_state.show_analytics = False
    
    if st.button("📊 View Analytics", use_container_width=True):
        # Toggle analytics visibility
        st.session_state.show_analytics = not st.session_state.show_analytics
        st.rerun()
    
    # Add help information at the bottom
    with st.expander("ℹ️ Help & Tips", expanded=False):
        st.markdown("""
            ### Task Management Tips
            - Use labels to organize related tasks
            - Set realistic due dates to avoid overdue tasks
            - Update task status regularly to track progress
            - Use the search function to quickly find tasks
        """)
        
        st.markdown("""
            ### Priority Levels
            - **Critical**: Urgent tasks requiring immediate attention
            - **High**: Important tasks with significant impact
            - **Medium**: Standard priority tasks
            - **Low**: Tasks that can be deferred if needed
        """)

# Main content - Streamlined header with search
# Removed duplicate title here

# Combined search, filters and view toggles in one row
col1, col2, col3 = st.columns([5, 3, 2])

# Only show tasks if profile is not being displayed
if not ('show_profile' in st.session_state and st.session_state.show_profile):
    with col1:
        search_query = st.text_input("🔍", placeholder="Search tasks by title, description or labels", 
                                key="task-search", label_visibility="collapsed")

    with col2:
        filter_container = st.container()
        filter_col1, filter_col2 = filter_container.columns([3, 1])
        
        with filter_col1:
            filter_type = st.selectbox(
                "Quick Filter",
                ["All Tasks", "Overdue", "Due Today", "Due This Week", "High Priority", "No Due Date"],
                index=0,
                label_visibility="collapsed"
            )
        
        with filter_col2:
            show_filters = st.toggle("Filters", value=False, label_visibility="collapsed")

    with col3:
        view_type = st.radio("View", ["Kanban", "Calendar"], horizontal=True, index=0, label_visibility="collapsed")

    # Initialize filter variables with default values
    filter_status = []
    filter_priority = []
    filter_due = "All"
    use_date_range = False
    start_date = date.today()
    end_date = date.today() + timedelta(days=7)
    no_due_date = False

    # Apply quick filters
    if filter_type == "Overdue":
        filter_due = "Overdue"
    elif filter_type == "Due Today":
        filter_due = "Due Today"
    elif filter_type == "Due This Week":
        filter_due = "Due This Week"
    elif filter_type == "High Priority":
        filter_priority = ["High", "Critical"]
    elif filter_type == "No Due Date":
        # We'll handle this specially
        no_due_date = True

    # Only show the detailed filter UI if toggled on
    if show_filters:
        with st.expander("Advanced Filters", expanded=True):
            filter_cols1 = st.columns(4)
            with filter_cols1[0]:
                filter_status = st.multiselect(
                    "Status",
                    ["To Do", "In Progress", "Done", "Blocked"],
                    default=[]
                )
            
            with filter_cols1[1]:
                filter_priority = st.multiselect(
                    "Priority",
                    ["Critical", "High", "Medium", "Low"],
                    default=filter_priority
                )
            
            with filter_cols1[2]:
                filter_due = st.selectbox(
                    "Due Date",
                    ["All", "Overdue", "Due Today", "Due This Week", "Due This Month"],
                    index=["All", "Overdue", "Due Today", "Due This Week", "Due This Month"].index(filter_due)
                )
            
            with filter_cols1[3]:
                use_date_range = st.checkbox("Custom Date Range")
            
            if use_date_range:
                filter_cols2 = st.columns(2)
                with filter_cols2[0]:
                    start_date = st.date_input("From", value=date.today())
                with filter_cols2[1]:
                    end_date = st.date_input("To", value=date.today() + timedelta(days=7))
                
                if start_date > end_date:
                    st.error("Start date must be before end date")

    # Get all tasks without filters first, to check if there are any
    all_tasks = get_fresh_tasks()
    original_task_count = len(all_tasks)

    # Apply search filter separately
    filtered_tasks_df = get_fresh_tasks().copy()
    if search_query:
        search_lower = search_query.lower()
        filtered_tasks_df = filtered_tasks_df[
            filtered_tasks_df['title'].str.lower().str.contains(search_lower, na=False) |
            filtered_tasks_df['description'].str.lower().str.contains(search_lower, na=False) |
            filtered_tasks_df['labels'].str.lower().str.contains(search_lower, na=False)
        ]

    # Apply status and priority filters
    if filter_status:
        filtered_tasks_df = filtered_tasks_df[filtered_tasks_df['status'].isin(filter_status)]
    if filter_priority:
        filtered_tasks_df = filtered_tasks_df[filtered_tasks_df['priority'].isin(filter_priority)]

    # Apply date filters
    if no_due_date:
        filtered_tasks_df = filtered_tasks_df[pd.isna(filtered_tasks_df['due_date'])]
    elif use_date_range and start_date <= end_date:
        filtered_tasks_df = filtered_tasks_df[
            (pd.to_datetime(filtered_tasks_df['due_date']).dt.date >= start_date) &
            (pd.to_datetime(filtered_tasks_df['due_date']).dt.date <= end_date)
        ]
    elif filter_due != "All":
        today = date.today()
        if filter_due == "Overdue":
            filtered_tasks_df = filtered_tasks_df[pd.to_datetime(filtered_tasks_df['due_date']).dt.date < today]
        elif filter_due == "Due Today":
            filtered_tasks_df = filtered_tasks_df[pd.to_datetime(filtered_tasks_df['due_date']).dt.date == today]
        elif filter_due == "Due This Week":
            end_of_week = today + timedelta(days=(6-today.weekday()))
            filtered_tasks_df = filtered_tasks_df[
                (pd.to_datetime(filtered_tasks_df['due_date']).dt.date >= today) &
                (pd.to_datetime(filtered_tasks_df['due_date']).dt.date <= end_of_week)
            ]
        elif filter_due == "Due This Month":
            next_month = today.replace(day=1) + timedelta(days=32)
            end_of_month = next_month.replace(day=1) - timedelta(days=1)
            filtered_tasks_df = filtered_tasks_df[
                (pd.to_datetime(filtered_tasks_df['due_date']).dt.date >= today) &
                (pd.to_datetime(filtered_tasks_df['due_date']).dt.date <= end_of_month)
            ]

    # Update tasks_df to use the filtered version
    tasks_df = filtered_tasks_df

    # Add a compact filter summary and task counts
    tasks_count = len(tasks_df)
    overdue_count = len(tasks_df[pd.to_datetime(tasks_df['due_date']).dt.date < date.today()])

    # Show a compact summary as regular text
    summary_col1, summary_col2 = st.columns([3, 1])
    with summary_col1:
        # Show filter type
        filter_text = filter_type
        if filter_type != "All Tasks":
            st.caption(f"Filtered: {filter_type}")
        else:
            st.caption("All Tasks")
            
    with summary_col2:
        st.caption(f"Total: {tasks_count} • Overdue: {overdue_count}")

    # Make sure the Kanban board is displayed immediately when view_type is Kanban
    if view_type == "Kanban":
        # Create columns for each status - reordered to put Blocked first and Done at the end
        cols = st.columns(4)
        statuses = ["Blocked", "To Do", "In Progress", "Done"]
        
        for idx, status in enumerate(statuses):
            with cols[idx]:
                # Header with count
                st.markdown(
                    f"<div style='background: {get_status_color(status)}; color: white; border-radius: 6px 6px 0 0; "
                    f"padding: 0.5rem; text-align: center; font-weight: 600; margin-bottom: 0;'>"
                    f"{status} <span style='background: rgba(255,255,255,0.3); border-radius: 9999px; "
                    f"padding: 0 0.4rem;'>{len(tasks_df[tasks_df['status'] == status])}</span></div>",
                    unsafe_allow_html=True
                )
                
                # Container for tasks in this status
                status_tasks = tasks_df[tasks_df['status'] == status]
                
                if status_tasks.empty:
                    st.info("No tasks")
                
                for _, task in status_tasks.iterrows():
                    # Prepare data for display
                    due_status = calculate_due_status(task['due_date'], task['due_time'])
                    task_id = task['id']
                    
                    # Create unique keys for this task
                    edit_key = f"edit_{status}_{task_id}"
                    move_key = f"move_{status}_{task_id}"
                    delete_key = f"delete_{status}_{task_id}"
                    expand_key = f"expand_{status}_{task_id}"
                    
                    # Track expanded state in session state
                    if expand_key not in st.session_state:
                        st.session_state[expand_key] = False
                    
                    # Create a card with columns for better layout
                    with st.container():
                        # Task card container
                        priority_color = get_priority_color(task['priority'])
                        
                        # Add a border on the left based on priority
                        st.markdown(f"<hr style='margin: 0; padding: 0; border: none; height: 3px; background-color: {priority_color};'>", unsafe_allow_html=True)
                        
                        # Compact header with title and expand control
                        title_row = st.container()
                        with title_row:
                            header_col, priority_col, expand_col = st.columns([6, 2, 1])
                            with header_col:
                                # Convert title to uppercase and make it bold
                                st.markdown(f"**{task['title'].upper()}**")
                            
                            with priority_col:
                                st.markdown(f"<span style='background-color: {priority_color}; color: white; padding: 2px 6px; border-radius: 12px; font-size: 12px;'>{task['priority']}</span>", unsafe_allow_html=True)
                            
                            with expand_col:
                                expand_icon = "▼" if st.session_state[expand_key] else "▶"
                                if st.button(expand_icon, key=f"btn_{expand_key}"):
                                    st.session_state[expand_key] = not st.session_state[expand_key]
                                    st.rerun()
                        
                            # Show due date outside the expansion block (always visible) but not for Done tasks
                            if pd.notna(task['due_date']) and status != "Done":
                                st.markdown(f"<span style='color: {due_status['color']}; font-size: 0.85em;'>⏱️ {due_status['display']} • <strong>{due_status['text']}</strong></span>", unsafe_allow_html=True)
                            # For Done tasks, just show when it was completed
                            elif pd.notna(task['due_date']) and status == "Done":
                                st.markdown(f"<span style='color: #10b981; font-size: 0.85em;'>✅ Completed</span>", unsafe_allow_html=True)
                        
                        # Only show details and buttons if expanded, but NOT another due date
                        if st.session_state[expand_key]:
                            # Show description preview (but no due date here since we already show it above)
                            description = task['description'] if task['description'] else "No description provided."
                            st.caption(description)
                            
                            # Action buttons in a row
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✏️", key=edit_key, use_container_width=True, help="Edit task"):
                                    st.session_state.editing_task = task_id
                                    st.rerun()
                            
                            with col2:
                                if st.button("🗑️", key=delete_key, use_container_width=True, help="Delete task"):
                                    remove_task(task_id)
                            
                            with col3:
                                # Simplified move button with debugging
                                if status == "Blocked":
                                    # Simple approach for blocked tasks
                                    next_status = "In Progress"  # Default target for blocked tasks
                                    
                                    # Button with debugging
                                    if st.button("→", key=move_key, use_container_width=True, help=f"Move to {next_status}"):
                                        try:
                                            st.write(f"Moving task {task_id} to {next_status}...")
                                            move_task(task_id, next_status)
                                            st.success(f"Task moved to {next_status}")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error moving task: {str(e)}")
                                else:
                                    # Standard next status for other columns
                                    next_status = {
                                        "To Do": "In Progress",
                                        "In Progress": "Done",
                                        "Done": "To Do"
                                    }[status]
                                    
                                    # Button with debugging
                                    if st.button("→", key=move_key, use_container_width=True, help=f"Move to {next_status}"):
                                        try:
                                            st.write(f"Moving task {task_id} to {next_status}...")
                                            move_task(task_id, next_status)
                                            st.success(f"Task moved to {next_status}")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error moving task: {str(e)}")
                        
                        # Add a divider between tasks
                        st.markdown("<hr>", unsafe_allow_html=True)
    elif view_type == "Calendar":
        # Calendar View Section
        st.subheader("📅 Calendar View")
        
        # Add month/year selector and collapse mode toggle
        today = date.today()
        current_month = today.month
        current_year = today.year
        
        col1, col2, col3, col4 = st.columns([2, 2, 2, 4])
        
        with col1:
            selected_month = st.selectbox(
                "Month",
                list(range(1, 13)),
                index=current_month - 1,
                format_func=lambda m: calendar.month_name[m]
            )
        
        with col2:
            selected_year = st.selectbox(
                "Year",
                list(range(current_year - 1, current_year + 5)),
                index=1  # Default to current year
            )
        
        with col3:
            # Initialize collapsed mode in session state if it doesn't exist
            if 'calendar_collapsed' not in st.session_state:
                st.session_state.calendar_collapsed = False
                
            # Toggle for collapsed view
            calendar_collapsed = st.toggle("Compact View", value=st.session_state.calendar_collapsed)
            # Update session state when changed
            if calendar_collapsed != st.session_state.calendar_collapsed:
                st.session_state.calendar_collapsed = calendar_collapsed
        
        # Get all tasks
        all_calendar_tasks = tasks_df.copy()
        
        # Create a calendar grid
        monthly_cal = calendar.monthcalendar(selected_year, selected_month)
        
        # Display weekday headers with better styling
        cols = st.columns(7)
        for i, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            with cols[i]:
                st.markdown(f"<div style='text-align: center; font-weight: bold; background-color: #f0f2f6; padding: 8px; border-radius: 4px;'>{day_name}</div>", unsafe_allow_html=True)
        
        # Convert due_date to datetime for comparison
        calendar_tasks = all_calendar_tasks.copy()
        calendar_tasks['due_date_parsed'] = pd.to_datetime(calendar_tasks['due_date'], errors='coerce')
        
        # Create day-based task dictionary
        day_task_dict = {}
        
        # Loop through all tasks and organize by day
        for _, task in calendar_tasks.iterrows():
            if pd.notna(task['due_date_parsed']):
                task_date = task['due_date_parsed'].date()
                if task_date.month == selected_month and task_date.year == selected_year:
                    day = task_date.day
                    if day not in day_task_dict:
                        day_task_dict[day] = []
                    day_task_dict[day].append(task)
        
        # Display the calendar grid with tasks
        for week in monthly_cal:
            week_cols = st.columns(7)
            for i, day in enumerate(week):
                with week_cols[i]:
                    if day != 0:
                        # Check if there are tasks for this day
                        day_has_tasks = day in day_task_dict
                        
                        if day_has_tasks:
                            day_tasks = day_task_dict[day]
                            task_count = len(day_tasks)
                            
                            # Day header styled based on whether it has tasks
                            background_color = "#d1e7dd" if day_has_tasks else "#f8f9fa"
                            st.markdown(f"<div style='text-align: center; font-weight: bold; background-color: {background_color}; padding: 8px; border-radius: 4px 4px 0 0;'>{day} ({task_count})</div>", unsafe_allow_html=True)
                            
                            # In expanded mode, show task details
                            if not st.session_state.calendar_collapsed:
                                # Container for tasks
                                st.markdown("<div style='border: 1px solid #d1e7dd; border-radius: 0 0 4px 4px; padding: 8px;'>", unsafe_allow_html=True)
                                
                                # Show tasks for this day
                                for task in day_tasks[:3]:  # Show up to 3 tasks
                                    # Get priority color for the task
                                    priority = task['priority'] if pd.notna(task['priority']) else "Medium"
                                    priority_color = get_priority_color(priority)
                                    
                                    # Format time if available
                                    time_text = f" {task['due_time']}" if pd.notna(task['due_time']) else ""
                                    
                                    # Show task with styling
                                    st.markdown(
                                        f"<div style='margin-bottom: 5px; padding: 6px; border-left: 3px solid {priority_color}; background-color: rgba(0,0,0,0.03); border-radius: 3px;'>"
                                        f"<strong style='font-size: 0.9em;'>{task['title'][:20]}</strong>"
                                        f"<div style='font-size: 0.75em; color: #666;'>{time_text} • {priority}</div>"
                                        f"</div>",
                                        unsafe_allow_html=True
                                    )
                                
                                # Show indicator if there are more tasks
                                if len(day_tasks) > 3:
                                    st.caption(f"+ {len(day_tasks) - 3} more tasks")
                                
                                # Close the container
                                st.markdown("</div>", unsafe_allow_html=True)
                            else:
                                # In collapsed mode, just show a colored bar to indicate tasks
                                priority_colors = [get_priority_color(task['priority']) for task in day_tasks if pd.notna(task['priority'])]
                                
                                if priority_colors:
                                    # Show a small color bar for each priority (up to 3)
                                    st.markdown("<div style='display: flex; gap: 2px; padding: 4px; border: 1px solid #d1e7dd; border-radius: 0 0 4px 4px;'>", unsafe_allow_html=True)
                                    for color in priority_colors[:3]:
                                        st.markdown(f"<div style='flex-grow: 1; height: 4px; background-color: {color};'></div>", unsafe_allow_html=True)
                                    st.markdown("</div>", unsafe_allow_html=True)
                                else:
                                    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                        else:
                            # Empty day
                            st.markdown(f"<div style='text-align: center; padding: 8px; border: 1px solid #e5e7eb; border-radius: 4px;'>{day}</div>", unsafe_allow_html=True)
                    else:
                        # Empty day (zero)
                        st.markdown("<div style='padding: 8px;'></div>", unsafe_allow_html=True)

# Add analytics section
if st.session_state.show_analytics:
    st.markdown("<a id='analytics'></a>", unsafe_allow_html=True)
    st.subheader("📊 Analytics")
    
    # Use cached analytics
    tasks = get_cached_tasks()
    analytics = generate_analytics(tasks)
    
    # Display metric cards
    metrics_cols = st.columns(4)
    with metrics_cols[0]:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{analytics['counts']['total']}</div>
                <div class="metric-label">Total Tasks</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with metrics_cols[1]:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{analytics['counts']['overdue']}</div>
                <div class="metric-label">Overdue Tasks</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with metrics_cols[2]:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{analytics['counts']['due_soon']}</div>
                <div class="metric-label">Due Soon (3 days)</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with metrics_cols[3]:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{analytics['counts']['by_status']['done']}</div>
                <div class="metric-label">Completed Tasks</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Display charts
    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.plotly_chart(analytics['status_chart'], use_container_width=True)
    
    with chart_cols[1]:
        st.plotly_chart(analytics['priority_chart'], use_container_width=True)

# User Profile Section
if 'show_profile' in st.session_state and st.session_state.show_profile:
    st.markdown("<a id='profile'></a>", unsafe_allow_html=True)
    
    # Create an attractive profile header
    st.markdown("""
        <div style="background: linear-gradient(to right, #4CAF50, #2196F3); 
                    color: white; 
                    padding: 20px; 
                    border-radius: 10px; 
                    margin-bottom: 20px; 
                    display: flex; 
                    align-items: center;">
            <h2 style="margin: 0; padding-left: 10px;">
                👤 User Profile Settings
            </h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Get current user profile
    user_profile = get_current_user_profile(st.session_state.username)
    
    if not user_profile:
        st.error("Could not load user profile")
    else:
        # Use columns for better layout
        profile_col1, profile_col2 = st.columns([1, 2])
        
        with profile_col1:
            # Profile card with user info
            st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    <div style="display: flex; flex-direction: column; align-items: center; margin-bottom: 15px;">
                        <div style="background-color: #4CAF50; color: white; border-radius: 50%; width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; margin-bottom: 15px; font-size: 32px; font-weight: bold;">
                            {user_profile['username'][0].upper()}
                        </div>
                        <div style="font-size: 24px; font-weight: bold; text-align: center;">{user_profile['username']}</div>
                    </div>
                    <div style="margin-top: 20px;">
                        <div style="margin-bottom: 10px;">
                            <span style="font-weight: bold;">Email:</span><br/>
                            <span>{user_profile['email'] or 'Not set'}</span>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <span style="font-weight: bold;">Member Since:</span><br/>
                            <span>{user_profile['created_date']}</span>
                        </div>
                        <div>
                            <span style="font-weight: bold;">Last Login:</span><br/>
                            <span>{user_profile['last_login']}</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        with profile_col2:
            # Profile edit form with improved styling
            st.markdown("""
                <h3 style="margin-bottom: 20px;">Edit Your Profile</h3>
            """, unsafe_allow_html=True)
            
            with st.form("edit_profile_form"):
                # Email field
                new_email = st.text_input("Email Address", 
                                        value=user_profile['email'] or "",
                                        help="Your contact email address")
                
                # Password section with explanation
                st.markdown("""
                    <h4 style="margin-top: 30px; margin-bottom: 10px;">Change Password</h4>
                    <p style="color: #666; margin-bottom: 20px; font-size: 14px;">
                        To keep your current password, leave these fields blank.
                    </p>
                """, unsafe_allow_html=True)
                
                new_password = st.text_input("New Password", 
                                          type="password", 
                                          help="Minimum 6 characters recommended")
                confirm_password = st.text_input("Confirm New Password", 
                                             type="password")
                
                # Submit button with better styling
                submit_col1, submit_col2 = st.columns([3, 1])
                with submit_col1:
                    update_button = st.form_submit_button("💾 Save Changes", 
                                                       use_container_width=True,
                                                       type="primary")
                with submit_col2:
                    cancel_button = st.form_submit_button("Cancel", 
                                                      use_container_width=True)
                
                if cancel_button:
                    st.session_state.show_profile = False
                    st.rerun()
                
                if update_button:
                    # Validate inputs
                    if new_password and new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        # Update profile
                        success, message = update_current_user_profile(
                            user_profile['id'],
                            email=new_email if new_email != user_profile['email'] else None,
                            password=new_password if new_password else None
                        )
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

# Add User Management section (only visible to admin) 