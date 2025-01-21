# sysinfo_server.py

"""
Small MCP server that provides system information to the client so that the client can make intelligent decisions about what packages to install.
"""
from mcp.server.fastmcp import FastMCP
import platform
import psutil
import GPUtil
import os
import json
import GPUtil

mcp = FastMCP("SystemInfo")

def _get_gpu_info() -> dict:
    """Internal function to get GPU information.
    
    Returns:
        dict: GPU information or error message
    """
    gpu_info = []
    try:
        gpus = GPUtil.getGPUs()
        for gpu in gpus:
            gpu_info.append({
                "id": gpu.id,
                "uuid": gpu.uuid,
                "name": gpu.name,
                "load_percentage": gpu.load * 100,
                "memory": {
                    "total_mb": gpu.memoryTotal,
                    "used_mb": gpu.memoryUsed,
                    "free_mb": gpu.memoryFree,
                    "utilization_percentage": gpu.memoryUtil * 100
                },
                "driver": gpu.driver,
                "serial": gpu.serial,
                "display_mode": gpu.display_mode,
                "display_active": gpu.display_active
            })
        
        if not gpu_info:
            return {"error": "No NVIDIA GPUs found in the system"}
            
        return {"gpus": gpu_info}
        
    except Exception as e:
        return {"error": f"Could not get GPU information: {str(e)}"}

@mcp.tool()
def get_system_info() -> str:
    """Get detailed information about the system.

    This tool provides comprehensive information about the system's hardware,
    operating system, and resources.

    Returns:
        A JSON string containing system information including:
        - CPU details (cores, threads, architecture)
        - GPU details (if NVIDIA GPUs are present)
        - Memory usage and capacity
        - Operating system details
        - Python environment details
        - Storage information
        - Network interfaces

    Examples:
        "What are my system specifications?"
        "Show me my CPU and GPU information"
        "What GPUs are available in my system?"
    """
    try:
        # CPU Information
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "cpu_frequency": {
                "current": psutil.cpu_freq().current if hasattr(psutil.cpu_freq(), 'current') else None,
                "min": psutil.cpu_freq().min if hasattr(psutil.cpu_freq(), 'min') else None,
                "max": psutil.cpu_freq().max if hasattr(psutil.cpu_freq(), 'max') else None
            },
            "cpu_usage_percent": psutil.cpu_percent(interval=1)
        }

        # Memory Information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "free": memory.free,
            "percent_used": memory.percent,
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent
            }
        }

        # OS Information
        os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation()
        }

        # Disk Information
        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
            except (PermissionError, OSError):
                continue

        # Network Information
        network_info = []
        for interface, addresses in psutil.net_if_addrs().items():
            interface_info = {
                "interface": interface,
                "addresses": []
            }
            for addr in addresses:
                addr_info = {
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast if hasattr(addr, 'broadcast') else None
                }
                interface_info["addresses"].append(addr_info)
            network_info.append(interface_info)

        # Combine all information
        system_info = {
            "cpu": cpu_info,
            "gpu": _get_gpu_info(),  # Use the shared GPU info function
            "memory": memory_info,
            "os": os_info,
            "disks": disk_info,
            "network": network_info,
            "timestamp": psutil.boot_time()
        }

        # Convert bytes to GB for better readability
        def bytes_to_gb(bytes_value):
            return round(bytes_value / (1024**3), 2)

        # Format memory values
        system_info["memory"]["total_gb"] = bytes_to_gb(memory.total)
        system_info["memory"]["available_gb"] = bytes_to_gb(memory.available)
        system_info["memory"]["used_gb"] = bytes_to_gb(memory.used)
        system_info["memory"]["free_gb"] = bytes_to_gb(memory.free)

        # Format disk values
        for disk in system_info["disks"]:
            disk["total_gb"] = bytes_to_gb(disk["total"])
            disk["used_gb"] = bytes_to_gb(disk["used"])
            disk["free_gb"] = bytes_to_gb(disk["free"])

        return json.dumps(system_info, indent=2)

    except Exception as e:
        return f"Error getting system information: {str(e)}"

@mcp.tool()
def get_nvidia_gpu_info() -> str:
    """Get detailed information about available NVIDIA GPUs.
    
    This tool uses GPUtil to get comprehensive information about all NVIDIA GPUs
    in the system, including their utilization and memory status.
    
    Returns:
        A JSON string containing GPU information including:
        - Device ID and UUID
        - GPU name and driver version
        - Memory capacity and usage
        - Current load/utilization
        - Display information
        
    Examples:
        "Show me available GPUs"
        "What's my GPU memory usage?"
        "List all GPU specifications"
    """
    return json.dumps(_get_gpu_info(), indent=2)

def run_sysinfo_server():
    """Entry point for the system information MCP server"""
    mcp.run()