#!/usr/bin/env bash

echo copying git pre-commit hook script
cp /home/klapaucius/.pre-commit /home/klapaucius/workspace/.git/hooks/pre-commit

# keep poetry envs up to date
echo "Installing poetry environments..."
find /home/klapaucius/workspace -name "pyproject.toml" -type f | while read -r lockfile; do
    poetry_dir=$(dirname "$lockfile")
    echo "Installing dependencies in: $poetry_dir"
    cd "$poetry_dir" && poetry install --all-extras --all-groups
    if [ $? -eq 0 ]; then
        echo "✓ Successfully installed dependencies in $poetry_dir"
    else
        echo "✗ Failed to install dependencies in $poetry_dir"
    fi
done
