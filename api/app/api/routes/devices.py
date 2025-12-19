from fastapi import APIRouter, HTTPException

from services import gns3, devices


task_status = {}

router = APIRouter(prefix="/topologies", tags=["ansible", "topology"])

@router.get("/{topology_id}/devices")
async def get_devices(topology_id: str):
    gns_nodes = gns3.get_devices(topology_id)

    device_ids = set([n['node_id'] for n in gns_nodes])
    
    for n in gns_nodes:
        devices.create_new_device(
            topology_id, 
            n["node_id"], 
            n["name"],
            n.get("device_type"),
            n.get("port")
        )
    
    ds = devices.get_devices_with_config(topology_id)
    
    final = [d for d in ds if d["device_id"] in device_ids]

    return final

@router.patch("/{topology_id}/devices/{device_id}")
def update_device_ip(topology_id: str, device_id: str, body: dict):
    ip_address = body.get('ip_address')

    if not ip_address:
        raise HTTPException(status_code=400, detail="ip_address is required")
    
    try:
        result = devices.update_device_ip(topology_id, device_id, ip_address)
        
        if not result:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return {"status": "updated", "device_id": result}
    except Exception as e:
        error_msg = str(e)
        if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
            raise HTTPException(status_code=409, detail=f"IP address {ip_address} is already in use by another device")
        raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")