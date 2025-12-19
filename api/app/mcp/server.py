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
        - "commands": List of configuration lines (commands ONLY, NO parent command, NO leading spaces)
        - "parent": Context command or null for global
    
    CRITICAL STRUCTURE RULES:
    1. Each context gets its own separate dict entry
    2. The parent is the context-entering command (e.g., "interface GigabitEthernet1/0.10")
    3. Commands list contains ONLY sub-commands (e.g., ["encapsulation dot1Q 10"])
    4. DO NOT include the parent command in the commands list
    5. DO NOT add leading spaces to commands
    6. Global commands (hostname, access-list entries) use parent: null
    
    CONTEXT TYPES:
    - Interface config → parent: "interface GigabitEthernet1/0.10"
    - VLAN config → parent: "vlan 10"
    - Named ACL → parent: "ip access-list extended IT_ACCESS"
    - Router protocol → parent: "router ospf 1"
    - Global commands → parent: null
    
    MANDATORY WORKFLOW:
    1. Call fetch_related_knowledge for syntax/SOPs
    2. Call fetch_live_config to check current state
    3. Call THIS tool to validate structure
    4. Call push_configuration with the validated structure
    
    EXAMPLE - CORRECT:
    device_configs = [
        {"device_name": "R1", "parent": "vlan 10", "commands": ["name HR"]},
        {"device_name": "R1", "parent": "interface GigabitEthernet1/0.10", "commands": ["encapsulation dot1Q 10", "ip address 192.168.10.1 255.255.255.0"]},
        {"device_name": "R1", "parent": null, "commands": ["access-list 101 permit ip any any"]}
    ]
    
    EXAMPLE - WRONG (don't do this):
    device_configs = [
        {"device_name": "R1", "parent": null, "commands": ["interface Gi1/0.10", " encapsulation dot1Q 10"]}
    ]
    """
    try:
        errors = []
        for idx, config in enumerate(device_configs):
            device_name = config.get("device_name")
            commands = config.get("commands", [])
            parent = config.get("parent")
            
            if not device_name:
                errors.append(f"Entry {idx}: Missing device_name")
            if not commands:
                errors.append(f"Entry {idx}: No commands provided")
            
            for cmd in commands:
                if cmd.startswith(" ") or cmd.startswith("\t"):
                    errors.append(f"Entry {idx}: Command '{cmd}' has leading whitespace - remove it")
                if any(cmd.startswith(prefix) for prefix in ["interface ", "vlan ", "router ", "ip access-list "]):
                    errors.append(f"Entry {idx}: Command '{cmd}' looks like a parent command - move it to parent field")
        
        if errors:
            return "VALIDATION ERRORS:\n" + "\n".join(errors)
        
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
        - "commands": List of configuration lines (commands ONLY, NO parent command, NO leading spaces)
        - "parent": Context command (e.g., "interface GigabitEthernet1/0.10") or null for global
    
    STRUCTURE RULES:
    1. Each context gets its own separate dict in device_configs
    2. The parent is the context-entering command (e.g., "interface Gi1/0.10")
    3. Commands list contains ONLY the sub-commands (e.g., ["encapsulation dot1Q 10", "ip address ..."])
    4. DO NOT include the parent command in the commands list
    5. DO NOT add leading spaces to commands
    6. Global commands (hostname, access-list) use parent: null
    
    EXAMPLE - CORRECT:
    device_configs = [
        {"device_name": "R1", "parent": "interface GigabitEthernet1/0.10", "commands": ["encapsulation dot1Q 10", "ip address 192.168.10.1 255.255.255.0"]},
        {"device_name": "R1", "parent": null, "commands": ["access-list 101 permit ip any any"]}
    ]
    
    EXAMPLE - WRONG:
    device_configs = [{"device_name": "R1", "parent": null, "commands": ["interface Gi1/0.10", " encapsulation dot1Q 10"]}]
    """
    try:
        results = []
        for config in device_configs:
            device_name = config.get("device_name")
            commands = config.get("commands", [])
            parent = config.get("parent")
            
            if not device_name:
                return "Error: device_name is required in device_configs"
            if not commands:
                return f"Error: No commands provided for device {device_name}"
            
            print(f"Pushing to {device_name} [parent: {parent or 'global'}]: {commands}")
            result = ansible.run_push_config(topology_id, device_name, commands, parent)
            results.append(f"✓ {device_name} [{parent or 'global'}]: Success")
        
        return "\n".join(results)
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