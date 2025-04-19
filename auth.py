import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import json
import base64

def init_auth_db():
    """Initialize the authentication database."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  email TEXT,
                  created_date TEXT,
                  last_login TEXT)''')
    
    # Create a default admin user if none exists
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        hashed_pw = hashlib.sha256('admin'.encode()).hexdigest()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute(
            "INSERT INTO users (username, password, email, created_date, last_login) VALUES (?, ?, ?, ?, ?)",
            ('admin', hashed_pw, 'admin@example.com', now, now)
        )
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, email=None):
    """Register a new user."""
    if not username or not password:
        return False, "Username and password are required"
        
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        # Check if username already exists
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            return False, "Username already exists"
            
        # Check if email already exists (if provided)
        if email:
            c.execute("SELECT id FROM users WHERE email = ?", (email,))
            if c.fetchone():
                return False, "Email already in use"
        
        # Hash the password
        hashed_pw = hash_password(password)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Insert the new user
        c.execute('''INSERT INTO users (username, password, email, created_date, last_login)
                     VALUES (?, ?, ?, ?, ?)''', 
                  (username, hashed_pw, email, now, now))
        
        conn.commit()
        return True, "User registered successfully"
    except Exception as e:
        conn.rollback()
        return False, f"Error during registration: {str(e)}"
    finally:
        conn.close()

def authenticate_user(username, password):
    """Authenticate a user."""
    if not username or not password:
        return False
        
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        # Hash the provided password
        hashed_pw = hash_password(password)
        
        # Check credentials
        c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_pw))
        user = c.fetchone()
        
        if user:
            # Update last login time
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user[0]))
            conn.commit()
            return True
        else:
            return False
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return False
    finally:
        conn.close()

def set_auth_cookie(username):
    """Set an authentication cookie to persist login across refreshes."""
    expiry = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    auth_data = {
        "username": username,
        "expiry": expiry
    }
    
    # Base64 encode the auth data for security
    cookie_value = base64.b64encode(json.dumps(auth_data).encode()).decode()
    
    # Set a Streamlit cookie that expires in 7 days
    js_code = f"""
    <script>
        document.cookie = "taskmanager_auth={cookie_value}; path=/; max-age={7*24*60*60}; SameSite=Lax";
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)

def get_auth_cookie():
    """Get authentication data from cookie if it exists."""
    # Streamlit doesn't have direct cookie access, so we use a JavaScript workaround
    cookie_container = st.empty()
    
    js_code = """
    <script>
        const getCookieValue = (name) => {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith(name + '=')) {
                    return cookie.substring(name.length + 1);
                }
            }
            return "";
        };
        
        // Get the auth cookie and pass it to Streamlit via session state
        const authCookie = getCookieValue("taskmanager_auth");
        if (authCookie) {
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: authCookie
            }, "*");
        }
    </script>
    """
    
    # Create a container to receive the cookie value via JavaScript
    cookie_container.markdown(js_code, unsafe_allow_html=True)
    
    # Try to get the cookie from session state
    if "taskmanager_auth" in st.session_state:
        try:
            cookie_value = st.session_state.taskmanager_auth
            auth_data = json.loads(base64.b64decode(cookie_value).decode())
            
            # Check if cookie is expired
            expiry = datetime.strptime(auth_data["expiry"], '%Y-%m-%d %H:%M:%S')
            if expiry > datetime.now():
                return auth_data["username"]
        except:
            pass
    
    return None

