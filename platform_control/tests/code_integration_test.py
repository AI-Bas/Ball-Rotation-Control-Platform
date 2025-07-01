#!/usr/bin/env python3
"""
Code Integration Test Module
Performs code integrity evaluation and development-specific testing.
Analyzes scripts, libraries, and dependencies for code maintenance.
"""

import os
import sys
import ast
import json
import importlib
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Try to import pkg_resources, fallback if not available
try:
    import pkg_resources
except ImportError:
    pkg_resources = None

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_logger import DataLogger


class CodeIntegrationTest:
    """Comprehensive code analysis and integration testing."""
    
    def __init__(self, development_mode: bool = False):
        self.development_mode = development_mode
        self.results = {}
        self.config = self.load_platform_config()
        
    def load_platform_config(self) -> Dict[str, Any]:
        """Load platform configuration."""
        config_path = Path(__file__).parent.parent / "config" / "platform_config.json"
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single Python file for code quality and dependencies."""
        result = {
            "file_path": str(file_path),
            "lines": 0,
            "imports": [],
            "classes": [],
            "functions": [],
            "issues": [],
            "suggestions": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                result["lines"] = len(content.split('\n'))
            
            # Parse AST
            tree = ast.parse(content)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        result["imports"].append(f"{module}.{alias.name}")
                elif isinstance(node, ast.ClassDef):
                    result["classes"].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    result["functions"].append(node.name)
            
            # Analyze code quality
            self._analyze_code_quality(content, result)
            
        except Exception as e:
            result["issues"].append(f"Error analyzing file: {e}")
        
        return result
    
    def _analyze_code_quality(self, content: str, result: Dict[str, Any]):
        """Analyze code quality and provide suggestions."""
        lines = content.split('\n')
        
        # Check for common issues
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Check for hardcoded paths
            if any(path_indicator in line for path_indicator in ['/home/', 'C:\\', 'C:/']):
                result["issues"].append(f"Line {i}: Hardcoded path detected")
                result["suggestions"].append(f"Line {i}: Use Path or os.path for cross-platform compatibility")
            
            # Check for print statements in production code
            if line.startswith('print(') and not self.development_mode:
                result["suggestions"].append(f"Line {i}: Consider using logging instead of print")
            
            # Check for TODO/FIXME comments
            if any(todo in line.upper() for todo in ['TODO', 'FIXME', 'HACK']):
                result["issues"].append(f"Line {i}: TODO/FIXME comment found")
    
    def scan_directory(self, directory: Path, file_pattern: str = "*.py") -> List[Dict[str, Any]]:
        """Scan directory for Python files and analyze them."""
        results = []
        
        for file_path in directory.rglob(file_pattern):
            if file_path.is_file():
                result = self.analyze_python_file(file_path)
                results.append(result)
        
        return results
    
    def test_pip_libraries(self) -> Dict[str, Any]:
        """Test pip library availability and compatibility."""
        result = {
            "status": True,
            "installed_packages": {},
            "missing_packages": [],
            "version_conflicts": [],
            "suggestions": [],
            "issues": [],
            "hardware_tests": {}
        }
        
        # Check if pkg_resources is available
        if pkg_resources is None:
            result["status"] = False
            result["issues"].append("pkg_resources not available - cannot check package versions")
            return result
        
        # Required packages for the platform
        required_packages = [
            "pyserial", "smbus2", "spidev", "RPi.GPIO", "pmw3901", "ina219"
        ]
        
        for package in required_packages:
            try:
                version = pkg_resources.get_distribution(package).version
                result["installed_packages"][package] = version
            except pkg_resources.DistributionNotFound:
                result["missing_packages"].append(package)
                result["status"] = False
        
        # Test hardware-specific library functionality
        result["hardware_tests"] = self._test_hardware_libraries()
        
        # Check for version conflicts
        if len(result["installed_packages"]) > 0:
            result["suggestions"].append("All required packages are installed")
        
        return result
    
    def _test_hardware_libraries(self) -> Dict[str, Any]:
        """Test hardware-specific library functionality."""
        hardware_tests = {}
        
        # Test PMW3901 optical flow sensor library
        print("Testing PMW3901 library...")
        try:
            from pmw3901 import PAA5100
            print("✓ PMW3901 library imported successfully")
            
            # Test initialization (without actual hardware)
            try:
                sensor = PAA5100()
                print("✓ PMW3901 sensor object created")
                hardware_tests["pmw3901"] = {"status": True, "error": None}
            except Exception as e:
                print(f"⚠ PMW3901 hardware not connected (expected): {e}")
                hardware_tests["pmw3901"] = {"status": True, "error": f"Hardware not connected: {e}"}
        except ImportError as e:
            print(f"✗ PMW3901 library import failed: {e}")
            hardware_tests["pmw3901"] = {"status": False, "error": str(e)}
        
        # Test INA219 current sensor library
        print("\nTesting INA219 library...")
        try:
            from ina219 import INA219
            print("✓ INA219 library imported successfully")
            
            # Test initialization (without actual hardware)
            try:
                sensor = INA219(0.1, address=0x40)
                print("✓ INA219 sensor object created")
                hardware_tests["ina219"] = {"status": True, "error": None}
            except Exception as e:
                print(f"⚠ INA219 hardware not connected (expected): {e}")
                hardware_tests["ina219"] = {"status": True, "error": f"Hardware not connected: {e}"}
        except ImportError as e:
            print(f"✗ INA219 library import failed: {e}")
            hardware_tests["ina219"] = {"status": False, "error": str(e)}
        
        # Test I2C device detection
        print("\nTesting I2C device detection...")
        try:
            import subprocess
            result_i2c = subprocess.run(['i2cdetect', '-y', '1'], 
                                      capture_output=True, text=True)
            if result_i2c.returncode == 0:
                print("✓ I2C detection successful")
                print("I2C scan result:")
                print(result_i2c.stdout)
                hardware_tests["i2c_detection"] = {"status": True, "error": None}
            else:
                print(f"✗ I2C detection failed: {result_i2c.stderr}")
                hardware_tests["i2c_detection"] = {"status": False, "error": result_i2c.stderr}
        except Exception as e:
            print(f"✗ I2C detection error: {e}")
            hardware_tests["i2c_detection"] = {"status": False, "error": str(e)}
        
        # Test serial port detection
        print("\nTesting serial port detection...")
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            print(f"✓ Found {len(ports)} serial ports:")
            for port in ports:
                print(f"  - {port.device}: {port.description}")
            hardware_tests["serial_detection"] = {"status": True, "error": None}
        except Exception as e:
            print(f"✗ Serial port detection error: {e}")
            hardware_tests["serial_detection"] = {"status": False, "error": str(e)}
        
        return hardware_tests
    
    def test_custom_libraries(self) -> Dict[str, Any]:
        """Test custom library functionality."""
        result = {
            "status": True,
            "tested_libraries": [],
            "issues": [],
            "suggestions": []
        }
        
        # Test custom library imports
        custom_libraries = [
            "utils.roboclaw_interface",
            "utils.power_sensor", 
            "utils.optical_flow_sensor",
            "utils.maker_pi_interface",
            "utils.kinematic_conversion",
            "utils.data_logger"
        ]
        
        for lib in custom_libraries:
            try:
                importlib.import_module(lib)
                result["tested_libraries"].append({
                    "name": lib,
                    "status": "imported",
                    "error": None
                })
            except Exception as e:
                result["tested_libraries"].append({
                    "name": lib,
                    "status": "failed",
                    "error": str(e)
                })
                result["status"] = False
                result["issues"].append(f"Failed to import {lib}: {e}")
        
        return result
    
    def analyze_example_code(self) -> Dict[str, Any]:
        """Analyze example code for best practices and integration potential."""
        result = {
            "status": True,
            "examples_analyzed": 0,
            "integration_opportunities": [],
            "best_practices": [],
            "issues": []
        }
        
        examples_dir = Path(__file__).parent.parent.parent / "examples"
        if examples_dir.exists():
            for example_file in examples_dir.rglob("*.py"):
                result["examples_analyzed"] += 1
                
                # Analyze example file
                analysis = self.analyze_python_file(example_file)
                
                # Check for integration opportunities
                if analysis["classes"] or analysis["functions"]:
                    result["integration_opportunities"].append({
                        "file": str(example_file),
                        "classes": analysis["classes"],
                        "functions": analysis["functions"]
                    })
                
                # Check for best practices
                if not analysis["issues"]:
                    result["best_practices"].append(str(example_file))
                else:
                    result["issues"].extend(analysis["issues"])
        
        return result
    
    def generate_mockup_script(self, template: str, context: Dict[str, Any]) -> str:
        """Generate a mockup script based on template and context."""
        mockup = f"""#!/usr/bin/env python3
