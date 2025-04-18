import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

def generate_task_counts(tasks_df):
    """Generate basic task count metrics."""
    total_tasks = len(tasks_df)
    to_do_count = len(tasks_df[tasks_df['status'] == 'To Do'])
    in_progress_count = len(tasks_df[tasks_df['status'] == 'In Progress'])
    done_count = len(tasks_df[tasks_df['status'] == 'Done'])
    blocked_count = len(tasks_df[tasks_df['status'] == 'Blocked'])
    
    # Calculate overdue tasks
    today = date.today()
    overdue_count = len(tasks_df[pd.to_datetime(tasks_df['due_date']).dt.date < today])
    
    # Calculate tasks by priority
    critical_count = len(tasks_df[tasks_df['priority'] == 'Critical'])
    high_count = len(tasks_df[tasks_df['priority'] == 'High'])
    medium_count = len(tasks_df[tasks_df['priority'] == 'Medium'])
    low_count = len(tasks_df[tasks_df['priority'] == 'Low'])
    
    # Due soon tasks (next 3 days)
    due_soon = len(tasks_df[
        (pd.to_datetime(tasks_df['due_date']).dt.date >= today) &
        (pd.to_datetime(tasks_df['due_date']).dt.date <= today + pd.Timedelta(days=3))
    ])
    
    return {
        'total': total_tasks,
        'by_status': {
            'to_do': to_do_count,
            'in_progress': in_progress_count,
            'done': done_count,
            'blocked': blocked_count
        },
        'by_priority': {
            'critical': critical_count,
            'high': high_count,
            'medium': medium_count,
            'low': low_count
        },
        'overdue': overdue_count,
        'due_soon': due_soon
    }

def create_status_chart(tasks_df):
    """Create a pie chart showing task distribution by status."""
    status_counts = tasks_df['status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    
    # Define colors for statuses
    colors = {
        'To Do': '#3b82f6',
        'In Progress': '#f59e0b',
        'Done': '#10b981',
        'Blocked': '#ef4444'
    }
    
    # Create the pie chart
    fig = px.pie(
        status_counts, 
        values='Count', 
        names='Status',
        color='Status',
        color_discrete_map=colors,
        title="Tasks by Status"
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    return fig

def create_priority_chart(tasks_df):
    """Create a bar chart showing task distribution by priority."""
    priority_counts = tasks_df['priority'].value_counts().reset_index()
    priority_counts.columns = ['Priority', 'Count']
    
    # Sort by priority level
    priority_order = ['Critical', 'High', 'Medium', 'Low']
    priority_counts['Priority'] = pd.Categorical(
        priority_counts['Priority'], 
        categories=priority_order, 
        ordered=True
    )
    priority_counts = priority_counts.sort_values('Priority')
    
    # Define colors for priorities
    colors = {
        'Critical': '#ef4444',
        'High': '#f59e0b',
        'Medium': '#10b981',
        'Low': '#6b7280'
    }
    
    # Create the bar chart
    fig = px.bar(
        priority_counts,
        x='Priority',
        y='Count',
        color='Priority',
        color_discrete_map=colors,
        title="Tasks by Priority"
    )
    
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    return fig

def generate_analytics(tasks_df):
    """Generate all analytics for the dashboard."""
    counts = generate_task_counts(tasks_df)
    status_chart = create_status_chart(tasks_df)
    priority_chart = create_priority_chart(tasks_df)
    
    return {
        'counts': counts,
        'status_chart': status_chart,
        'priority_chart': priority_chart
    } 