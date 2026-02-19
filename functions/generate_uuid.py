import uuid


def generate_uuid_to_clipboard(root):
    value = str(uuid.uuid4())
    root.clipboard_clear()
    root.clipboard_append(value)
    root.update_idletasks()
    return value
