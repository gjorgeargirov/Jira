import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import json
import base64
import os
import uuid
import time

# Create a directory for session tokens if it doesn't exist
SESSIONS_DIR = "sessions"
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

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
                  last_login TEXT,
                  is_admin INTEGER DEFAULT 0)''')
    
    # Check if 'is_admin' column exists
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    if 'is_admin' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    
    # Check if admin user exists
    c.execute("SELECT id, password FROM users WHERE username = 'admin'")
    admin_user = c.fetchone()
    
    # Admin password - hardcoded for reliability
    admin_pw = 'admin'
    hashed_admin_pw = hashlib.sha256(admin_pw.encode()).hexdigest()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not admin_user:
        # Create admin user if doesn't exist
        c.execute(
            "INSERT INTO users (username, password, email, created_date, last_login, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
            ('admin', hashed_admin_pw, 'admin@example.com', now, now, 1)
        )
        print("Admin user created")
    else:
        # Only update if password is different
        current_password = admin_user[1]
        if current_password != hashed_admin_pw:
            c.execute(
                "UPDATE users SET password = ?, is_admin = 1, last_login = ? WHERE username = 'admin'",
                (hashed_admin_pw, now)
            )
            print("Admin user password reset")
        else:
            # Just ensure admin flag is set without printing
            c.execute(
                "UPDATE users SET is_admin = 1 WHERE username = 'admin'"
            )
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_session_token():
    """Generate a unique session token."""
    return str(uuid.uuid4())

def save_session_token(username, token):
    """Save a session token to a file."""
    session_data = {
        "username": username,
        "created": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "expires": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Save to a file named after the token
    with open(os.path.join(SESSIONS_DIR, f"{token}.json"), "w") as f:
        json.dump(session_data, f)
    
    # Also store in browser using JavaScript
    js_code = f"""
    <script>
        // Store session token in localStorage
        try {{
            localStorage.setItem("taskmanager_session", "{token}");
            console.log("Session token saved to localStorage");
        }} catch (e) {{
            console.error("Error saving to localStorage:", e);
        }}
        
        // Also store as a cookie
        document.cookie = "taskmanager_session={token}; path=/; max-age={7*24*60*60}; SameSite=Lax";
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)
    
    return token

def load_session_token():
    """Try to load a session token from query params, localStorage, or cookie."""
    # First check if we already have a token in session state
    if "auth_token" in st.session_state and st.session_state.auth_token:
        return st.session_state.auth_token
    
    # Set up JavaScript to read from localStorage and cookies and pass to Streamlit
    js_code = """
    <script>
        function getSessionToken() {
            // Try localStorage first
            let token = "";
            try {
                token = localStorage.getItem("taskmanager_session");
            } catch (e) {
                console.error("Error reading from localStorage:", e);
            }
            
            // If not in localStorage, try cookies
            if (!token) {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.startsWith("taskmanager_session=")) {
                        token = cookie.substring("taskmanager_session=".length);
                        break;
                    }
                }
            }
            
            // Send token to Streamlit if found
            if (token) {
                window.parent.postMessage({
                    type: "streamlit:setComponentValue",
                    value: token
                }, "*");
            }
        }
        
        // Try immediately and after a delay
        getSessionToken();
        setTimeout(getSessionToken, 500);
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)
    
    # Check if the JavaScript sent us a token
    if "componentValue" in st.session_state:
        token = st.session_state.componentValue
        # Store it in our session state
        st.session_state.auth_token = token
        return token
    
    return None

def validate_session_token(token):
    """Check if a session token is valid and return the username."""
    if not token:
        return None
    
    token_file = os.path.join(SESSIONS_DIR, f"{token}.json")
    if not os.path.exists(token_file):
        return None
    
    try:
        with open(token_file, "r") as f:
            session_data = json.load(f)
        
        # Check if session is expired
        expiry = datetime.strptime(session_data["expires"], '%Y-%m-%d %H:%M:%S')
        if expiry < datetime.now():
            # Session expired, delete the file
            os.remove(token_file)
            return None
        
        return session_data["username"]
    except Exception as e:
        print(f"Error validating session: {str(e)}")
        return None

def clear_session_token(token):
    """Clear a session token."""
    if token:
        token_file = os.path.join(SESSIONS_DIR, f"{token}.json")
        if os.path.exists(token_file):
            os.remove(token_file)
    
    # Clear from browser
    js_code = """
    <script>
        // Clear from localStorage
        try {
            localStorage.removeItem("taskmanager_session");
        } catch (e) {
            console.error("Error removing from localStorage:", e);
        }
        
        // Clear cookie
        document.cookie = "taskmanager_session=; path=/; max-age=0";
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)
    
    # Clear from session state
    if "auth_token" in st.session_state:
        del st.session_state.auth_token
    if "componentValue" in st.session_state:
        del st.session_state.componentValue

def register_user(username, password, email=None):
    """Register a new user."""
    if not username or not password or not email:
        return False, "Username, password, and email are required"
    
    # Validate username (alphanumeric, 3-20 chars)
    if not (3 <= len(username) <= 20) or not username.isalnum():
        return False, "Username must be 3-20 alphanumeric characters"
    
    # Validate password (minimum 8 chars)
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Validate email format (simple check)
    if '@' not in email or '.' not in email:
        return False, "Please enter a valid email address"
        
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
    
    # Debug information - will show in the console but not to the user
    print(f"Attempting to authenticate user: {username}")
        
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        # Hash the provided password
        hashed_pw = hash_password(password)
        
        # Check credentials
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        
        if not user:
            print(f"User not found: {username}")
            return False
            
        stored_password = user[1]
        
        # Debug: Compare hashed passwords
        print(f"Input password hash: {hashed_pw}")
        print(f"Stored password hash: {stored_password}")
        
        if hashed_pw == stored_password:
            # Update last login time
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user[0]))
            conn.commit()
            print(f"Authentication successful for: {username}")
            return True
        else:
            print(f"Password mismatch for: {username}")
            return False
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return False
    finally:
        conn.close()

def login_required():
    """Check if user is logged in, if not show login page."""
    # Initialize authentication database only once per session
    if "auth_db_initialized" not in st.session_state:
        init_auth_db()
        st.session_state.auth_db_initialized = True
    
    # Initialize session state for authentication
    if "username" not in st.session_state:
        st.session_state.username = None
    
    # Initialize remembered username if not already set
    if "remembered_username" not in st.session_state:
        st.session_state.remembered_username = ""
    
    # Initialize show_login flag (True for login form, False for register form)
    if "show_login" not in st.session_state:
        st.session_state.show_login = True
    
    # Initialize admin panel flag
    if "show_admin_panel" not in st.session_state:
        st.session_state.show_admin_panel = False
    
    # Define functions to switch between forms
    def switch_to_register():
        st.session_state.show_login = False
        
    def switch_to_login():
        st.session_state.show_login = True
    
    # First check for existing session
    if st.session_state.username is None:
        token = load_session_token()
        if token:
            username = validate_session_token(token)
            if username:
                st.session_state.username = username
                # Auto-enable admin panel for admin users upon login
                if is_admin(username) and not st.session_state.show_admin_panel:
                    st.session_state.show_admin_panel = True
                    st.rerun()
    
    # If user is already logged in, check if admin and show admin panel
    if st.session_state.username:
        # Admin user flow - completely separate from regular app
        if is_admin(st.session_state.username):
            # Always show admin panel for admin users
            st.session_state.show_admin_panel = True
            
            # Display admin panel
            st.title("Admin Panel")
            admin_panel()
            
            # Add a logout button in the sidebar
            st.sidebar.title("Admin Actions")
            if st.sidebar.button("Logout"):
                logout_user()
            
            # Stop normal app flow when in admin panel
            return False
        
        # Regular user flow
        return True
    
    # Otherwise, show login page
    st.title("Task Manager Login")
    
    # Show either login or register based on session state
    if st.session_state.show_login:
        # Login Form
        # Add autocomplete attributes to help browsers save credentials
        st.markdown("""
        <style>
        /* Add autocomplete attributes to the username and password fields */
        [data-testid="stTextInput"] input:nth-of-type(1) {
            autocomplete: username;
        }
        [data-testid="stTextInput"] input[type="password"] {
            autocomplete: current-password;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", value=st.session_state.get("remembered_username", ""))
            password = st.text_input("Password", type="password")
            col1, col2 = st.columns(2)
            with col1:
                remember_me = st.checkbox("Remember me", value=True)
            with col2:
                remember_username = st.checkbox("Save credentials", value=True)
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                if authenticate_user(username, password):
                    # Save username in session state if requested
                    if remember_username:
                        st.session_state.remembered_username = username
                    else:
                        if "remembered_username" in st.session_state:
                            del st.session_state.remembered_username
                    
                    # Set session username
                    st.session_state.username = username
                    
                    # Create session token if remember me is checked
                    if remember_me:
                        token = generate_session_token()
                        save_session_token(username, token)
                        st.session_state.auth_token = token
                        
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        # Add a button to switch to registration
        st.button("Need an account? Register here", on_click=switch_to_register)
        
    else:
        # Register Form
        with st.form("register_form"):
            new_username = st.text_input("Username (3-20 alphanumeric characters)")
            new_email = st.text_input("Email (required)")
            new_password = st.text_input("Password (min 8 characters)", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            # Add a password strength indicator/helper text
            if new_password:
                if len(new_password) < 8:
                    st.warning("Password is too short (minimum 8 characters)")
                else:
                    st.success("Password length is good")
            
            submit_register = st.form_submit_button("Register")
            
            if submit_register:
                if not new_username or not new_password or not new_email:
                    st.error("Username, password, and email are required")
                elif len(new_username) < 3 or len(new_username) > 20 or not new_username.isalnum():
                    st.error("Username must be 3-20 alphanumeric characters")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long")
                elif '@' not in new_email or '.' not in new_email:
                    st.error("Please enter a valid email address")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    success, message = register_user(new_username, new_password, new_email)
                    if success:
                        st.success(message + " You can now login.")
                        # Set the remembered username to make login easier
                        st.session_state.remembered_username = new_username
                        # Switch to login form
                        st.session_state.show_login = True
                        st.rerun()
                    else:
                        st.error(message)
        
        # Add a button to switch back to login
        st.button("Already have an account? Login here", on_click=switch_to_login)
    
    # User is not authenticated
    return False

def login_page():
    """Alias for login_required for backward compatibility."""
    return login_required()

def logout_user():
    """Log out the user."""
    # Get the token first
    token = None
    if "auth_token" in st.session_state:
        token = st.session_state.auth_token
    
    # Clear user from session state
    if "username" in st.session_state:
        st.session_state.username = None
    
    # Reset admin panel flag
    if "show_admin_panel" in st.session_state:
        st.session_state.show_admin_panel = False
    
    # Clear the session token
    clear_session_token(token)
    
    st.rerun()

def get_all_users():
    """Get all users from the database."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT id, username, email, created_date, last_login, is_admin FROM users")
        users = c.fetchall()
        
        # Convert to list of dictionaries
        user_list = []
        for user in users:
            user_list.append({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'created_date': user[3],
                'last_login': user[4],
                'is_admin': user[5]
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

def is_admin(username):
    """Check if the user is an admin."""
    if not username:
        return False
        
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT is_admin FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        
        if result and result[0] == 1:
            return True
        return False
    except Exception as e:
        print(f"Error checking admin status: {str(e)}")
        return False
    finally:
        conn.close()

def admin_panel():
    """Admin panel for user management."""
    # Check if user is admin
    if not st.session_state.username or not is_admin(st.session_state.username):
        st.error("You do not have permission to access this page.")
        return False
    
    st.header("User Management")
    
    # Get all users
    users = get_all_users()
    
    # Display users in a table
    if users:
        # Convert to DataFrame for better display
        import pandas as pd
        users_df = pd.DataFrame(users)
        users_df = users_df[['id', 'username', 'email', 'created_date', 'last_login', 'is_admin']]
        users_df['is_admin'] = users_df['is_admin'].apply(lambda x: "Yes" if x == 1 else "No")
        
        st.dataframe(users_df)
        
        # User management section
        st.subheader("Manage User")
        
        # Select user to edit
        user_ids = [user['id'] for user in users]
        user_names = [user['username'] for user in users]
        selected_user_index = st.selectbox("Select User", range(len(user_ids)), format_func=lambda x: user_names[x])
        selected_user_id = user_ids[selected_user_index]
        
        # Get selected user
        selected_user = next((user for user in users if user['id'] == selected_user_id), None)
        
        if selected_user:
            # Edit user form
            with st.form("edit_user_form"):
                new_username = st.text_input("Username", value=selected_user['username'])
                new_email = st.text_input("Email", value=selected_user['email'] or "")
                new_password = st.text_input("New Password (leave blank to keep current)", type="password")
                is_admin_checkbox = st.checkbox("Admin", value=selected_user.get('is_admin', 0) == 1)
                
                col1, col2 = st.columns(2)
                with col1:
                    update_button = st.form_submit_button("Update User")
                with col2:
                    delete_button = st.form_submit_button("Delete User")
                
                if update_button:
                    # Convert checkbox to integer for database
                    admin_value = 1 if is_admin_checkbox else 0
                    
                    # First update the user details using the proper function
                    success, message = update_user(
                        selected_user_id,
                        username=new_username,
                        email=new_email,
                        password=new_password if new_password else None
                    )
                    
                    if success:
                        # Then update the admin status separately
                        conn = sqlite3.connect('users.db')
                        c = conn.cursor()
                        try:
                            c.execute("UPDATE users SET is_admin = ? WHERE id = ?", 
                                     (admin_value, selected_user_id))
                            conn.commit()
                            
                            # Force data refresh
                            st.success("User updated successfully!")
                            time.sleep(0.5)  # Small delay to ensure changes are committed
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating admin status: {str(e)}")
                        finally:
                            conn.close()
                    else:
                        st.error(message)
                
                if delete_button:
                    # Prevent deleting the currently logged-in user
                    if selected_user['username'] == st.session_state.username:
                        st.error("You cannot delete your own account!")
                    else:
                        success, message = delete_user(selected_user_id)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        
        # Add new user section
        st.subheader("Add New User")
        with st.form("add_user_form"):
            add_username = st.text_input("Username (3-20 alphanumeric characters)", key="add_username")
            add_email = st.text_input("Email", key="add_email")
            add_password = st.text_input("Password (min 8 characters)", type="password", key="add_password")
            add_is_admin = st.checkbox("Admin", key="add_is_admin")
            
            add_user_button = st.form_submit_button("Add User")
            
            if add_user_button:
                if not add_username or not add_password or not add_email:
                    st.error("Username, password, and email are required")
                elif len(add_username) < 3 or len(add_username) > 20 or not add_username.isalnum():
                    st.error("Username must be 3-20 alphanumeric characters")
                elif len(add_password) < 8:
                    st.error("Password must be at least 8 characters long")
                elif '@' not in add_email or '.' not in add_email:
                    st.error("Please enter a valid email address")
                else:
                    # Handle admin flag
                    conn = sqlite3.connect('users.db')
                    c = conn.cursor()
                    
                    try:
                        hashed_pw = hash_password(add_password)
                        admin_value = 1 if add_is_admin else 0
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        c.execute('''INSERT INTO users 
                                     (username, password, email, created_date, last_login, is_admin) 
                                     VALUES (?, ?, ?, ?, ?, ?)''', 
                                  (add_username, hashed_pw, add_email, now, now, admin_value))
                        
                        conn.commit()
                        st.success("User added successfully!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Username already exists!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                    finally:
                        conn.close()
    else:
        st.warning("No users found in the database.")
    
    return True

def reset_admin_password():
    """Reset the admin password to 'admin'."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Admin password
    admin_pw = 'admin'
    hashed_admin_pw = hashlib.sha256(admin_pw.encode()).hexdigest()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Update admin password
        c.execute(
            "UPDATE users SET password = ?, is_admin = 1, last_login = ? WHERE username = 'admin'",
            (hashed_admin_pw, now)
        )
        
        # Check if any rows were updated
        if c.rowcount == 0:
            # Admin doesn't exist, create it
            c.execute(
                "INSERT INTO users (username, password, email, created_date, last_login, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                ('admin', hashed_admin_pw, 'admin@example.com', now, now, 1)
            )
        
        conn.commit()
        return True, "Admin password reset to 'admin'"
    except Exception as e:
        conn.rollback()
        return False, f"Error resetting admin password: {str(e)}"
    finally:
        conn.close() 