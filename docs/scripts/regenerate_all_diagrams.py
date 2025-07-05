#!/usr/bin/env python3
"""
Regenerate All Diagrams Script
Automatically regenerates all system architecture diagrams and updates documentation
"""

import os
import sys
import subprocess
from datetime import datetime

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"   Error output: {e.stderr}")
        return False

def main():
    """Main function to regenerate all diagrams"""
    print("🚀 Regenerating All System Architecture Diagrams")
    print("=" * 60)
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    docs_dir = os.path.dirname(script_dir)
    yaml_file = os.path.join(docs_dir, 'system_design_architecture.yaml')
    
    # Check if YAML file exists
    if not os.path.exists(yaml_file):
        print(f"❌ YAML file not found: {yaml_file}")
        sys.exit(1)
    
    print(f"📁 Working directory: {script_dir}")
    print(f"📄 YAML source: {yaml_file}")
    print()
    
    # Change to scripts directory
    os.chdir(script_dir)
    
    # Generate DOT diagrams
    success1 = run_command(
        f"python3 generate_dot.py {yaml_file} .",
        "Generating DOT diagrams"
    )
    
    # Generate UML diagrams
    success2 = run_command(
        f"python3 generate_uml.py {yaml_file} .",
        "Generating UML diagrams"
    )
    
    # List generated files
    print("\n📊 Generated Files:")
    print("-" * 30)
    
    # DOT files
    dot_files = [f for f in os.listdir('.') if f.endswith('.dot')]
    png_files = [f for f in os.listdir('.') if f.endswith('.png')]
    
    print("DOT Format:")
    for file in sorted(dot_files):
        size = os.path.getsize(file)
        print(f"  📄 {file} ({size} bytes)")
    
    print("PNG Images:")
    for file in sorted(png_files):
        size = os.path.getsize(file)
        print(f"  🖼️  {file} ({size} bytes)")
    
    # Mermaid files
    mmd_files = [f for f in os.listdir('.') if f.endswith('.mmd')]
    html_files = [f for f in os.listdir('.') if f.endswith('.html')]
    
    print("Mermaid Format:")
    for file in sorted(mmd_files):
        size = os.path.getsize(file)
        print(f"  📄 {file} ({size} bytes)")
    
    print("HTML Files:")
    for file in sorted(html_files):
        size = os.path.getsize(file)
        print(f"  🌐 {file} ({size} bytes)")
    
    # Update documentation timestamp
    docs_file = os.path.join(docs_dir, 'system_architecture_diagrams.md')
    if os.path.exists(docs_file):
        print(f"\n📝 Updating documentation timestamp...")
        try:
            with open(docs_file, 'r') as f:
                content = f.read()
            
            # Replace the timestamp at the bottom
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content = content.replace(
                "*Generated on: $(date)*",
                f"*Generated on: {timestamp}*"
            )
            
            with open(docs_file, 'w') as f:
                f.write(content)
            
            print(f"✅ Documentation updated with timestamp: {timestamp}")
        except Exception as e:
            print(f"⚠️  Could not update documentation: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 All diagrams generated successfully!")
        print(f"📁 Files saved in: {script_dir}")
        print(f"📖 Documentation: {docs_file}")
        print("\n💡 Next steps:")
        print("   - View PNG files with any image viewer")
        print("   - Open HTML files in a web browser")
        print("   - Use DOT files with Graphviz tools")
        print("   - Use MMD files with Mermaid Live Editor")
    else:
        print("⚠️  Some diagrams failed to generate. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 