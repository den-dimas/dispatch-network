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
def push_configuration(topology_id: str, device_configs: List[dict]) -> str:
    """
    Pushes configuration commands to live devices using Ansible.

    ARGS:
    - topology_id: (Injected automatically)
    - device_configs: List of configuration dictionaries.
    
    ### CONFIGURATION MODES & STRUCTURE
    
    1. **Global Configuration Mode** (Commands run directly in `config terminal`)
       - **Definition**: Commands that apply to the whole device.
       - **Structure**: `parent: null`
       - **Examples**: `hostname`, `ip routing`, `ip route ...`, `username ...`, `crypto key generate`
       - **JSON**: `{"device_name": "R1", "parent": null, "commands": ["hostname CORE-R1"]}`

    2. **Sub-Configuration Mode** (Interface, Router, Line, ACL)
       - **Definition**: Commands that require entering a specific section first.
       - **Structure**: `parent: "SECTION COMMAND"`
       - **Examples**: 
         - Interface: `parent: "interface Gi0/0"`, `commands: ["ip address ..."]`
         - OSPF: `parent: "router ospf 1"`, `commands: ["network ..."]`
         - Extended ACL: `parent: "ip access-list extended FILTER_WEB"`, `commands: ["permit tcp ..."]`
       - **JSON**: `{"device_name": "R1", "parent": "interface Gi0/0", "commands": ["no shutdown"]}`

    ### CRITICAL RULES
    1. **Do not nest parents**: If you need to configure an interface, the `parent` IS the interface command.
    2. **Clean Commands**: No leading spaces in `commands` list. Ansible handles indentation.
    3. **One Block Per Context**: Do not mix Interface commands and Global commands in the same dict entry. Create two separate entries.
    """
    try:
        results = []
        for config in device_configs:
            device_name = config.get("device_name")
            commands = config.get("commands", [])
            parent = config.get("parent")
            
            print(f"Pushing to {device_name} [parent: {parent or 'global'}]: {commands}")
            
            result = ansible.run_push_config(topology_id, device_name, commands, parent)
            
            results.append(f"{device_name} [{parent or 'global'}]: Success")
        
        return "\n".join(results)
    except Exception as e:
        return f"Push Error: {str(e)}"

@mcp.tool
async def fetch_related_knowledge(query: str, model_name: str, topology_id: str = None) -> str:
    """
    Query the LightRAG knowledge base for Cisco Device configuration documentation.
    
    CRITICAL: 
    - Use this tool BEFORE generating any configuration.
    - Use this to check syntax (e.g. "How to configure OSPF on Cisco IOS").
    - Use this to check SOPs (e.g. "Standard naming convention for WAN interfaces").
    """
    try:
        return await llm.query_context(query, model_name, "mix")
    except Exception as e:
        return str(e)

mcp_app = mcp.http_app()