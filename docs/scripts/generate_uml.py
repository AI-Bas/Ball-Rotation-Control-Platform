import yaml
import sys

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def generate_mermaid(yaml_data):
    print('classDiagram')
    # Print modules and submodules as classes
    for module in yaml_data.get('modules', []):
        print(f'    class {module["name"]}')
        for sub in module.get('submodules', []):
            print(f'    class {sub["name"]}')
            print(f'    {module["name"]} <|-- {sub["name"]}')
    # Print dependencies as associations
    for dep in yaml_data.get('dependencies', []):
        if isinstance(dep['to'], list):
            for target in dep['to']:
                print(f'    {dep["from"]} --> {target}')
        else:
            print(f'    {dep["from"]} --> {dep["to"]}')

if __name__ == "__main__":
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else '../system_design_architecture.yaml'
    data = load_yaml(yaml_path)
    generate_mermaid(data) 