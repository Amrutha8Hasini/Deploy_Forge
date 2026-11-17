"""
CPU and memory calculation for Docker containers.

Kept in its own file (without importing Docker) so it is easy to unit test.
"""


def calculate_stats(raw: dict) -> dict:
    """Convert Docker's raw statistics into CPU % and memory numbers.

    This is the same formula the `docker stats` command uses:
    CPU % = (container CPU time used / total system CPU time used) * number of CPUs * 100
    """
    cpu_stats = raw.get("cpu_stats") or {}
    precpu_stats = raw.get("precpu_stats") or {}
    cpu_delta = (cpu_stats.get("cpu_usage") or {}).get("total_usage", 0) - (
        precpu_stats.get("cpu_usage") or {}
    ).get("total_usage", 0)
    system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)
    online_cpus = cpu_stats.get("online_cpus") or len((cpu_stats.get("cpu_usage") or {}).get("percpu_usage") or []) or 1

    cpu_percent = 0.0
    if cpu_delta > 0 and system_delta > 0:
        cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0

    memory = raw.get("memory_stats") or {}
    # "cache"/"inactive_file" is file cache that can be freed, so subtract it
    cache = (memory.get("stats") or {}).get("inactive_file", (memory.get("stats") or {}).get("cache", 0))
    memory_used = max(memory.get("usage", 0) - cache, 0)
    memory_limit = memory.get("limit", 0)
    memory_percent = (memory_used / memory_limit * 100.0) if memory_limit else 0.0

    return {
        "cpu_percent": round(cpu_percent, 2),
        "memory_used_mb": round(memory_used / (1024 * 1024), 1),
        "memory_limit_mb": round(memory_limit / (1024 * 1024), 1),
        "memory_percent": round(memory_percent, 2),
    }
