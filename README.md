# Task Manager (Jira-like Application)

A simple task management application built with Streamlit that helps you organize and track your daily tasks.

## Features

- Create new tasks with title, description, priority, and due date
- Update task status (To Do, In Progress, Done)
- Filter tasks by status
- Delete tasks
- Track creation and due dates
- Priority levels (High, Medium, Low)

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

The application will open in your default web browser.

## Usage

1. Use the sidebar to add new tasks
2. View all tasks in the main area
3. Filter tasks by status using the dropdown
4. Update task status or delete tasks using the buttons in each task card
5. Tasks are automatically saved to a SQLite database 