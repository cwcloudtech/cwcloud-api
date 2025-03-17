import psutil

from psutil._common import bytes2human

def disk_usage():
    dd = psutil.disk_usage('/')
    div = (1024.0 ** 3)
    total_gb = dd.total / div
    used_gb = dd.used / div
    free_gb = dd.free / div
    percent_used = (used_gb / total_gb) * 100

    return {
        "total": total_gb,
        "used": used_gb,
        "free": free_gb,
        "percent": percent_used
    }

def virtual_memory():
    mem = psutil.virtual_memory()
    total = bytes2human(mem.total)
    available = bytes2human(mem.available)
    used = bytes2human(mem.used)
    percent_used = (mem.used / mem.total) * 100
    return {
        "total": total,
        "used": used,
        "available": available,
        "percent": percent_used,
    }

def swap_memory():
    sw = psutil.swap_memory()
    return {
        "total": bytes2human(sw.total),
        "used": bytes2human(sw.used),
        "free": bytes2human(sw.free),
        "percent": sw.percent
    }

def cpu():
    return {
        "percent": {
            "all": psutil.cpu_percent(interval=1),
            "percpu": psutil.cpu_percent(interval=1, percpu=True)
        },
        "count": {
            "all": psutil.cpu_count(),
            "with_logical": psutil.cpu_count(logical=False)
        },
        "times": {
            "all": psutil.cpu_times(),
            "percpu": psutil.cpu_times(percpu=True)
        }
    }

def all_metrics():
    return {
        "disk_usage": disk_usage(),
        "virtual_memory": virtual_memory(),
        "swap_memory": swap_memory(),
        "cpu": cpu()
    }
