import re
from datetime import datetime, date

def validate_task_input(title, description, status, priority, due_date, due_time):
    """Validate task input data."""
    errors = []
    
    # Validate title
    if not title:
        errors.append("Title is required")
    elif len(title) > 100:
        errors.append("Title must be less than 100 characters")
    
    # Validate description (optional)
    if description and len(description) > 2000:
        errors.append("Description must be less than 2000 characters")
    
    # Validate status
    valid_statuses = ["To Do", "In Progress", "Done", "Blocked"]
    if status not in valid_statuses:
        errors.append(f"Status must be one of: {', '.join(valid_statuses)}")
    
    # Validate priority
    valid_priorities = ["Critical", "High", "Medium", "Low"]
    if priority not in valid_priorities:
        errors.append(f"Priority must be one of: {', '.join(valid_priorities)}")
    
    # Validate due date
    if due_date:
        try:
            if isinstance(due_date, str):
                parsed_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            else:
                parsed_date = due_date
                
            # Optionally check if date is not in the past
            today = date.today()
            if parsed_date < today:
                errors.append("Warning: Due date is in the past")
        except ValueError:
            errors.append("Due date must be in YYYY-MM-DD format")
    
    # Validate due time
    if due_time:
        try:
            if isinstance(due_time, str):
                datetime.strptime(due_time, '%H:%M')
        except ValueError:
            errors.append("Due time must be in HH:MM format")
    
    return errors

def sanitize_input(text):
    """Remove potentially harmful characters from input."""
    if not text:
        return ""
    
    # Remove any HTML/script tags
    text = re.sub(r'<[^>]*>', '', text)
    
    # Remove any SQL injection attempts
    text = text.replace("'", "''")
    
    return text

def validate_labels(labels):
    """Validate and normalize task labels."""
    if not labels:
        return ""
        
    # Split by comma and trim whitespace
    label_list = [label.strip() for label in labels.split(',')]
    
    # Remove empty labels and duplicates
    label_list = [label for label in label_list if label]
    label_list = list(set(label_list))
    
    # Validate each label
    valid_labels = []
    for label in label_list:
        if len(label) <= 20 and re.match(r'^[a-zA-Z0-9\-_]+$', label):
            valid_labels.append(label)
    
    return ','.join(valid_labels) 