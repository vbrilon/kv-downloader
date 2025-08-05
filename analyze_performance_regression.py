#!/usr/bin/env python3
"""
Quick Performance Regression Analysis Script
Demonstrates the A/B testing capabilities for isolating performance regression
"""

import sys
import logging
from pathlib import Path

# Setup path for imports
sys.path.append(str(Path(__file__).parent))

from packages.utils import (
    BASELINE_CONFIGURATIONS, 
    PerformanceBaselineTester,
    run_ab_test,
    quick_regression_test
)

def main():
    """Run performance regression analysis"""
    
    print("🔍 KARAOKE AUTOMATION - PERFORMANCE REGRESSION ANALYSIS")
    print("=" * 60)
    
    # Show available baselines
    print("\n📋 Available Baseline Configurations:")
    for name, config in BASELINE_CONFIGURATIONS.items():
        print(f"  {name:15}: {config.description}")
    
    print(f"\n🎯 Key Configuration Differences:")
    print(f"   CURRENT (suspected regression source):")
    current = BASELINE_CONFIGURATIONS['current']
    print(f"     - Solo delays: {current.solo_activation_delay}s/{current.solo_activation_delay_simple}s/{current.solo_activation_delay_complex}s")
    print(f"     - Download monitoring: {current.download_monitoring_initial_wait}s initial wait, {current.download_check_interval}s intervals")
    
    print(f"\n   PRE-OPTIMIZATION (baseline):")
    pre_opt = BASELINE_CONFIGURATIONS['pre_optimization'] 
    print(f"     - Solo delays: {pre_opt.solo_activation_delay}s/{pre_opt.solo_activation_delay_simple}s/{pre_opt.solo_activation_delay_complex}s")
    print(f"     - Download monitoring: {pre_opt.download_monitoring_initial_wait}s initial wait, {pre_opt.download_check_interval}s intervals")
    
    print(f"\n🔬 REGRESSION ANALYSIS COMMANDS:")
    print(f"   Full A/B test (pre-optimization vs current):")
    print(f"     python karaoke_automator.py --ab-test pre_optimization current --max-tracks 2")
    
    print(f"\n   Test solo activation delay impact only:")
    print(f"     python karaoke_automator.py --ab-test current solo_only --max-tracks 2")
    
    print(f"\n   Test download monitoring impact only:")
    print(f"     python karaoke_automator.py --ab-test current download_only --max-tracks 2")
    
    print(f"\n   Individual baseline test:")
    print(f"     python karaoke_automator.py --baseline-test pre_optimization --max-tracks 2")
    
    print(f"\n💡 ANALYSIS WORKFLOW:")
    print(f"   1. Run: --ab-test pre_optimization current")
    print(f"      → Confirms overall 2x regression and quantifies impact")
    
    print(f"\n   2. Run: --ab-test current solo_only") 
    print(f"      → Isolates solo activation delay impact (5s → 12s/15s/21s)")
    
    print(f"\n   3. Run: --ab-test current download_only")
    print(f"      → Isolates download monitoring impact (0s → 30s initial wait)")
    
    print(f"\n   4. Compare results to identify primary regression source")
    
    print(f"\n📁 All results saved to: logs/performance/baselines/")
    print(f"📊 Detailed profiling data included for method-level analysis")
    
    print(f"\n" + "=" * 60)

if __name__ == "__main__":
    main()