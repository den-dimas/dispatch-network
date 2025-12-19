import ansible_runner

from utils.db import execute_read

from services import devices, topologies

from config import ANSIBLE_DIR, GET_CONFIG_PLAYBOOK, PUSH_CONFIG_PLAYBOOK

task_status = {}

def get_dynamic_inventory(topology_id: str):
    topologies = execute_read("SELECT * FROM topologies WHERE project_id = %s", (topology_id,))
    
    if not topologies:
        raise ValueError(f"Topology with ID {topology_id} not found")
    
    topology = topologies[0]
    device_list = execute_read("SELECT * FROM devices WHERE topology_id = %s AND device_type = 'Router'", (topology_id,))
    
    inventory = {
        "all": {
            "hosts": {},
            "vars": {
                "ansible_network_os": "cisco.ios.ios",
                "ansible_connection": "network_cli",
                "ansible_user": topology["username"],
                "ansible_password": topology["password"],
            }
        }
    }

    for device in device_list:
        inventory["all"]["hosts"][device['name']] = {
            "ansible_host": device['ip_address'],
        }
        
    return inventory

def get_device_inventory(topology_id: str, device_name: str):
    """Helper to generate inventory for a device"""
    topology = topologies.get_topology_detail(topology_id)
    
    if not topology:
        raise ValueError(f"Topology with id {topology_id} not found.")
    
    dev = devices.get_device_by_name(topology_id, device_name)

    if not dev:
        raise ValueError(f"Device {device_name} not found in topology {topology['name']}.")
    
    return {
        "all": {
            "hosts": {device_name: {"ansible_host": dev[0]["ip_address"]}},
            "vars": {
                "ansible_network_os": "cisco.ios.ios",
                "ansible_connection": "network_cli",
                "ansible_user": topology["username"],
                "ansible_password": topology["password"],
            }
        }
    }

def run_fetch_single_config(topology_id: str, device_name: str):
    """
    Runs 'get_config' playbook for a specific device, saves to DB, 
    and returns the content directly.
    """

    try:
        target = get_device_inventory(topology_id, device_name)
        runner = ansible_runner.run(
            private_data_dir=ANSIBLE_DIR,
            playbook=GET_CONFIG_PLAYBOOK,
            inventory=target,
        )
        
        for event in runner.events:
            if event.get('event') == 'runner_on_ok':
                event_data = event.get('event_data', {})
                task_name = event_data.get('task', '')
                hostname = event_data.get('host', '')
                
                if 'show running-config' in task_name:
                    task_result = event_data.get('res', {})
                    stdout = task_result.get('stdout', [])
                    
                    if stdout and len(stdout) > 0:
                        config_content = stdout[0]
                        
                        dev = devices.get_device_by_name(topology_id, hostname)[0]["device_id"]
                        if dev:
                            devices.insert_config_snapshot(dev, config_content)

                        return config_content
        
        return f"Error: No configuration found for device {device_name}"
    except Exception as e:
        print(f"Background Ansible Failed: {e}")
        return f"Error: {str(e)}"

def run_fetch_config(topology_id: str, task_id: str):
    """Helper to fetch running config in background"""
    try:
        inventory = get_dynamic_inventory(topology_id)
        total_hosts = len(inventory["all"]["hosts"])
        
        task_status[task_id]["message"] = f"Running ansible on {total_hosts} devices..."
        
        runner = ansible_runner.run(
            private_data_dir=ANSIBLE_DIR,
            playbook=GET_CONFIG_PLAYBOOK,
            inventory=inventory,
        )
        
        completed_count = 0
        
        if runner.status == 'successful' or runner.status == 'failed':
            for event in runner.events:
                if event.get('event') == 'runner_on_ok':
                    event_data = event.get('event_data', {})
                    task_name = event_data.get('task', '')
                    hostname = event_data.get('host', '')
                    
                    if 'show running-config' in task_name:
                        task_result = event_data.get('res', {})
                        stdout = task_result.get('stdout', [])
                        
                        if stdout and len(stdout) > 0:
                            config_content = stdout[0]
                            
                            dev = devices.get_device_by_name(topology_id, hostname)[0]["device_id"]
                            
                            if dev:
                                devices.insert_config_snapshot(dev, config_content)

                                completed_count += 1
                                task_status[task_id]["completed_devices"] = completed_count
                                task_status[task_id]["progress"] = int((completed_count / total_hosts) * 100)
                                task_status[task_id]["message"] = f"Completed {completed_count}/{total_hosts} devices"
            
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["progress"] = 100
            task_status[task_id]["message"] = f"Config refresh completed. {completed_count} devices updated."
        else:
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["message"] = f"Ansible job failed with status: {runner.status}"
            
    except Exception as e:
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["message"] = f"Error: {str(e)}"
        print(f"Background Ansible Failed: {e}")

def run_push_config(topology_id: str, device_name: str, commands: list, parent: str = None):
    """
    Helper to push running config synchronously.
    
    Args:
        commands: List of config lines (e.g., ["ip address 1.1.1.1..."])
        parent: Optional parent context (e.g., "interface Gi0/0"). 
                If None, commands are treated as global.
    """

    if not commands:
        raise ValueError("No commands provided to push.")

    payload = {
        "commands": commands
    }

    if parent:
        payload["name"] = parent

    target = get_device_inventory(topology_id, device_name)

    runner = ansible_runner.run(
        private_data_dir=ANSIBLE_DIR,
        playbook=PUSH_CONFIG_PLAYBOOK,
        inventory=target,
        extravars={
            "interface_config": payload 
        },
    )

    if runner.status != 'successful':
        error_msg = "Unknown error"
        if hasattr(runner, 'stdout') and hasattr(runner.stdout, 'read'):
            error_msg = runner.stdout.read()
        
        raise RuntimeError(f"Ansible Push Failed: {error_msg}")

    return {"status": "success", "device": device_name, "events": list(runner.events)}