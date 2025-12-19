from utils.db import execute_write, execute_read

def create_new_device(topology_id: str, device_id: str, name: str, device_type: str = None, port: int = None):
    q = """
    INSERT INTO devices (topology_id, device_id, name, device_type, port)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (device_id) DO UPDATE 
    SET name = EXCLUDED.name, device_type = EXCLUDED.device_type, port = EXCLUDED.port
    RETURNING device_id
    """

    return execute_write(q, (topology_id, device_id, name, device_type, port))

def get_device_by_name(topology_id: str, name: str):
    q = """
    SELECT * FROM devices
    WHERE topology_id = %s AND name = %s
    """

    return execute_read(q, (topology_id, name,))

def get_devices_with_config(topology_id: str):
    q = """
    SELECT d.device_id, d.topology_id, d.name, d.device_type, d.ip_address, d.port, d.created_at, (
        SELECT content FROM config_snapshots cs
        WHERE cs.device_id = d.device_id
        ORDER BY cs.created_at DESC
        LIMIT 1
    ) as latest_config
    FROM devices d
    WHERE d.topology_id = %s
    """

    return execute_read(q, (topology_id,))

def update_device_ip(topology_id: str, device_id: str, ip_address: str):
    q = """
    UPDATE devices SET ip_address = %s
    WHERE device_id = %s AND topology_id = %s
    RETURNING *
    """

    return execute_write(q, (ip_address, device_id, topology_id))

def insert_config_snapshot(device_id: str, config: str):
    q = """
    INSERT INTO config_snapshots (device_id, content)
    VALUES (%s, %s) RETURNING *
    """

    return execute_write(q, (device_id, config, ))