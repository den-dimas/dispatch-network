from fastapi import HTTPException
import httpx

from config import GNS_URL

def get_project_lists():
    try:
        with httpx.Client() as client:
            response = client.get(f"{GNS_URL}/projects")

            response.raise_for_status()

            return response.json()
    except httpx.HTTPError as e:
        return []
    
def get_project_detail(topology_id: str):
    try:
        with httpx.Client() as client:
            response = client.get(f"{GNS_URL}/projects/{topology_id}")
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Topology not found in GNS3")
            
            response.raise_for_status()
            
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"GNS3 Error: {str(e)}")
    
def get_devices(topology_id: str):
    try:
        with httpx.Client() as client:
            response = client.get(f"{GNS_URL}/projects/{topology_id}/nodes")
            
            response.raise_for_status()
            
            data = response.json()

            filtered = []
            for n in data:
                node_type = n.get('node_type')
                if node_type in ['dynamips', 'iou']:
                    device_type = 'Router' if node_type == 'dynamips' else 'Switch'
                    filtered.append({
                        'node_id': n['node_id'],
                        'name': n['name'],
                        'device_type': device_type,
                        'port': n.get('console')
                    })
            return filtered
    except httpx.HTTPError:
        return []