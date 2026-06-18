import os
from pathlib import Path
from deer.tools.builtin.python_editor import RuntimeManager

def test_add_function():
    # Setup
    jail_path = Path("./sandbox_test").resolve()
    jail_path.mkdir(exist_ok=True)
    
    manager = RuntimeManager()
    manager.jail = jail_path
    
    test_file = "script.py"
    
    # 1. Add new function
    fn1 = """
def hello():
    print("hello")
"""
    result = manager.add_function(test_file, fn1)
    print(f"Step 1: {result}")
    
    with open(jail_path / test_file, "r") as f:
        content = f.read()
        print("Content after step 1:")
        print(content)
        assert "def hello():" in content

    # 2. Update existing function
    fn1_updated = """
def hello():
    print("hello updated")
"""
    result = manager.add_function(test_file, fn1_updated)
    print(f"Step 2: {result}")
    
    with open(jail_path / test_file, "r") as f:
        content = f.read()
        print("Content after step 2:")
        print(content)
        assert "hello updated" in content
        assert content.count("def hello():") == 1

    # 3. Add second function
    fn2 = """
def world():
    print("world")
"""
    result = manager.add_function(test_file, fn2)
    print(f"Step 3: {result}")
    
    with open(jail_path / test_file, "r") as f:
        content = f.read()
        print("Content after step 3:")
        print(content)
        assert "def world():" in content
        assert "def hello():" in content

    print("All tests passed!")

if __name__ == "__main__":
    try:
        test_add_function()
    finally:
        # Cleanup
        import shutil
        if os.path.exists("./sandbox_test"):
            shutil.rmtree("./sandbox_test")
