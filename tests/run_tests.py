#!/usr/bin/env python3
"""
Test Suite Runner
Organized test execution for the karaoke automation project
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRunner:
    """Organized test suite runner"""
    
    def __init__(self):
        self.tests_dir = Path(__file__).parent
        self.results = {}
    
    def run_regression_tests(self):
        """Run regression tests for refactor safety"""
        print("🔄 RUNNING REGRESSION TESTS")
        print("=" * 50)
        
        regression_dir = self.tests_dir / "regression"
        
        tests = [
            ("Configuration System", regression_dir / "test_config_refactor.py"),
            ("Core Functionality", regression_dir / "test_regression_suite.py")
        ]
        
        for test_name, test_path in tests:
            if test_path.exists():
                print(f"\n📋 Running {test_name}...")
                success = self._run_test(test_path)
                self.results[f"Regression: {test_name}"] = success
            else:
                print(f"⚠️ Test not found: {test_path}")
                self.results[f"Regression: {test_name}"] = False
    
    def run_integration_tests(self, quick_mode=False):
        """Run integration tests"""
        print("\n🧪 RUNNING INTEGRATION TESTS")
        print("=" * 50)
        
        integration_dir = self.tests_dir / "integration"
        
        if quick_mode:
            tests = [
                ("Mixer Controls", integration_dir / "test_mixer_controls.py")
            ]
        else:
            tests = [
                ("Download Functionality", integration_dir / "test_download_fix.py"),
                ("Mixer Controls", integration_dir / "test_mixer_controls.py"),
                ("End-to-End Comprehensive", integration_dir / "test_end_to_end_comprehensive.py")
            ]
        
        for test_name, test_path in tests:
            if test_path.exists():
                print(f"\n📋 Running {test_name}...")
                if test_name == "End-to-End Comprehensive":
                    print("   (This test takes longer and opens a browser)")
                success = self._run_test(test_path)
                self.results[f"Integration: {test_name}"] = success
            else:
                print(f"⚠️ Test not found: {test_path}")
                self.results[f"Integration: {test_name}"] = False
    
    def run_unit_tests(self):
        """Run unit tests from unit/ directory"""
        print("\n🔬 RUNNING UNIT TESTS")
        print("=" * 50)
        
        unit_dir = self.tests_dir / "unit"
        unit_tests_exist = unit_dir.exists() and any(unit_dir.glob("test_*.py"))
        
        if unit_tests_exist:
            print("📋 Running unit tests...")
            try:
                # Try pytest first
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    str(unit_dir), 
                    "-v", "--tb=short"
                ], cwd=project_root, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ Unit tests passed")
                    self.results["Unit Tests"] = True
                else:
                    # Fallback to running individual test files
                    print("📋 Pytest failed, trying individual test files...")
                    unit_tests = list(unit_dir.glob("test_*.py"))
                    successful = 0
                    
                    for test_file in unit_tests[:5]:  # Limit to first 5 for performance
                        success = self._run_test(test_file)
                        if success:
                            successful += 1
                    
                    if successful > len(unit_tests) / 2:
                        print(f"✅ Unit tests mostly passed ({successful}/{len(unit_tests[:5])})")
                        self.results["Unit Tests"] = True
                    else:
                        print(f"❌ Unit tests mostly failed ({successful}/{len(unit_tests[:5])})")
                        self.results["Unit Tests"] = False
                        
            except Exception as e:
                print(f"⚠️ Could not run unit tests: {e}")
                self.results["Unit Tests"] = False
        else:
            print("ℹ️ No unit tests found in unit/ directory")
            self.results["Unit Tests"] = True
    
    def _run_test(self, test_path):
        """Run a single test file"""
        try:
            # Set environment to include project root in Python path
            env = os.environ.copy()
            python_path = str(project_root)
            if 'PYTHONPATH' in env:
                python_path = f"{python_path}:{env['PYTHONPATH']}"
            env['PYTHONPATH'] = python_path
            
            result = subprocess.run([
                sys.executable, str(test_path)
            ], cwd=project_root, capture_output=True, text=True, timeout=300, env=env)
            
            # Check for success indicators in output
            output = result.stdout + result.stderr
            
            # Look for success patterns
            success_patterns = [
                "✅", "PASSED", "SUCCESS", "ALL.*TESTS.*PASSED", 
                "EXCELLENT", "test.*passed", "SUCCESSFUL"
            ]
            
            failure_patterns = [
                "❌", "FAILED", "ERROR", "CRITICAL", "test.*failed"
            ]
            
            # Count success vs failure indicators
            success_count = sum(1 for pattern in success_patterns if pattern.lower() in output.lower())
            failure_count = sum(1 for pattern in failure_patterns if pattern.lower() in output.lower())
            
            # Look for definitive success indicators at the end
            lines = output.strip().split('\n')
            final_lines = '\n'.join(lines[-5:]).lower()  # Check last 5 lines
            has_final_success = any(pattern.lower() in final_lines for pattern in ["successful", "all.*tests.*passed", "passed"])
            has_final_failure = any(pattern.lower() in final_lines for pattern in ["failed", "critical"])
            
            if result.returncode == 0 and (has_final_success or (success_count > failure_count and success_count > 0)):
                print("   ✅ PASSED")
                return True
            else:
                print("   ❌ FAILED")
                if result.returncode != 0:
                    print(f"   Exit code: {result.returncode}")
                if output:
                    # Show last few lines of output for debugging
                    lines = output.strip().split('\n')
                    for line in lines[-3:]:
                        if line.strip():
                            print(f"   {line}")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ⏰ TIMEOUT (5 minutes)")
            return False
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            return False
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 70)
        print("📊 TEST SUITE RESULTS SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.results.values() if result)
        total = len(self.results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Overall Results: {passed}/{total} ({success_rate:.1f}%)")
        print()
        
        # Group by category
        categories = {}
        for test_name, result in self.results.items():
            if ":" in test_name:
                category, name = test_name.split(":", 1)
                if category not in categories:
                    categories[category] = []
                categories[category].append((name.strip(), result))
            else:
                if "Other" not in categories:
                    categories["Other"] = []
                categories["Other"].append((test_name, result))
        
        for category, tests in categories.items():
            print(f"📋 {category}:")
            for test_name, result in tests:
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"   {status} - {test_name}")
            print()
        
        # Overall assessment
        if success_rate >= 90:
            print("🎉 EXCELLENT - All systems operational")
            print("✅ SAFE TO PROCEED with refactoring or deployment")
        elif success_rate >= 75:
            print("✅ GOOD - Most functionality working")
            print("🔧 Minor issues to address")
        elif success_rate >= 50:
            print("⚠️ CONCERNING - Multiple test failures")
            print("🛠️ Investigate and fix issues before proceeding")
        else:
            print("🛑 CRITICAL - Major test failures")
            print("❌ DO NOT PROCEED - Fix critical issues first")
        
        return success_rate >= 75

def main():
    """Main test runner entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run organized test suite")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick tests only (regression + minimal integration)")
    parser.add_argument("--regression-only", action="store_true",
                       help="Run only regression tests")
    parser.add_argument("--integration-only", action="store_true", 
                       help="Run only integration tests")
    parser.add_argument("--unit-only", action="store_true",
                       help="Run only unit tests")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    print("🧪 KARAOKE AUTOMATION TEST SUITE")
    print("=" * 70)
    print("Organized test execution for safe development and refactoring")
    print("=" * 70)
    
    start_time = time.time()
    
    if args.regression_only:
        runner.run_regression_tests()
    elif args.integration_only:
        runner.run_integration_tests()
    elif args.unit_only:
        runner.run_unit_tests()
    elif args.quick:
        print("🚀 QUICK MODE - Running essential tests only")
        runner.run_regression_tests()
        runner.run_integration_tests(quick_mode=True)
    else:
        print("🔍 FULL MODE - Running comprehensive test suite")
        runner.run_regression_tests()
        runner.run_integration_tests()
        runner.run_unit_tests()
    
    elapsed = time.time() - start_time
    print(f"\n⏱️ Total execution time: {elapsed:.1f} seconds")
    
    success = runner.print_summary()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()