import os

def search_text(root_dir, target):
    print(f"Searching for '{target}' in {root_dir}...")
    for root, dirs, files in os.walk(root_dir):
        # Exclude directories starting with . or env
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'env', 'venv']]
        for file in files:
            if file.endswith('.py') or file.endswith('.js') or file.endswith('.ts') or file.endswith('.tsx'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            if target in line:
                                print(f"Found in {path}:{i} -> {line.strip()}")
                except Exception as e:
                    pass

if __name__ == "__main__":
    search_text("backend", "scheduler")
