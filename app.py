import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import os
import plotly.express as px
import plotly.graph_objects as go
import calendar
from plotly.subplots import make_subplots
import json
from streamlit.components.v1 import html
import re

# Set page configuration
st.set_page_config(
    page_title="Task Manager Pro",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add keyboard shortcuts JavaScript
st.markdown("""
<script>
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'n') {  // Ctrl+N: New Task
        document.querySelector('[data-testid="stSidebar"]').click();
    } else if (e.ctrlKey && e.key === 'f') {  // Ctrl+F: Search
        document.querySelector('#task-search').focus();
    } else if (e.ctrlKey && e.key === 'v') {  // Ctrl+V: Toggle View
        document.querySelector('[data-testid="view-toggle"]').click();
    }
});
</script>
""", unsafe_allow_html=True)

# Custom CSS with improved styling
st.markdown("""
    <style>
    /* Color Variables */
    :root {
        --primary-color: #3b82f6;
        --primary-light: #dbeafe;
        --secondary-color: #8b5cf6;
        --success-color: #10b981;
        --warning-color: #f59e0b;
        --danger-color: #ef4444;
        --dark-color: #1f2937;
        --light-color: #f9fafb;
        --border-color: #e5e7eb;
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }

    /* Global Styles */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    h1, h2, h3 {
        font-weight: 600 !important;
        color: var(--dark-color) !important;
    }
    
    /* Page Layout */
    .main-content {
        max-width: 1400px;
        margin: 0 auto;
    }
    
    .section {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-color);
    }
    
    .section-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--border-color);
        color: var(--dark-color);
    }
    
    /* Header Styles */
    .app-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .app-header img {
        margin-right: 0.75rem;
    }
    
    /* Task Cards */
    .kanban-container {
        display: flex;
        gap: 1rem;
        overflow-x: auto;
        padding-bottom: 1rem;
    }
    
    .status-column {
        flex: 1;
        min-width: 280px;
        background: var(--light-color);
        border-radius: 8px;
        padding: 0.75rem;
        border: 1px solid var(--border-color);
    }
    
    .status-header {
        background: white;
        padding: 0.75rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        font-weight: 600;
        text-align: center;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-color);
    }
    
    .task-card {
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        margin: 0.75rem 0;
        background: white;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
    }
    
    .task-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }
    
    .task-card.task-urgent {
        border-left: 4px solid var(--danger-color);
    }
    
    .task-card.task-soon {
        border-left: 4px solid var(--warning-color);
    }
    
    .task-card.task-future {
        border-left: 4px solid var(--success-color);
    }
    
    .task-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }
    
    .task-title {
        font-weight: 600;
        color: var(--dark-color);
        margin: 0;
        font-size: 1rem;
    }
    
    .priority-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
        color: white;
    }
    
    .task-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
        color: #6b7280;
    }
    
    .due-date {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    
    .description {
        font-size: 0.9rem;
        line-height: 1.5;
        color: #4b5563;
        margin: 0.75rem 0;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
    }
    
    .description.expanded {
        -webkit-line-clamp: initial;
    }
    
    .labels {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
        margin-top: 0.5rem;
    }
    
    .label {
        background: #f3f4f6;
        color: #4b5563;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
    }
    
    /* Action Buttons */
    .action-buttons {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.75rem;
    }
    
    .action-button {
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        border: 1px solid var(--border-color);
        background: white;
        color: #374151;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    .action-button:hover {
        background: #f3f4f6;
        border-color: #d1d5db;
    }
    
    .action-button.primary {
        background: var(--primary-color);
        color: white;
        border-color: var(--primary-color);
    }
    
    .action-button.primary:hover {
        background: #2563eb;
    }
    
    .action-button.danger {
        background: white;
        color: var(--danger-color);
        border-color: var(--danger-color);
    }
    
    .action-button.danger:hover {
        background: #fee2e2;
    }
    
    /* Filters */
    .filters-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: var(--shadow-sm);
        margin-bottom: 1rem;
        border: 1px solid var(--border-color);
    }
    
    .filter-group {
        margin-bottom: 0.75rem;
    }
    
    .filter-label {
        font-weight: 500;
        margin-bottom: 0.25rem;
        display: block;
        font-size: 0.9rem;
    }
    
    /* Analytics */
    .metrics-container {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.25rem;
        border-radius: 8px;
        box-shadow: var(--shadow-sm);
        text-align: center;
        border: 1px solid var(--border-color);
    }
    
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--primary-color);
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #6b7280;
    }
    
    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: var(--shadow-sm);
        margin-bottom: 1rem;
        border: 1px solid var(--border-color);
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .metrics-container {
            grid-template-columns: 1fr;
        }
        
        .kanban-container {
            flex-direction: column;
        }
        
        .status-column {
            min-width: 100%;
        }
        
        .task-card {
            margin: 0.5rem 0;
            padding: 0.75rem;
        }
        
        .action-buttons {
            flex-wrap: wrap;
        }
    }
    
    /* Enhance form elements */
    .stTextInput > div > div {
        border-radius: 0.375rem !important;
    }
    
    .stButton > button {
        border-radius: 0.375rem !important;
        font-weight: 500;
    }
    
    .stDateInput > div > div > input {
        border-radius: 0.375rem !important;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 8px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 8px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #a1a1a1;
    }
    
    /* Keyboard shortcuts */
    .keyboard-shortcuts {
        margin-top: 2rem;
        padding: 1rem;
        background-color: var(--light-color);
        border-radius: 8px;
        font-size: 0.9rem;
        border: 1px solid var(--border-color);
    }
    
    kbd {
        background-color: #f3f4f6;
        border: 1px solid #d1d5db;
        border-radius: 3px;
        box-shadow: 0 1px 1px rgba(0, 0, 0, 0.2);
        color: #374151;
        display: inline-block;
        font-size: 0.8rem;
        line-height: 1;
        padding: 0.2rem 0.4rem;
        vertical-align: middle;
        margin: 0 0.2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Helper functions
def get_status_color(status):
    return {
        "To Do": "#3b82f6",  # Blue
        "In Progress": "#f59e0b",  # Amber
        "Done": "#10b981",  # Green
        "Blocked": "#ef4444"  # Red
    }.get(status, "#6b7280")  # Gray default

def get_priority_color(priority):
    return {
        "Critical": "#ef4444",  # Red
        "High": "#f59e0b",  # Amber
        "Medium": "#10b981",  # Green
        "Low": "#6b7280"  # Gray
    }.get(priority, "#6b7280")

def calculate_due_status(due_date_str, due_time_str=None):
    if pd.isna(due_date_str):
        return {"color": "#6b7280", "text": "", "days": None}
        
    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if isinstance(due_date_str, str) else due_date_str
        today = date.today()
        now = datetime.now()
        
        # Format for display with a single icon
        formatted_date = due_date.strftime('%d %b %Y')  # Format as "19 Apr 2025"
        
        if due_time_str and pd.notna(due_time_str):
            formatted_time = due_time_str
            due_datetime = datetime.combine(due_date, datetime.strptime(due_time_str, '%H:%M').time())
            time_diff = due_datetime - now
            
            if time_diff.total_seconds() < 0:
                return {"color": "#ef4444", "text": "Overdue", "days": abs(time_diff.days), "display": f"{formatted_time} • {formatted_date}"}
            elif due_date == today:
                hours_left = time_diff.total_seconds() / 3600
                if hours_left < 1:
                    minutes_left = int(time_diff.total_seconds() / 60)
                    return {"color": "#ef4444", "text": f"Due in {minutes_left} minutes!", "days": 0, "display": f"{formatted_time} • Today"}
                else:
                    return {"color": "#f59e0b", "text": f"Due in {int(hours_left)} hours", "days": 0, "display": f"{formatted_time} • Today"}
            else:
                days_until_due = (due_date - today).days
                if days_until_due <= 2:
                    return {"color": "#f59e0b", "text": f"Due in {days_until_due} days", "days": days_until_due, "display": f"{formatted_time} • {formatted_date}"}
                else:
                    return {"color": "#10b981", "text": f"Due in {days_until_due} days", "days": days_until_due, "display": f"{formatted_time} • {formatted_date}"}
        else:
            days_until_due = (due_date - today).days
            if days_until_due < 0:
                return {"color": "#ef4444", "text": "Overdue", "days": abs(days_until_due), "display": formatted_date}
            elif days_until_due == 0:
                return {"color": "#f59e0b", "text": "Due Today", "days": 0, "display": "Today"}
            elif days_until_due <= 2:
                return {"color": "#f59e0b", "text": f"Due in {days_until_due} days", "days": days_until_due, "display": formatted_date}
            else:
                return {"color": "#10b981", "text": f"Due in {days_until_due} days", "days": days_until_due, "display": formatted_date}
    except:
        return {"color": "#6b7280", "text": "", "days": None, "display": due_date_str}

def get_urgency_class(due_date_str, due_time_str=None):
    if not due_date_str:
        return ""
    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        today = date.today()
        days_until = (due_date - today).days
        
        if days_until < 0:
            return "task-urgent"
        elif days_until <= 2:
            return "task-soon"
        else:
            return "task-future"
    except:
        return ""

def create_calendar_view(tasks_df, year, month):
    # Create calendar matrix
    cal = calendar.monthcalendar(year, month)
    
    # Create figure with subplots for calendar
    fig = make_subplots(
        rows=len(cal) + 1,  # Add extra row for day names
        cols=7,
        subplot_titles=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] + [" " for _ in range(len(cal) * 7)],
        vertical_spacing=0.02,
        horizontal_spacing=0.01,
        specs=[[{"type": "table"}] * 7] + [[{"type": "scatter"}] * 7] * len(cal)
    )
    
    # Convert all due dates to datetime if not already
    if not pd.api.types.is_datetime64_dtype(tasks_df['due_date']):
        tasks_df['due_date'] = pd.to_datetime(tasks_df['due_date'], errors='coerce')
    
    # Filter for the specific month and year
    month_tasks = tasks_df[
        (tasks_df['due_date'].dt.month == month) &
        (tasks_df['due_date'].dt.year == year)
    ].copy()
    
    # Ensure we're working with task dates correctly
    month_tasks['day'] = month_tasks['due_date'].dt.day
    
    # For each day in the calendar
    for week_idx, week in enumerate(cal):
        for day_idx, day in enumerate(week):
            if day != 0:  # Skip empty days
                current_date = date(year, month, day)
                
                # Get tasks for this day
                day_tasks = month_tasks[month_tasks['day'] == day]
                
                # Background color based on whether there are tasks
                bg_color = "#e8f4f8" if not day_tasks.empty else "#d1e7dd"
                
                # Add cell background
                fig.add_shape(
                    type="rect",
                    x0=0, x1=1, y0=0, y1=1,
                    line=dict(color="#e1e4e8", width=1),
                    fillcolor=bg_color,
                    row=week_idx + 2,  # +2 because of header row
                    col=day_idx + 1
                )
                
                # Add day number
                fig.add_trace(
                    go.Scatter(
                        x=[0.1],
                        y=[0.9],
                        text=f"<b>{day}</b>",
                        mode="text",
                        textfont=dict(size=14),
                        hoverinfo="none",
                        showlegend=False
                    ),
                    row=week_idx + 2,
                    col=day_idx + 1
                )
                
                # Add tasks for this day
                if not day_tasks.empty:
                    # Create task text
                    task_items = []
                    for _, task in day_tasks.iterrows():
                        priority_color = get_priority_color(task['priority'])
                        time_text = f" {task['due_time']}" if pd.notna(task['due_time']) else ""
                        status_text = f" ({task['status']})" if pd.notna(task['status']) else ""
                        
                        task_items.append(
                            f"<span style='color:{priority_color};'>■</span> "
                            f"{task['title'][:15]}{'..' if len(task['title']) > 15 else ''}"
                            f"{time_text}{status_text}"
                        )
                    
                    # Join task items with line breaks
                    task_text = "<br>".join(task_items[:3])
                    if len(day_tasks) > 3:
                        task_text += f"<br>+ {len(day_tasks) - 3} more"
                    
                    # Add task list
                    fig.add_trace(
                        go.Scatter(
                            x=[0.1],
                            y=[0.7],
                            text=task_text,
                            mode="text",
                            textfont=dict(size=10),
                            hoverinfo="text",
                            hovertext="<br>".join([
                                f"{task['title']} - {task['priority']} - {task['status']}"
                                for _, task in day_tasks.iterrows()
                            ]),
                            showlegend=False
                        ),
                        row=week_idx + 2,
                        col=day_idx + 1
                    )
            else:
                # Add grey background for empty days
                fig.add_shape(
                    type="rect",
                    x0=0, x1=1, y0=0, y1=1,
                    line=dict(color="#e1e4e8", width=1),
                    fillcolor="#f8f9fa",
                    row=week_idx + 2,
                    col=day_idx + 1
                )
    
    # Update layout
    fig.update_layout(
        height=600,
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # Update axes
    fig.update_xaxes(showgrid=False, showticklabels=False, zeroline=False)
    fig.update_yaxes(showgrid=False, showticklabels=False, zeroline=False)
    
    # Add month/year title
    month_name = calendar.month_name[month]
    fig.update_layout(title=f"{month_name} {year}")
    
    return fig

# Database functions
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT,
                  status TEXT DEFAULT 'To Do',
                  priority TEXT,
                  created_date TEXT,
                  due_date TEXT,
                  due_time TEXT,
                  position INTEGER,
                  labels TEXT,
                  last_updated TEXT)''')
    
    conn.commit()
    conn.close()

def add_task(title, description, status, priority, due_date, due_time, labels=""):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Get the maximum position for the current status
    c.execute('SELECT MAX(position) FROM tasks WHERE status = ?', (status,))
    max_pos = c.fetchone()[0]
    position = 1 if max_pos is None else max_pos + 1
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Format the due date and time
    due_date_str = due_date if isinstance(due_date, str) else due_date.strftime('%Y-%m-%d')
    due_time_str = due_time if isinstance(due_time, str) else due_time.strftime('%H:%M')
    
    c.execute('''INSERT INTO tasks 
                 (title, description, status, priority, created_date, due_date, due_time, position, labels, last_updated)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (title, description, status, priority, now, due_date_str, due_time_str, position, labels, now))
    
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect('tasks.db')
    df = pd.read_sql_query('SELECT * FROM tasks', conn)
    conn.close()
    
    # Convert due_date to datetime for proper sorting
    df['due_date'] = pd.to_datetime(df['due_date'])
    df['due_time'] = df['due_time'].fillna('')
    
    # Create a combined datetime column for sorting
    df['sort_datetime'] = df.apply(
        lambda x: pd.to_datetime(f"{x['due_date'].strftime('%Y-%m-%d')} {x['due_time']}")
        if pd.notna(x['due_date']) and x['due_time']
        else (x['due_date'] if pd.notna(x['due_date']) else pd.Timestamp.max), 
        axis=1
    )
    
    # Sort the dataframe
    df = df.sort_values(
        by=['status', 'sort_datetime'],
        key=lambda x: pd.Categorical(x, categories=['To Do', 'In Progress', 'Blocked', 'Done'])
        if x.name == 'status' else x
    )
    
    # Format due_date back to string for display
    df['due_date'] = df['due_date'].dt.strftime('%Y-%m-%d')
    
    return df

def get_subtasks(task_id):
    conn = sqlite3.connect('tasks.db')
    df = pd.read_sql_query('SELECT * FROM tasks WHERE parent_id = ?', conn, params=[task_id])
    conn.close()
    return df

def update_task(task_id, title, description, status, priority, due_date, due_time, labels=""):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Format the due date and time
    due_date_str = due_date if isinstance(due_date, str) else due_date.strftime('%Y-%m-%d')
    due_time_str = due_time if isinstance(due_time, str) else due_time.strftime('%H:%M')
    
    c.execute('''UPDATE tasks 
                 SET title = ?, 
                     description = ?, 
                     status = ?,
                     priority = ?, 
                     due_date = ?,
                     due_time = ?,
                     labels = ?,
                     last_updated = ?
                 WHERE id = ?''',
              (title, description, status, priority, due_date_str, due_time_str, labels, now, task_id))
    
    conn.commit()
    conn.close()

def update_task_status(task_id, new_status):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Get the old status and position
    c.execute('SELECT status, position FROM tasks WHERE id = ?', (task_id,))
    old_status, old_position = c.fetchone()
    
    # Get the maximum position in the new status column
    c.execute('SELECT MAX(position) FROM tasks WHERE status = ?', (new_status,))
    max_pos = c.fetchone()[0]
    new_position = 1 if max_pos is None else max_pos + 1
    
    # Update positions of other tasks in the old status column
    c.execute('UPDATE tasks SET position = position - 1 WHERE status = ? AND position > ?', 
             (old_status, old_position))
    
    # Update the task's status and position
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('UPDATE tasks SET status = ?, position = ?, last_updated = ? WHERE id = ?', 
             (new_status, new_position, now, task_id))
    
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Get the status and position of the task to be deleted
    c.execute('SELECT status, position FROM tasks WHERE id = ?', (task_id,))
    status, position = c.fetchone()
    
    # Update positions of remaining tasks
    c.execute('UPDATE tasks SET position = position - 1 WHERE status = ? AND position > ?', 
             (status, position))
    
    # Delete the task
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Sidebar
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
            <img src="https://img.icons8.com/color/48/000000/task.png" width="32" style="margin-right: 0.5rem;">
            <h2 style="margin: 0; font-size: 1.5rem;">Task Management</h2>
        </div>
        <hr style="margin-bottom: 1.5rem;">
    """, unsafe_allow_html=True)
    
    # Determine if we're editing or adding
    is_editing = 'editing_task' in st.session_state and st.session_state.editing_task
    form_title = "✏️ Edit Task" if is_editing else "✨ Add New Task"
    
    # Get current task if editing
    current_task = None
    if is_editing:
        tasks_df = get_tasks()
        task_matches = tasks_df[tasks_df['id'] == st.session_state.editing_task]
        if not task_matches.empty:
            current_task = task_matches.iloc[0]
        else:
            st.error("Task not found!")
            st.session_state.editing_task = None
            st.rerun()
    
    with st.form("task_form", clear_on_submit=not is_editing):
        st.subheader(form_title)
        
        # Task Information
        st.markdown('<div style="font-weight: 500; margin-bottom: 0.5rem;">Basic Information</div>', unsafe_allow_html=True)
        
        new_title = st.text_input(
            "Title*", 
            value=current_task['title'] if current_task is not None else "",
            help="Enter a concise task title"
        )
        
        # Add parent task selection for subtasks
        all_tasks = get_tasks()
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
                    update_task(
                        current_task['id'],
                        new_title,
                        new_description,
                        new_status,
                        new_priority,
                        due_date_str,
                        due_time_str,
                        new_labels
                    )
                    st.success("✅ Task updated successfully!")
                    st.session_state.editing_task = None
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
    
    if st.button("📊 View Analytics", use_container_width=True):
        # Use anchor links to scroll to analytics section
        js = """
        <script>
            window.open('#analytics', '_self');
        </script>
        """
        st.markdown(js, unsafe_allow_html=True)
        
    # Add help information at the bottom
    with st.expander("ℹ️ Help & Tips", expanded=False):
        st.markdown("""
            ### Keyboard Shortcuts
            - `Ctrl+N`: Open sidebar to add a new task
            - `Ctrl+F`: Focus the search box
            - `Ctrl+V`: Toggle between Kanban and Calendar views
            
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
st.markdown("# 📋 Task Manager Pro", unsafe_allow_html=False)

# Combined search, filters and view toggles in one row
col1, col2, col3 = st.columns([5, 3, 2])

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
all_tasks = get_tasks()
original_task_count = len(all_tasks)

# Apply search filter separately
filtered_tasks_df = all_tasks.copy()
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
                        
                        # Show due date outside the expansion block (always visible)
                        if pd.notna(task['due_date']):
                            st.markdown(f"<span style='color: {due_status['color']}; font-size: 0.85em;'>⏱️ {due_status['display']} • <strong>{due_status['text']}</strong></span>", unsafe_allow_html=True)
                    
                    # Only show details and buttons if expanded, but NOT another due date
                    if st.session_state[expand_key]:
                        # Show description preview (but no due date here since we already show it above)
                        description = task['description'] if task['description'] else "No description provided."
                        st.caption(description)
                        
                        # Action buttons in a row
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("✏️ Edit", key=edit_key, use_container_width=True):
                                st.session_state.editing_task = task_id
                                st.rerun()
                        
                        with col2:
                            # Next logical status
                            next_status = {
                                "To Do": "In Progress",
                                "In Progress": "Done",
                                "Done": "To Do",
                                "Blocked": "In Progress"
                            }[status]
                            
                            if st.button(f"→ {next_status}", key=move_key, use_container_width=True):
                                update_task_status(task_id, next_status)
                                st.rerun()
                        
                        with col3:
                            if st.button("🗑️", key=delete_key, use_container_width=True):
                                delete_task(task_id)
                                st.rerun()
                    
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

# Add performance caching for database operations
@st.cache_data(ttl=5)  # Cache for 5 seconds
def get_cached_tasks():
    return get_tasks()

# Use the cached version for operations that don't need the most up-to-date data
def get_cached_analytics():
    tasks = get_cached_tasks()
    return generate_analytics(tasks) 