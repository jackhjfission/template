#!/usr/bin/env python3
"""
Generate a cookiecutter template from the current repository.

This script transforms the working template repository into a cookiecutter-ready
structure by:
1. Copying all relevant files to cookiecutter-output/
2. Renaming directories with cookiecutter template syntax
3. Replacing hardcoded values with cookiecutter variables
4. Creating a cookiecutter.json configuration file

Usage:
    python generate_cookiecutter.py
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Set
import json


# Configuration
SOURCE_DIR = Path(".")
OUTPUT_DIR = Path("cookiecutter-output")
TEMPLATE_ROOT = OUTPUT_DIR / "{{cookiecutter.project_slug}}"

# Files and directories to exclude from copying
EXCLUDE_PATTERNS = {
    ".git",
    ".gitignore",  # Will create a new one
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "poetry.lock",
    "mypy.ini",  # Generated file, should not be in template
    "cookiecutter-output",
    "generate_cookiecutter.py",
    "COOKIECUTTER_README.md",  # Cookiecutter documentation
    ".ruff_cache",
    ".vscode",  # IDE settings
    ".idea",  # IDE settings
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".Python",
    "pip-log.txt",
    "pip-delete-this-directory.txt",
    ".coverage",
    "htmlcov",
    ".tox",
    ".DS_Store",
    ".approval_tests_temp",
    ".approval_tests_cache",  # Approval tests cache
    "approved_files",  # Approval tests temp files
    "received_files",  # Approval tests temp files
}

# Cookiecutter default values
COOKIECUTTER_CONFIG = {
    "project_slug": "myproject",
    "project_name": "My Project",
    "author_name": "Your Name",
    "author_email": "you@example.com",
    "docker_image_name": "myproject",
    "docker_service_name": "myproject-dev",
    "user_name": "devuser",
    "docker_image_version": "v0.0.0",
}

# Mapping of source names to cookiecutter template names
DIRECTORY_RENAMES = {
    "template_core": "{{cookiecutter.project_slug}}_core",
    "template_tools": "{{cookiecutter.project_slug}}_tools",
}


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded from copying."""
    path_str = str(path)
    
    # First priority: Always exclude .git directory (but not .github)
    if path.name == ".git" and path.is_dir():
        return True
    # Also exclude any files/dirs inside .git
    if ".git" in path.parts and path.parts[path.parts.index(".git") + 1:]:
        # This means .git is in the path and there are parts after it (we're inside .git)
        return True
    
    # Special case: in scratchpads directories, only keep .gitignore files
    if "scratchpads" in path.parts and path.is_file():
        if path.name == ".gitignore":
            return False  # Keep .gitignore in scratchpads
        else:
            return True  # Exclude all other files
    
    for pattern in EXCLUDE_PATTERNS:
        # Skip .git pattern since we handle it above
        if pattern == ".git":
            continue
        elif pattern in path_str or path.name == pattern:
            return True
        # Handle glob patterns
        elif "*" in pattern and path.match(pattern):
            return True
    return False


def get_template_path(source_path: Path) -> Path:
    """Convert a source path to its corresponding template path."""
    parts = list(source_path.parts)
    
    # Skip the current directory marker if present
    if parts[0] == ".":
        parts = parts[1:]
    
    # Rename directories according to DIRECTORY_RENAMES
    new_parts = []
    for part in parts:
        if part in DIRECTORY_RENAMES:
            new_parts.append(DIRECTORY_RENAMES[part])
        else:
            new_parts.append(part)
    
    return TEMPLATE_ROOT / Path(*new_parts) if new_parts else TEMPLATE_ROOT


