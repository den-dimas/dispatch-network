from fastapi import APIRouter, HTTPException, BackgroundTasks

import httpx

from models.domain import UserTopologyIn

from services import gns3, topologies, ansible, devices as devices_services

router = APIRouter(prefix="/topologies", tags=["ansible", "topology"])

@router.get("/")
async def get_topologies():
    """List all topologies/projects from GNS3 Server"""

    try:
        projects = gns3.get_project_lists()

        return projects
    except httpx.HTTPError as e:
        HTTPException(status_code=500, detail=e)


@router.get("/{topology_id}")
async def get_topology_detail(topology_id: str):
    gns_data = gns3.get_project_detail(topology_id)

    topologies.create_new_topology(gns_data["project_id"], gns_data["name"])

    result = topologies.get_topology_detail(topology_id)
    if not result:
        raise HTTPException(status_code=404, detail="Topology not found")
    
    return result

@router.patch("/{topology_id}")
async def update_user_topology(topology_id: str, user: UserTopologyIn):
    result = topologies.update_user_topology(topology_id, user.username, user.password)

    if not result:
        raise HTTPException(status_code=404, detail="Topology not found")
    
    return {"status": "updated", "topology_id": result}



@router.get("/{topology_id}/task/{task_id}")
def get_task_status(topology_id: str, task_id: str):
    """Get the status of a background task"""
    if task_id not in ansible.task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = ansible.task_status[task_id]
    if task["topology_id"] != topology_id:
        raise HTTPException(status_code=404, detail="Task not found for this topology")
    
    return task

@router.post("/{topology_id}/config/refresh")
def refresh_configs(topology_id: str, background_task: BackgroundTasks):
    """
    Trigger Ansible to fetch configs for ALL devices in this specific topology.
    """
    
    device_list = devices_services.get_devices_with_config(topology_id)

    if not device_list:
        raise HTTPException(status_code=400, detail="No devices found. Sync first.")
    
    routers = [d for d in device_list if d.get('device_type') == 'Router']
    valid_devices = [d for d in routers if d['ip_address']]
    if not valid_devices:
        raise HTTPException(status_code=400, detail="No routers with IP addresses found. Please set IP addresses for routers first.")
    
    import uuid
    task_id = str(uuid.uuid4())

    ansible.task_status[task_id] = {
        "status": "running",
        "topology_id": topology_id,
        "progress": 0,
        "total_devices": len(valid_devices),
        "completed_devices": 0,
        "message": "Starting config refresh..."
    }
    
    background_task.add_task(ansible.run_fetch_config, topology_id, task_id)

    return {"status": "queued", "task_id": task_id, "message": "Config refresh started in background"}


