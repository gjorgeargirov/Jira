import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st

def init_db():
    """Initialize the database with required tables."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Check if tasks table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    table_exists = c.fetchone() is not None
    
    if not table_exists:
        # Create table with username field
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
                      parent_id INTEGER,
                      last_updated TEXT,
                      username TEXT,
                      FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE CASCADE)''')
    else:
        # Check if username column exists and add it if not
        c.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in c.fetchall()]
        if 'username' not in columns:
            c.execute("ALTER TABLE tasks ADD COLUMN username TEXT")
            print("Added username column to tasks table")
    
    conn.commit()
    conn.close()

def add_task(title, description, status, priority, due_date, due_time, labels="", parent_id=None):
    """Add a new task to the database."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    try:
        # Get current username from session state
        username = st.session_state.username if hasattr(st.session_state, 'username') else None
        
        # Get the maximum position for the current status and user
        if username:
            c.execute('SELECT MAX(position) FROM tasks WHERE status = ? AND username = ?', (status, username))
        else:
            c.execute('SELECT MAX(position) FROM tasks WHERE status = ?', (status,))
        max_pos = c.fetchone()[0]
        position = 1 if max_pos is None else max_pos + 1
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Format the due date and time
        due_date_str = due_date if isinstance(due_date, str) else due_date.strftime('%Y-%m-%d')
        due_time_str = due_time if isinstance(due_time, str) else due_time.strftime('%H:%M')
        
        c.execute('''INSERT INTO tasks 
                    (title, description, status, priority, created_date, due_date, due_time, position, labels, parent_id, last_updated, username)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (title, description, status, priority, now, due_date_str, due_time_str, position, labels, parent_id, now, username))
        
        task_id = c.lastrowid
        conn.commit()
        return task_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_tasks():
    """Retrieve all tasks from the database for the current user."""
    conn = sqlite3.connect('tasks.db')
    try:
        # Get current username from session state
        username = st.session_state.username if hasattr(st.session_state, 'username') else None
        
        if username:
            # Filter tasks by username
            df = pd.read_sql_query('SELECT * FROM tasks WHERE username = ? OR username IS NULL', conn, params=[username])
        else:
            # If no user is logged in, show all tasks (or none, depending on your security model)
            df = pd.read_sql_query('SELECT * FROM tasks', conn)
        
        # Handle empty dataframe case
        if df.empty:
            return df
            
        # Convert due_date to datetime for proper sorting
        df['due_date'] = pd.to_datetime(df['due_date'], errors='coerce')
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
    except Exception as e:
        print(f"Error retrieving tasks: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_subtasks(task_id):
    """Retrieve subtasks for a given parent task ID."""
    conn = sqlite3.connect('tasks.db')
    try:
        # Get current username from session state
        username = st.session_state.username if hasattr(st.session_state, 'username') else None
        
        if username:
            # Filter by username and parent_id
            df = pd.read_sql_query('SELECT * FROM tasks WHERE parent_id = ? AND (username = ? OR username IS NULL)', 
                                  conn, params=[task_id, username])
        else:
            df = pd.read_sql_query('SELECT * FROM tasks WHERE parent_id = ?', conn, params=[task_id])
        return df
    except Exception as e:
        print(f"Error retrieving subtasks: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def update_task(task_id, title, description, status, priority, due_date, due_time, labels=""):
    """Update an existing task in the database."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Format the due date and time
    due_date_str = due_date if isinstance(due_date, str) else due_date.strftime('%Y-%m-%d')
    due_time_str = due_time if isinstance(due_time, str) else due_time.strftime('%H:%M')
    
    # Get current username from session state to ensure users can only update their own tasks
    username = st.session_state.username if hasattr(st.session_state, 'username') else None
    
    if username:
        # Only update if the task belongs to the user or has no user
        c.execute('''UPDATE tasks 
                    SET title = ?, 
                        description = ?, 
                        status = ?,
                        priority = ?, 
                        due_date = ?,
                        due_time = ?,
                        labels = ?,
                        last_updated = ?,
                        username = ?
                    WHERE id = ? AND (username = ? OR username IS NULL)''',
                (title, description, status, priority, due_date_str, due_time_str, labels, now, username, task_id, username))
    else:
        # Standard update without user restriction (should be limited in real-world apps)
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
    """Update a task's status and position in the database."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Get current username from session state
    username = st.session_state.username if hasattr(st.session_state, 'username') else None
    
    # Get the old status and position
    if username:
        c.execute('SELECT status, position FROM tasks WHERE id = ? AND (username = ? OR username IS NULL)', (task_id, username))
    else:
        c.execute('SELECT status, position FROM tasks WHERE id = ?', (task_id,))
    
    result = c.fetchone()
    if not result:
        conn.close()
        return  # Task not found or not owned by user
        
    old_status, old_position = result
    
    # Get the maximum position in the new status column for the current user
    if username:
        c.execute('SELECT MAX(position) FROM tasks WHERE status = ? AND (username = ? OR username IS NULL)', (new_status, username))
    else:
        c.execute('SELECT MAX(position) FROM tasks WHERE status = ?', (new_status,))
    
    max_pos = c.fetchone()[0]
    new_position = 1 if max_pos is None else max_pos + 1
    
    # Update positions of other tasks in the old status column
    if username:
        c.execute('UPDATE tasks SET position = position - 1 WHERE status = ? AND position > ? AND (username = ? OR username IS NULL)', 
                 (old_status, old_position, username))
    else:
        c.execute('UPDATE tasks SET position = position - 1 WHERE status = ? AND position > ?', 
                 (old_status, old_position))
    
    # Update the task's status and position
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if username:
        # Ensure task ownership or unassigned
        c.execute('UPDATE tasks SET status = ?, position = ?, last_updated = ?, username = ? WHERE id = ? AND (username = ? OR username IS NULL)', 
                 (new_status, new_position, now, username, task_id, username))
    else:
        c.execute('UPDATE tasks SET status = ?, position = ?, last_updated = ? WHERE id = ?', 
                 (new_status, new_position, now, task_id))
    
    conn.commit()
    conn.close()

def delete_task(task_id):
    """Delete a task from the database."""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Get current username from session state
    username = st.session_state.username if hasattr(st.session_state, 'username') else None
    
    try:
        # Get the status and position of the task to be deleted
        if username:
            c.execute('SELECT status, position FROM tasks WHERE id = ? AND (username = ? OR username IS NULL)', (task_id, username))
        else:
            c.execute('SELECT status, position FROM tasks WHERE id = ?', (task_id,))
        
        result = c.fetchone()
        if not result:
            return  # Task not found or not owned by user
            
        status, position = result
        
        # Update positions of remaining tasks
        if username:
            c.execute('UPDATE tasks SET position = position - 1 WHERE status = ? AND position > ? AND (username = ? OR username IS NULL)', 
                    (status, position, username))
        else:
            c.execute('UPDATE tasks SET position = position - 1 WHERE status = ? AND position > ?', 
                    (status, position))
        
        # Delete the task
        if username:
            c.execute('DELETE FROM tasks WHERE id = ? AND (username = ? OR username IS NULL)', (task_id, username))
        else:
            c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        
        conn.commit()
    except Exception as e:
        print(f"Error deleting task: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

# Cache functionality
def get_cached_tasks():
    """Return all tasks from the database (for caching)."""
    return get_tasks()

def get_cached_analytics(tasks):
    """Generate analytics from cached tasks."""
    return tasks 