def process_text_content(content: str, filepath: Path) -> str:
    """
    Replace template-specific values with cookiecutter variables.
    
    Args:
        content: The file content as a string
        filepath: The path to the file being processed (for context-aware replacements)
    
    Returns:
        The processed content with cookiecutter variables
    """
    filename = filepath.name
    
    # Handle pyproject.toml files
    if filename == "pyproject.toml":
        # Replace package names
        content = re.sub(
            r'name = "template_core"',
            'name = "{{cookiecutter.project_slug}}_core"',
            content
        )
        content = re.sub(
            r'name = "template_tools"',
            'name = "{{cookiecutter.project_slug}}_tools"',
            content
        )
        content = re.sub(
            r'name = "template-tools"',
            'name = "{{cookiecutter.project_slug}}-tools"',
            content
        )
        
        # Replace CLI script names
        content = re.sub(
            r'template-core = "template_core\.cli:main"',
            '{{cookiecutter.project_slug}}-core = "{{cookiecutter.project_slug}}_core.cli:main"',
            content
        )
        content = re.sub(
            r'template-tools = "template_tools\.cli:main"',
            '{{cookiecutter.project_slug}}-tools = "{{cookiecutter.project_slug}}_tools.cli:main"',
            content
        )
        
        # Replace author information
        content = re.sub(
            r'authors = \["[^"]+"\]',
            'authors = ["{{cookiecutter.author_name}} <{{cookiecutter.author_email}}>"]',
            content
        )
        
        # Replace cross-package dependencies
        content = re.sub(
            r'template_tools = \{ path = "\.\./template_tools/", develop = true \}',
            '{{cookiecutter.project_slug}}_tools = { path = "../{{cookiecutter.project_slug}}_tools/", develop = true }',
            content
        )
        
        # Replace description references
        content = re.sub(
            r'description = "Core functionality for the template project\."',
            'description = "Core functionality for the {{cookiecutter.project_name}} project."',
            content
        )
        content = re.sub(
            r'description = "Shared utils for the template project\."',
            'description = "Shared utils for the {{cookiecutter.project_name}} project."',
            content
        )
    
    # Handle .env file
    elif filename == ".env":
        content = re.sub(
            r'IMAGE_NAME=template',
            'IMAGE_NAME={{cookiecutter.docker_image_name}}',
            content
        )
        content = re.sub(
            r'USER_NAME=\w+',
            'USER_NAME={{cookiecutter.user_name}}',
            content
        )
        content = re.sub(
            r'IMAGE_VERSION=v\d+\.\d+\.\d+',
            'IMAGE_VERSION={{cookiecutter.docker_image_version}}',
            content
        )
    
    # Handle devcontainer.json
    elif filename == "devcontainer.json":
        content = re.sub(
            r'"name": "template"',
            '"name": "{{cookiecutter.project_name}}"',
            content
        )
        content = re.sub(
            r'"image": "template:v\d+\.\d+\.\d+"',
            '"image": "{{cookiecutter.docker_image_name}}:{{cookiecutter.docker_image_version}}"',
            content
        )
        # Replace user name in paths
        content = re.sub(
            r'/home/klapaucius/',
            '/home/{{cookiecutter.user_name}}/',
            content
        )
    
    # Handle compose.yaml
    elif filename == "compose.yaml":
        content = re.sub(
            r'template-dev:',
            '{{cookiecutter.docker_service_name}}:',
            content
        )
    
    # Handle shell scripts and pre-commit hooks
    elif filename.endswith('.sh') or filename == 'pre-commit':
        # Replace user name in paths first
        content = re.sub(
            r'/home/klapaucius/',
            '/home/{{cookiecutter.user_name}}/',
            content
        )
        
        # For bash scripts, we need to escape ${# which Jinja2 interprets as comment start
        # Replace ${# with {{ '${#' }} which outputs the literal string
        if '${#' in content:
            content = content.replace('${#', "{{ '${#' }}")
    
    # Handle README.md
    elif filename == "README.md":
        # Remove the cookiecutter notice line (not needed in generated projects)
        content = re.sub(
            r'> \*\*📦 Using this as a Cookiecutter Template\?\*\* See \[COOKIECUTTER_README\.md\]\(COOKIECUTTER_README\.md\) for instructions on generating new projects from this template\.\n\n',
            '',
            content
        )
        
        # Replace project title
        content = re.sub(
            r'^# Template Project',
            '# {{cookiecutter.project_name}}',
            content,
            flags=re.MULTILINE
        )
        
        # Replace git clone URL
        content = re.sub(
            r'git clone git@github\.com:jackhjfission/template\.git',
            'git clone <your-repo-url>',
            content
        )
        content = re.sub(
            r'cd template',
            'cd {{cookiecutter.project_slug}}',
            content
        )
        
        # Replace package references
        content = re.sub(r'\btemplate_core\b', '{{cookiecutter.project_slug}}_core', content)
        content = re.sub(r'\btemplate_tools\b', '{{cookiecutter.project_slug}}_tools', content)
        content = re.sub(r'\btemplate-tools\b', '{{cookiecutter.project_slug}}-tools', content)
        
        # Replace generic "template" references in documentation
        content = re.sub(
            r'A Python monorepo template',
            'A Python monorepo for {{cookiecutter.project_name}}',
            content
        )
        
        # Replace user name references
        content = re.sub(r'\bklapaucius\b', '{{cookiecutter.user_name}}', content)
        
        # Replace IMAGE_NAME references
        content = re.sub(
            r'IMAGE_NAME=template',
            'IMAGE_NAME={{cookiecutter.docker_image_name}}',
            content
        )
    
    # Handle Python source files
    elif filename.endswith('.py'):
        # Replace package imports
        content = re.sub(r'\btemplate_core\b', '{{cookiecutter.project_slug}}_core', content)
        content = re.sub(r'\btemplate_tools\b', '{{cookiecutter.project_slug}}_tools', content)
    
    # Handle .pre-commit-config.yaml files
    elif filename == '.pre-commit-config.yaml':
        # Replace hardcoded paths in mypy config-file arguments
        content = re.sub(
            r'--config-file=template_core/mypy\.ini',
            '--config-file={{cookiecutter.project_slug}}_core/mypy.ini',
            content
        )
        content = re.sub(
            r'--config-file=template_tools/mypy\.ini',
            '--config-file={{cookiecutter.project_slug}}_tools/mypy.ini',
            content
        )
    
    # Handle GitHub Actions workflow files
    elif filename.endswith('.yml') or filename.endswith('.yaml'):
        # GitHub Actions uses ${{ }} syntax which conflicts with Jinja2
        # Wrap entire content in raw blocks to prevent Jinja2 processing
        if '${{' in content:
            content = '{% raw %}' + content + '{% endraw %}'
    
    return content


