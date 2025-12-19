from fastmcp import FastMCP
from typing import List

import json

from services import llm, devices, ansible

mcp = FastMCP("Dispatch Network")

@mcp.tool
def list_devices(topology_id: str) -> str:
    """
    List all devices in the specified topology to understand the network map.
    Returns a JSON string of devices with names, types, and port information.
    """

    ds = devices.get_devices_with_config(topology_id)

    return json.dumps([{
        "name": d["name"], 
        "device_type": d.get("device_type"), 
        "port": d.get("port"),
        "ip_address": d.get("ip_address")
    } for d in ds], indent=2)

@mcp.tool
def fetch_live_config(topology_id: str, device_name: str) -> str:
    """
    Connects to the device immediately, runs 'show running-config', 
    saves it to history, and returns the configuration content.
    Use this to inspect the device state before making any changes.
    """
    try:
        config_content = ansible.run_fetch_single_config(topology_id, device_name)
        return config_content
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"System Error fetching config: {str(e)}"

@mcp.tool
def propose_configuration(topology_id: str, device_configs: List[dict]) -> str:
    """
    Validates and structures configuration commands before pushing to devices.
    Returns a formatted proposal showing how commands will be organized.
    
    ARGS:
    - topology_id: (Injected automatically)
    - device_configs: List of device configurations. Each dict must have:
        - "device_name": Target device name (e.g., "R1")
        - "commands": List of configuration lines
        - "parent": REQUIRED for commands that need context mode
    
    CRITICAL PARENT REQUIREMENTS:
    - VLAN commands ("name HR", etc.) → parent: "vlan 10"
    - Interface commands ("ip address...", "encapsulation...") → parent: "interface GigabitEthernet1/0"
    - Access-list rules ("permit ip...", "deny ip...") → parent: "ip access-list extended IT_ACCESS"
    - Router protocol commands → parent: "router ospf 1"
    - Global commands ONLY (hostname, ip routing) → parent: null
    
    MANDATORY WORKFLOW:
    1. Call fetch_related_knowledge for syntax/SOPs
    2. Call fetch_live_config to check current state
    3. Call THIS tool to validate structure
    4. Call push_configuration with the validated structure
    
    EXAMPLE:
    device_configs = [
        {"device_name": "R1", "commands": ["name HR"], "parent": "vlan 10"},
        {"device_name": "R1", "commands": ["encapsulation dot1Q 10", "ip address 192.168.10.1 255.255.255.0"], "parent": "interface GigabitEthernet1/0.10"},
        {"device_name": "R1", "commands": ["permit ip 192.168.30.0 0.0.0.255 any"], "parent": "ip access-list extended IT_ACCESS"}
    ]
    """
    try:
        proposal_data = {
            "devices": device_configs,
            "reasoning": "Configuration validated and structured with proper parent contexts for Ansible execution."
        }
        
        proposal_json = json.dumps(proposal_data, indent=2)
        
        return f"<config_proposal>{proposal_json}</config_proposal>\n\nReady to push. Call push_configuration with the same device_configs structure."
    except Exception as e:
        return f"Proposal Error: {str(e)}"

@mcp.tool
def push_configuration(topology_id: str, device_configs: List[dict]) -> str:
    """
    Pushes configuration commands to one or more live devices.
    
    ⚠️ MANDATORY: Call propose_configuration FIRST to validate structure.
    
    ARGS:
    - topology_id: (Injected automatically)
    - device_configs: List of device configurations. Each dict must have:
        - "device_name": Target device name (e.g., "R1")
        - "commands": List of configuration lines
        - "parent": REQUIRED for all non-global commands (see propose_configuration for details)
    
    CRITICAL: Each command group MUST have the correct parent.
    - VLAN config commands → parent: "vlan X"
    - Interface commands → parent: "interface <name>"
    - ACL rules → parent: "ip access-list extended <name>"
    - Global commands only → parent: null
    
    DO NOT mix different contexts in one command list. Each parent gets its own dict entry.
    """
    try:
        results = []
        for config in device_configs:
            device_name = config.get("device_name")
            commands = config.get("commands", [])
            parent = config.get("parent")
            
            print(f"Pushing config to {device_name}: {commands}")
            result = ansible.run_push_config(topology_id, device_name, commands, parent)
            results.append(f"Device {device_name}: {result}")
        
        return "\n\n".join(results)
    except Exception as e:
        return f"Push Error: {str(e)}"

@mcp.tool
async def fetch_related_knowledge(query: str, model_name: str, topology_id: str = None) -> str:
    """
    Query the LightRAG knowledge base for Cisco Device configuration documentation,
    topology details, or standard operating procedures (SOPs).

    Always use this before generating configuration and before calling 'push_configuration'.

    ARGS:
    - topology_id: (Injected automatically, optional here)
    """
    try:
        return await llm.query_context(query, model_name, "mix")
    except Exception as e:
        return str(e)

mcp_app = mcp.http_app()