CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DROP TABLE IF EXISTS config_snapshots;
DROP TABLE IF EXISTS devices;
DROP TABLE IF EXISTS chat_messages;
DROP TABLE IF EXISTS chat_sessions;
DROP TABLE IF EXISTS topologies;

CREATE TABLE IF NOT EXISTS topologies (
    project_id UUID PRIMARY KEY NOT NULL,
    
    username VARCHAR(255),
    password VARCHAR(255),
    
    name VARCHAR(255) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS devices (
    device_id UUID PRIMARY KEY NOT NULL,
    topology_id UUID REFERENCES topologies(project_id) 
        ON DELETE CASCADE
        ON UPDATE CASCADE,
        
    name VARCHAR(255) NOT NULL,
    device_type VARCHAR(50),
    ip_address VARCHAR(50),
    port INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS config_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(device_id) 
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    content TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topology_id UUID REFERENCES topologies(project_id) 
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    title VARCHAR(255),
    mode VARCHAR(50) DEFAULT 'agent',
    model VARCHAR(50) DEFAULT 'qwen',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) 
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    role VARCHAR(50),
    content TEXT,
    meta_data TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_devices_topology_id 
ON devices(topology_id);

CREATE INDEX IF NOT EXISTS idx_config_snapshots_device_created 
ON config_snapshots(device_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_topology_id 
ON chat_sessions(topology_id);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created 
ON chat_messages(session_id, created_at ASC);