def copy_and_process_file(source: Path, dest: Path) -> None:
    """Copy a file and process its content if it's a text file."""
    # Create parent directory if it doesn't exist
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Try to read as text and process
    try:
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process the content
        processed_content = process_text_content(content, source)
        
        # Write processed content
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        # Preserve executable bit
        if os.access(source, os.X_OK):
            os.chmod(dest, os.stat(dest).st_mode | 0o111)
            
    except (UnicodeDecodeError, IsADirectoryError):
        # If it's not a text file, just copy it
        shutil.copy2(source, dest)


def copy_directory_structure(source: Path, template_root: Path) -> None:
    """Recursively copy directory structure, processing files along the way."""
    for item in source.rglob("*"):
        # Skip if should be excluded
        if should_exclude(item):
            continue
        
        # Get relative path and convert to template path
        try:
            relative_path = item.relative_to(source)
        except ValueError:
            continue
        
        dest_path = get_template_path(relative_path)
        
        if item.is_file():
            copy_and_process_file(item, dest_path)
        elif item.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)


def create_cookiecutter_json() -> None:
    """Create the cookiecutter.json configuration file."""
    config_path = OUTPUT_DIR / "cookiecutter.json"
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(COOKIECUTTER_CONFIG, f, indent=2)
    
    print(f"Created {config_path}")


def create_gitignore() -> None:
    """Create a .gitignore file in the template root."""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
*.log

# Poetry
poetry.lock

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project specific
prototyping/
scratchpads/

# user specific
mypy.ini
"""
    
    gitignore_path = TEMPLATE_ROOT / ".gitignore"
    gitignore_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(gitignore_path, 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    
    print(f"Created {gitignore_path}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("Cookiecutter Template Generator")
    print("=" * 60)
    
    # Clean up old output if it exists
    if OUTPUT_DIR.exists():
        print(f"\nRemoving existing {OUTPUT_DIR}...")
        shutil.rmtree(OUTPUT_DIR)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Created output directory: {OUTPUT_DIR}")
    
    # Create cookiecutter.json
    print("\nCreating cookiecutter.json...")
    create_cookiecutter_json()
    
    # Copy and process directory structure
    print("\nCopying and processing files...")
    copy_directory_structure(SOURCE_DIR, TEMPLATE_ROOT)
    
    # Create .gitignore in template root
    print("\nCreating .gitignore...")
    create_gitignore()
    
    print("\n" + "=" * 60)
    print("✓ Cookiecutter template generated successfully!")
    print("=" * 60)
    print(f"\nOutput location: {OUTPUT_DIR}")
    print("\nTo test the generated template:")
    print(f"  cookiecutter {OUTPUT_DIR}")
    print("\nTo customize default values, edit:")
    print(f"  {OUTPUT_DIR / 'cookiecutter.json'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
