"""Tests for the CPU / memory calculation used by monitoring (Module 10)."""

from app.services.stats import calculate_stats


def test_cpu_and_memory_calculation():
    raw = {
        "cpu_stats": {"cpu_usage": {"total_usage": 2_000_000}, "system_cpu_usage": 20_000_000, "online_cpus": 4},
        "precpu_stats": {"cpu_usage": {"total_usage": 1_000_000}, "system_cpu_usage": 10_000_000},
        "memory_stats": {"usage": 60 * 1024 * 1024, "limit": 256 * 1024 * 1024, "stats": {"inactive_file": 10 * 1024 * 1024}},
    }
    stats = calculate_stats(raw)
    # (1,000,000 / 10,000,000) * 4 CPUs * 100 = 40 %
    assert stats["cpu_percent"] == 40.0
    assert stats["memory_used_mb"] == 50.0
    assert stats["memory_limit_mb"] == 256.0
    assert stats["memory_percent"] == round(50 / 256 * 100, 2)


def test_empty_stats_do_not_crash():
    stats = calculate_stats({})
    assert stats == {"cpu_percent": 0.0, "memory_used_mb": 0.0, "memory_limit_mb": 0.0, "memory_percent": 0.0}
