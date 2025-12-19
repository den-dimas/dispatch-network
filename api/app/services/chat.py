from utils.db import execute_write, execute_read

def get_chat_sessions_by_topology(topology_id: str):
    query = """
    SELECT * FROM chat_sessions
    WHERE topology_id = %s
    ORDER BY created_at DESC
    """
    return execute_read(query, (topology_id,))

def delete_chat_session_by_id(session_id: str):
    query = """
    DELETE FROM chat_sessions
    WHERE id = %s RETURNING id
    """
    return execute_write(query, (session_id,))

def get_chat_history_by_session(session_id: str, topology_id: str):
    check = execute_read(
        "SELECT id FROM chat_sessions WHERE id = %s AND topology_id = %s",
        (session_id, topology_id)
    )
    if not check:
        return None
    
    query = """
    SELECT role, content, created_at 
    FROM chat_messages 
    WHERE session_id = %s 
    ORDER BY created_at ASC
    """
    return execute_read(query, (session_id,))

def create_chat_session(topology_id: str, title: str, mode: str = 'agent', model: str = 'qwen'):
    return execute_write(
        "INSERT INTO chat_sessions (topology_id, title, mode, model) VALUES (%s, %s, %s, %s) RETURNING id",
        (topology_id, title, mode, model)
    )

def get_conversation_history(session_id: str, limit_pairs: int = None):
    query = "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY created_at "
    
    if limit_pairs is not None:
        query += f"DESC LIMIT {limit_pairs * 2}"
        history_rows = execute_read(query, (session_id,))
        history_rows = list(reversed(history_rows))
    else:
        query += "ASC"
        history_rows = execute_read(query, (session_id,))
    
    return [{"role": r["role"], "content": r["content"]} for r in history_rows]

def save_chat_message(session_id: str, role: str, content: str):
    execute_write(
        "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
        (session_id, role, content)
    )

def check_topology_exists(topology_id: str):
    topos = execute_read(
        "SELECT name FROM topologies WHERE project_id = %s",
        (topology_id,)
    )
    return bool(topos)

def rename_chat_session(session_id: str, new_title: str):
    return execute_write(
        "UPDATE chat_sessions SET title = %s WHERE id = %s RETURNING id",
        (new_title, session_id)
    )
