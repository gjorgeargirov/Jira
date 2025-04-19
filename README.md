# Task Manager Pro

A full-featured task management application built with Streamlit that helps you organize, track, and analyze your tasks.

## Features

- Create, update, and delete tasks with detailed information
- Track task status (To Do, In Progress, Done, Blocked)
- Set priority levels (Critical, High, Medium, Low)
- Assign due dates and times with visual indicators
- Organize tasks with labels/tags
- Group tasks with parent-child relationships (subtasks)
- Filter and search tasks
- Visualize task analytics with charts and statistics
- Calendar view for date-based task planning
- User authentication system
- Responsive design for desktop and mobile

## Installation

1. Clone this repository
2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

To run the application, use the following command:
```bash
streamlit run app.py
```

The application will open in your default web browser at http://localhost:8501

## Development

### Project Structure
- `app.py` - Main application file
- `database.py` - Database operations for tasks
- `auth.py` - User authentication system
- `utils.py` - Utility functions and helpers
- `analytics.py` - Data analysis and visualization
- `validation.py` - Input validation
- `static/` - Static assets (JS, images)
- `tests/` - Unit and integration tests

### Testing
Run the tests using:
```bash
python -m unittest discover tests
```

## Usage Guide

### First-time Setup
1. Register a new account from the login page
2. Login with your credentials

### Adding Tasks
1. Use the sidebar form to add new tasks
2. Fill in required fields (title, priority, status)
3. Add optional details (description, due date, labels)
4. Create subtasks by selecting a parent task

### Managing Tasks
1. View all tasks in the main kanban board
2. Drag tasks between status columns to update
3. Click on a task to view details or edit
4. Use filters to focus on specific tasks

### Keyboard Shortcuts
- Ctrl+N: Create new task
- Ctrl+F: Focus search box
- Ctrl+V: Toggle view (Kanban/List)

### Analytics
1. Navigate to the Analytics tab
2. View task distribution by status and priority
3. Track completion rates and overdue tasks

## License

[MIT License](LICENSE) 