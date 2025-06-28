import yaml
import sys

# Load YAML system architecture
def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def generate_dot(yaml_data):
    print('digraph SystemDesign {')
    print('  rankdir=LR;')
    # Print modules as nodes
    for module in yaml_data.get('modules', []):
        print(f'  "{module["name"]}" [shape=box];')
        for sub in module.get('submodules', []):
            print(f'  "{sub["name"]}" [shape=ellipse];')
            print(f'  "{module["name"]}" -> "{sub["name"]}" [style=dotted, label="submodule"];')
    # Print dependencies
    for dep in yaml_data.get('dependencies', []):
        if isinstance(dep['to'], list):
            for target in dep['to']:
                print(f'  "{dep["from"]}" -> "{target}" [color=blue, label="depends"];')
        else:
            print(f'  "{dep["from"]}" -> "{dep["to"]}" [color=blue, label="depends"];')
    print('}')

if __name__ == "__main__":
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else '../system_design_architecture.yaml'
    data = load_yaml(yaml_path)
    generate_dot(data) 