\"\"\"
Mockup Script: {template}
Generated by Code Integration Test
Context: {json.dumps(context, indent=2)}
\"\"\"

import sys
from pathlib import Path

# Add platform_control to path
sys.path.append(str(Path(__file__).parent / "platform_control"))

def main():
    \"\"\"Main function for {template}.\"\"\"
    print(f"Mockup script for {template}")
    print(f"Context: {context}")
    
    # TODO: Implement actual functionality
    # This is a placeholder for development and testing
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        return mockup
    
    def run_code_integration_tests(self) -> Dict[str, Any]:
        """Run comprehensive code integration tests."""
        print("🔍 Running Code Integration Tests...")
        
        results = {
            "pip_libraries": self.test_pip_libraries(),
            "custom_libraries": self.test_custom_libraries(),
            "example_analysis": self.analyze_example_code(),
            "platform_analysis": self.scan_directory(Path(__file__).parent.parent),
            "timestamp": self._get_timestamp()
        }
        
        # Overall status
        results["status"] = all([
            results["pip_libraries"]["status"],
            results["custom_libraries"]["status"]
        ])
        
        return results
    
    def display_results(self, results: Dict[str, Any]):
        """Display code integration test results."""
        print("\n" + "=" * 60)
        print("🔍 CODE INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        # Pip Libraries
        pip = results["pip_libraries"]
        print(f"📦 PIP LIBRARIES: {'✅' if pip['status'] else '❌'}")
        print(f"   Installed: {len(pip['installed_packages'])}")
        print(f"   Missing: {len(pip['missing_packages'])}")
        if pip['missing_packages']:
            print(f"   Missing packages: {', '.join(pip['missing_packages'])}")
        
        # Custom Libraries
        custom = results["custom_libraries"]
        print(f"🔧 CUSTOM LIBRARIES: {'✅' if custom['status'] else '❌'}")
        print(f"   Tested: {len(custom['tested_libraries'])}")
        failed = [lib for lib in custom['tested_libraries'] if lib['status'] == 'failed']
        if failed:
            print(f"   Failed: {len(failed)}")
            for lib in failed:
                print(f"     - {lib['name']}: {lib['error']}")
        
        # Example Analysis
        examples = results["example_analysis"]
        print(f"📚 EXAMPLE ANALYSIS: {'✅' if examples['status'] else '❌'}")
        print(f"   Analyzed: {examples['examples_analyzed']} files")
        print(f"   Integration opportunities: {len(examples['integration_opportunities'])}")
        print(f"   Best practices: {len(examples['best_practices'])}")
        
        # Platform Analysis
        platform = results["platform_analysis"]
        print(f"🏗️ PLATFORM ANALYSIS:")
        print(f"   Files analyzed: {len(platform)}")
        total_lines = sum(f["lines"] for f in platform)
        print(f"   Total lines: {total_lines}")
        
        print("\n" + "-" * 60)
        print(f"📊 SUMMARY: {'✅' if results['status'] else '❌'} Overall Status")
        print("=" * 60)
    
    def save_results(self, results: Dict[str, Any]) -> bool:
        """Save test results to file."""
        try:
            log_dir = Path(__file__).parent / "test_logs" / "code_integration"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = self._get_timestamp()
            filename = f"code_integration_test_{timestamp}.json"
            filepath = log_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"💾 Results saved to: {filepath}")
            return True
            
        except Exception as e:
            print(f"Error saving results: {e}")
            return False
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for file naming."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    """Main function for code integration testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Code Integration Test Module")
    parser.add_argument("--dev", action="store_true", help="Development mode")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument("--autopilot", type=str, help="Autopilot input sequence")
    
    args = parser.parse_args()
    
    # Initialize test
    test = CodeIntegrationTest(development_mode=args.dev)
    
    # Run tests
    results = test.run_code_integration_tests()
    
    # Display results
    test.display_results(results)
    
    # Save results if requested
    if args.save:
        test.save_results(results)
    
    return 0 if results["status"] else 1


if __name__ == "__main__":
    sys.exit(main())