def clear_auth_cookie():
    """Clear the authentication cookie when logging out."""
    js_code = """
    <script>
        document.cookie = "taskmanager_auth=; path=/; max-age=0";
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)

def login_required():
    """Check if user is logged in, if not show login page."""
    # Initialize authentication database
    init_auth_db()
    
    # Initialize session state for authentication
    if "username" not in st.session_state:
        st.session_state.username = None
    
    # First check if there's a stored auth cookie
    if st.session_state.username is None:
        cookie_username = get_auth_cookie()
        if cookie_username:
            st.session_state.username = cookie_username
    
    # If user is already logged in, return True
    if st.session_state.username:
        return True
    
    # Otherwise, show login page
    st.title("Task Manager Login")
    
    # Create tabs for login and register
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    # Login tab
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            remember_me = st.checkbox("Remember me", value=True)
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                if authenticate_user(username, password):
                    st.session_state.username = username
                    
                    # Set auth cookie if remember me is checked
                    if remember_me:
                        set_auth_cookie(username)
                        
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    # Register tab
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email (optional)")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit_register = st.form_submit_button("Register")
            
            if submit_register:
                if not new_username or not new_password:
                    st.error("Username and password are required")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(new_username, new_password, new_email)
                    if success:
                        st.success(message + " You can now login.")
                    else:
                        st.error(message)
    
    # User is not authenticated
    return False

def login_page():
    """Alias for login_required for backward compatibility."""
    return login_required()

def logout_user():
    """Log out the user."""
    if "username" in st.session_state:
        st.session_state.username = None
    
    # Clear the auth cookie
    clear_auth_cookie()
    
    st.rerun()

def get_all_users():
    """Get all users from the database."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT id, username, email, created_date, last_login FROM users")
        users = c.fetchall()
        
        # Convert to list of dictionaries
        user_list = []
        for user in users:
            user_list.append({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'created_date': user[3],
                'last_login': user[4]
            })
            
        return user_list
    except Exception as e:
        print(f"Error getting users: {str(e)}")
        return []
    finally:
        conn.close()

def get_user(user_id):
    """Get a single user by ID."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT id, username, email, created_date, last_login FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'created_date': user[3],
                'last_login': user[4]
            }
        return None
    except Exception as e:
        print(f"Error getting user: {str(e)}")
        return None
    finally:
        conn.close()

def update_user(user_id, username=None, email=None, password=None):
    """Update user details."""
    if not user_id:
        return False, "User ID is required"
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        # Check if user exists
        c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not c.fetchone():
            return False, "User not found"
        
        # Check if username already exists (if changing username)
        if username:
            c.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
            if c.fetchone():
                return False, "Username already exists"
        
        # Check if email already exists (if changing email)
        if email:
            c.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
            if c.fetchone():
                return False, "Email already in use"
        
        # Update fields that are not None
        updates = []
        params = []
        
        if username:
            updates.append("username = ?")
            params.append(username)
        
        if email:
            updates.append("email = ?")
            params.append(email)
        
        if password:
            updates.append("password = ?")
            params.append(hash_password(password))
        
        if not updates:
            return False, "No updates provided"
        
        # Build the query
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        params.append(user_id)
        
        # Execute update
        c.execute(query, params)
        conn.commit()
        
        return True, "User updated successfully"
    except Exception as e:
        conn.rollback()
        return False, f"Error updating user: {str(e)}"
    finally:
        conn.close()

def delete_user(user_id):
    """Delete a user by ID."""
    if not user_id:
        return False, "User ID is required"
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        # Check if user exists
        c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not c.fetchone():
            return False, "User not found"
        
        # Delete the user
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        
        return True, "User deleted successfully"
    except Exception as e:
        conn.rollback()
        return False, f"Error deleting user: {str(e)}"
    finally:
        conn.close()

def get_current_user_profile(username):
    """Get profile data for the currently logged in user."""
    if not username:
        return None
        
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT id, username, email, created_date, last_login FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'created_date': user[3],
                'last_login': user[4]
            }
        return None
    except Exception as e:
        print(f"Error getting user profile: {str(e)}")
        return None
    finally:
        conn.close()

def update_current_user_profile(user_id, email=None, password=None):
    """Update the current user's profile."""
    if not user_id:
        return False, "User ID is required"
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        # Check if user exists
        c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not c.fetchone():
            return False, "User not found"
        
        # Update fields that are not None
        updates = []
        params = []
        
        if email is not None:
            # Check if email already exists (if changing email)
            c.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
            if c.fetchone():
                return False, "Email already in use"
            updates.append("email = ?")
            params.append(email)
        
        if password:
            updates.append("password = ?")
            params.append(hash_password(password))
        
        if not updates:
            return False, "No updates provided"
        
        # Build the query
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        params.append(user_id)
        
        # Execute update
        c.execute(query, params)
        conn.commit()
        
        return True, "Profile updated successfully"
    except Exception as e:
        conn.rollback()
        return False, f"Error updating profile: {str(e)}"
    finally:
        conn.close() 