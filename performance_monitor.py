#!/usr/bin/env python3
"""
Performance Monitor for Supervisor Agent
Adds detailed timing and performance metrics to track optimization improvements.
"""

import time
import asyncio
from typing import Dict, Any, List
from datetime import datetime

class PerformanceMonitor:
    """Performance monitoring for concurrent operations"""
    
    def __init__(self):
        self.start_time = None
        self.checkpoints = {}
        self.task_times = {}
    
    def start(self, operation_name: str = "main"):
        """Start timing an operation"""
        self.start_time = time.time()
        self.checkpoints[operation_name] = self.start_time
        print(f"⏱️ Performance Monitor: Started {operation_name}")
    
    def checkpoint(self, name: str):
        """Record a checkpoint"""
        current_time = time.time()
        self.checkpoints[name] = current_time
        if self.start_time:
            elapsed = current_time - self.start_time
            print(f"⏱️ Checkpoint {name}: {elapsed:.2f}s")
    
    def end_task(self, task_name: str, start_time: float):
        """Record task completion time"""
        end_time = time.time()
        duration = end_time - start_time
        self.task_times[task_name] = duration
        print(f"✅ Task {task_name} completed in {duration:.2f}s")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.start_time:
            return {"error": "No timing data"}
        
        total_time = time.time() - self.start_time
        
        return {
            "total_execution_time": total_time,
            "checkpoints": {k: v - self.start_time for k, v in self.checkpoints.items()},
            "task_times": self.task_times,
            "optimization_status": "enabled",
            "timestamp": datetime.now().isoformat()
        }

# Global performance monitor instance
perf_monitor = PerformanceMonitor()

async def optimized_concurrent_analysis(internet_search_task, data_pool_task):
    """
    Optimized concurrent analysis with performance monitoring
    
    Args:
        internet_search_task: Async task for internet search
        data_pool_task: Async task for data pool retrieval
        
    Returns:
        Tuple of (internet_search_result, data_pool_result)
    """
    print("🚀 Starting OPTIMIZED concurrent analysis...")
    perf_monitor.start("concurrent_analysis")
    
    try:
        # Execute both tasks concurrently with timeout
        internet_search_result, data_pool_result = await asyncio.wait_for(
            asyncio.gather(internet_search_task, data_pool_task),
            timeout=180  # 3 minute timeout
        )
        
        perf_monitor.checkpoint("concurrent_tasks_completed")
        
        print("✅ OPTIMIZED concurrent analysis completed successfully")
        return internet_search_result, data_pool_result
        
    except asyncio.TimeoutError:
        print("⏰ Concurrent analysis timeout reached")
        perf_monitor.checkpoint("timeout_reached")
        raise Exception("Concurrent analysis timeout")
    except Exception as e:
        print(f"❌ Concurrent analysis failed: {e}")
        perf_monitor.checkpoint("error_occurred")
        raise e

def get_performance_summary():
    """Get current performance summary"""
    return perf_monitor.get_summary()

def print_performance_summary():
    """Print formatted performance summary"""
    summary = perf_monitor.get_summary()
    
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"⏱️ Total Execution Time: {summary['total_execution_time']:.2f} seconds")
    print(f"🚀 Optimization Status: {summary['optimization_status']}")
    print(f"📅 Timestamp: {summary['timestamp']}")
    
    if summary['checkpoints']:
        print("\n🔍 Checkpoints:")
        for name, time in summary['checkpoints'].items():
            print(f"   {name}: {time:.2f}s")
    
    if summary['task_times']:
        print("\n📈 Task Performance:")
        for task, time in summary['task_times'].items():
            print(f"   {task}: {time:.2f}s")
    
    print("=" * 60)
