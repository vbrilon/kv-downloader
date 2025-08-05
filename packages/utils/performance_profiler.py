"""
Performance Profiling System for Karaoke Automation
Provides multi-tier timing analysis with detailed logging
"""

import time
import logging
import json
import os
import threading
from pathlib import Path
from functools import wraps
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class PerformanceProfiler:
    """
    Multi-tier performance profiling system
    
    Provides System → Component → Method → Operation level timing analysis
    with memory usage tracking and detailed logging capabilities
    """
    
    def __init__(self, enabled=False, enable_memory=True, enable_detailed_logging=True):
        self.enabled = enabled
        self.enable_memory = enable_memory and PSUTIL_AVAILABLE  # Disable memory tracking if psutil unavailable
        self.enable_detailed_logging = enable_detailed_logging
        
        # DEBUG: Print profiler initialization state
        print(f"🔍 PROFILER INIT: enabled={enabled}, detailed_logging={enable_detailed_logging}")
        logging.info(f"🔍 PROFILER INIT: enabled={enabled}, detailed_logging={enable_detailed_logging}")
        
        # Performance data storage
        self.timing_data = {}
        self.operation_counts = {}
        self.memory_snapshots = []
        self.session_start_time = time.time()
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Warn if memory tracking disabled due to missing psutil
        if enable_memory and not PSUTIL_AVAILABLE:
            logging.warning("🔍 Performance profiling: psutil not available - memory tracking disabled")
        
        # Setup logging
        if self.enabled:
            self._setup_performance_logging()
    
    def _setup_performance_logging(self):
        """Setup dedicated performance logging"""
        # Create performance logs directory
        perf_logs_dir = Path("logs/performance")
        perf_logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = perf_logs_dir / f"performance_{timestamp}.log"
        
        # Setup performance logger
        self.perf_logger = logging.getLogger('performance')
        self.perf_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.perf_logger.handlers[:]:
            self.perf_logger.removeHandler(handler)
        
        # Add file handler
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('%(asctime)s - PERF - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.perf_logger.addHandler(handler)
        
        # Prevent propagation to avoid duplicate console output
        self.perf_logger.propagate = False
        
        logging.info(f"🔍 Performance profiling enabled - logs: {self.log_file}")
        self.perf_logger.info("Performance profiling session started")
    
    def profile_timing(self, operation_name: str, component: str = None, tier: str = "method"):
        """
        Decorator for timing method execution
        
        Args:
            operation_name: Name of the operation being timed
            component: Component/package name (e.g., 'track_management', 'download_management')  
            tier: Profiling tier ('system', 'component', 'method', 'operation')
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                # Create hierarchical operation key
                if component:
                    operation_key = f"{component}.{operation_name}"
                else:
                    operation_key = operation_name
                
                start_time = time.time()
                start_memory = self._get_memory_usage() if self.enable_memory else None
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    end_time = time.time()
                    end_memory = self._get_memory_usage() if self.enable_memory else None
                    duration = end_time - start_time
                    
                    self._record_timing(
                        operation_key=operation_key,
                        tier=tier,
                        duration=duration,
                        start_memory=start_memory,
                        end_memory=end_memory,
                        success=success,
                        error=error,
                        func_name=func.__name__
                    )
                
                return result
            return wrapper
        return decorator
    
    def profile_selenium_operation(self, operation_type: str, timeout_tracking=False, retry_tracking=False):
        """
        Specialized decorator for Selenium operations with additional context
        
        Args:
            operation_type: Type of selenium operation ('element_wait', 'click_operation', 'page_navigation')
            timeout_tracking: Track timeout-related metrics
            retry_tracking: Track retry attempt metrics
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                operation_key = f"selenium.{operation_type}"
                start_time = time.time()
                
                # Extract timeout from kwargs if present
                timeout_value = kwargs.get('timeout', 'default')
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    duration = time.time() - start_time
                    
                    # Additional selenium-specific context
                    context = {
                        'timeout': timeout_value,
                        'func_name': func.__name__
                    }
                    
                    self._record_selenium_timing(
                        operation_key=operation_key,
                        duration=duration,
                        success=success,
                        error=error,
                        context=context
                    )
                
                return result
            return wrapper
        return decorator
    
    def record_operation_start(self, operation_name: str, context: Dict = None):
        """Manually record operation start for complex flows"""
        if not self.enabled:
            return None
        
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        
        with self._lock:
            if 'manual_operations' not in self.timing_data:
                self.timing_data['manual_operations'] = {}
            
            self.timing_data['manual_operations'][operation_id] = {
                'name': operation_name,
                'start_time': time.time(),
                'start_memory': self._get_memory_usage() if self.enable_memory else None,
                'context': context or {}
            }
        
        return operation_id
    
    def record_operation_end(self, operation_id: str, success: bool = True, error: str = None, context: Dict = None):
        """Manually record operation end"""
        if not self.enabled or not operation_id:
            return
        
        end_time = time.time()
        
        with self._lock:
            if ('manual_operations' in self.timing_data and 
                operation_id in self.timing_data['manual_operations']):
                
                op_data = self.timing_data['manual_operations'][operation_id]
                duration = end_time - op_data['start_time']
                
                # Complete operation record
                op_data.update({
                    'end_time': end_time,
                    'duration': duration,
                    'end_memory': self._get_memory_usage() if self.enable_memory else None,
                    'success': success,
                    'error': error,
                    'end_context': context or {}
                })
                
                if self.enable_detailed_logging:
                    self.perf_logger.info(f"MANUAL_OP: {op_data['name']} - {duration:.4f}s - {'SUCCESS' if success else 'FAILED'}")
    
    def _record_timing(self, operation_key: str, tier: str, duration: float, 
                      start_memory: float, end_memory: float, success: bool, 
                      error: str, func_name: str):
        """Record timing data with thread safety"""
        with self._lock:
            if operation_key not in self.timing_data:
                self.timing_data[operation_key] = {
                    'tier': tier,
                    'calls': [],
                    'total_calls': 0,
                    'total_duration': 0.0,
                    'success_count': 0,
                    'error_count': 0
                }
            
            call_data = {
                'timestamp': time.time(),
                'duration': duration,
                'success': success,
                'error': error,
                'func_name': func_name
            }
            
            if self.enable_memory and start_memory and end_memory:
                call_data.update({
                    'start_memory_mb': start_memory,
                    'end_memory_mb': end_memory,
                    'memory_delta_mb': end_memory - start_memory
                })
            
            # Update aggregated data
            data = self.timing_data[operation_key]
            data['calls'].append(call_data)
            data['total_calls'] += 1
            data['total_duration'] += duration
            data['success_count'] += 1 if success else 0
            data['error_count'] += 1 if not success else 0
            
            # Track operation counts
            if operation_key not in self.operation_counts:
                self.operation_counts[operation_key] = 0
            self.operation_counts[operation_key] += 1
        
        # Detailed logging
        if self.enable_detailed_logging:
            memory_info = ""
            if self.enable_memory and start_memory and end_memory:
                delta = end_memory - start_memory
                memory_info = f" - Memory: {start_memory:.1f}MB → {end_memory:.1f}MB (Δ{delta:+.1f}MB)"
            
            status = "SUCCESS" if success else f"FAILED: {error}"
            self.perf_logger.info(f"{tier.upper()}: {operation_key} - {duration:.4f}s - {status}{memory_info}")
        
        # DEBUG: Also print to console to verify timing is being recorded
        if self.enabled:
            print(f"🔍 PERF DEBUG: {operation_key} - {duration:.4f}s - {'SUCCESS' if success else 'FAILED'}")
            logging.info(f"🔍 PERF DEBUG: {operation_key} - {duration:.4f}s - {'SUCCESS' if success else 'FAILED'}")
    
    def _record_selenium_timing(self, operation_key: str, duration: float, 
                               success: bool, error: str, context: Dict):
        """Record Selenium-specific timing data"""
        with self._lock:
            if 'selenium_operations' not in self.timing_data:
                self.timing_data['selenium_operations'] = {}
            
            if operation_key not in self.timing_data['selenium_operations']:
                self.timing_data['selenium_operations'][operation_key] = {
                    'calls': [],
                    'total_calls': 0,
                    'total_duration': 0.0,
                    'success_count': 0,
                    'error_count': 0
                }
            
            call_data = {
                'timestamp': time.time(),
                'duration': duration,
                'success': success,
                'error': error,
                'context': context
            }
            
            # Update data
            data = self.timing_data['selenium_operations'][operation_key]
            data['calls'].append(call_data)
            data['total_calls'] += 1
            data['total_duration'] += duration
            data['success_count'] += 1 if success else 0
            data['error_count'] += 1 if not success else 0
        
        # Detailed logging
        if self.enable_detailed_logging:
            status = "SUCCESS" if success else f"FAILED: {error}"
            timeout_info = f" (timeout: {context.get('timeout', 'default')})" if 'timeout' in context else ""
            self.perf_logger.info(f"SELENIUM: {operation_key} - {duration:.4f}s - {status}{timeout_info}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        if not PSUTIL_AVAILABLE:
            return 0.0
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)  # Convert to MB
        except:
            return 0.0
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        if not self.enabled:
            return "Performance profiling was not enabled"
        
        report_lines = []
        total_session_time = time.time() - self.session_start_time
        
        report_lines.append("="*80)
        report_lines.append("🔍 PERFORMANCE PROFILING REPORT")
        report_lines.append("="*80)
        report_lines.append(f"Session Duration: {total_session_time:.2f}s")
        report_lines.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # System-level summary
        report_lines.append("📊 TIMING SUMMARY BY TIER")
        report_lines.append("-" * 50)
        
        tier_summaries = {}
        for op_key, data in self.timing_data.items():
            if op_key in ['manual_operations', 'selenium_operations']:
                continue
            
            tier = data.get('tier', 'unknown')
            if tier not in tier_summaries:
                tier_summaries[tier] = {'total_time': 0.0, 'operations': 0}
            
            tier_summaries[tier]['total_time'] += data['total_duration']
            tier_summaries[tier]['operations'] += data['total_calls']
        
        for tier, summary in tier_summaries.items():
            report_lines.append(f"{tier.upper():12}: {summary['total_time']:8.2f}s ({summary['operations']} operations)")
        
        report_lines.append("")
        
        # Top slowest operations
        report_lines.append("🐌 TOP 10 SLOWEST OPERATIONS")
        report_lines.append("-" * 50)
        
        # Calculate average duration for each operation
        op_averages = []
        for op_key, data in self.timing_data.items():
            if op_key in ['manual_operations', 'selenium_operations']:
                continue
            if data['total_calls'] > 0:
                avg_duration = data['total_duration'] / data['total_calls']
                op_averages.append((op_key, avg_duration, data['total_calls'], data['total_duration']))
        
        # Sort by average duration descending
        op_averages.sort(key=lambda x: x[1], reverse=True)
        
        for i, (op_key, avg_duration, calls, total_duration) in enumerate(op_averages[:10]):
            report_lines.append(f"{i+1:2d}. {op_key:40} | Avg: {avg_duration:6.3f}s | Calls: {calls:3d} | Total: {total_duration:6.2f}s")
        
        return "\n".join(report_lines)
    
    def save_detailed_report(self, filename: str = None) -> str:
        """Save detailed performance data to JSON file"""
        if not self.enabled:
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/performance/detailed_performance_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Prepare detailed report data
        report_data = {
            'session_info': {
                'start_time': self.session_start_time,
                'end_time': time.time(),
                'total_duration': time.time() - self.session_start_time,
                'generated_at': datetime.now().isoformat()
            },
            'timing_data': self.timing_data,
            'operation_counts': self.operation_counts,
            'memory_snapshots': self.memory_snapshots if self.enable_memory else []
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logging.info(f"📁 Detailed performance report saved: {filename}")
            return filename
        except Exception as e:
            logging.error(f"Failed to save performance report: {e}")
            return None


# Global profiler instance
_global_profiler: Optional[PerformanceProfiler] = None


def get_profiler() -> PerformanceProfiler:
    """Get the global profiler instance"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler(enabled=False)
    return _global_profiler


def initialize_profiler(enabled: bool = False, enable_memory: bool = True, enable_detailed_logging: bool = True):
    """Initialize global profiler with specified settings"""
    global _global_profiler
    _global_profiler = PerformanceProfiler(
        enabled=enabled, 
        enable_memory=enable_memory, 
        enable_detailed_logging=enable_detailed_logging
    )
    return _global_profiler


def profile_timing(operation_name: str, component: str = None, tier: str = "method"):
    """Convenience decorator using global profiler"""
    return get_profiler().profile_timing(operation_name, component, tier)


def profile_selenium(operation_type: str, timeout_tracking=False, retry_tracking=False):
    """Convenience decorator for Selenium operations using global profiler"""
    return get_profiler().profile_selenium_operation(operation_type, timeout_tracking, retry_tracking)