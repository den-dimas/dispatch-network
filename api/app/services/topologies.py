from utils.db import execute_write, execute_read

def get_topology_detail(topology_id: str):
    result = execute_read("SELECT * FROM topologies WHERE project_id = %s", (topology_id,))
    return result[0] if result else None

def create_new_topology(topology_id: str, name: str):
    q = """
    INSERT INTO topologies (project_id, name)
    VALUES (%s, %s)
    ON CONFLICT (project_id) DO UPDATE 
    SET name = EXCLUDED.name
    RETURNING *;
    """

    return execute_write(q, (topology_id, name,))

def update_user_topology(topology_id: str, username: str, password: str):
    q = """
    UPDATE topologies SET 
        username = %s,
        password = %s
    WHERE project_id = %s
    RETURNING project_id
    """

    return execute_write(q, (username, password, topology_id))