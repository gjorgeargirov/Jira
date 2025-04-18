import pandas as pd
import calendar
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def get_status_color(status):
    """Return color code for a given task status."""
    return {
        "To Do": "#3b82f6",  # Blue
        "In Progress": "#f59e0b",  # Amber
        "Done": "#10b981",  # Green
        "Blocked": "#ef4444"  # Red
    }.get(status, "#6b7280")  # Gray default

def get_priority_color(priority):
    """Return color code for a given task priority."""
    return {
        "Critical": "#ef4444",  # Red
        "High": "#f59e0b",  # Amber
        "Medium": "#10b981",  # Green
        "Low": "#6b7280"  # Gray
    }.get(priority, "#6b7280")

def calculate_due_status(due_date_str, due_time_str=None):
    """Calculate and format the due status of a task."""
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
    """Return CSS class based on task urgency."""
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
    """Create a calendar visualization with tasks."""
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