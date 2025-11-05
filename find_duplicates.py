#!/usr/bin/env python3
"""Find duplicate function definitions in src/"""

import os
import re
from collections import defaultdict

def find_function_defs(directory):
    """Find all function definitions and their locations"""
    func_locations = defaultdict(list)

    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ directories
        if '__pycache__' in root:
            continue

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        for line_num, line in enumerate(f, 1):
                            # Match function definitions at start of line
                            match = re.match(r'^def\s+(\w+)\s*\(', line)
                            if match:
                                func_name = match.group(1)
                                func_locations[func_name].append((filepath, line_num))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

    return func_locations

def main():
    func_locations = find_function_defs('src')

    # Find duplicates (functions appearing more than once)
    duplicates = {name: locs for name, locs in func_locations.items() if len(locs) > 1}

    if duplicates:
        print(f"Found {len(duplicates)} duplicate functions:\n")
        for func_name in sorted(duplicates.keys()):
            locs = duplicates[func_name]
            print(f"=== {func_name} ({len(locs)} occurrences) ===")
            for filepath, line_num in sorted(locs):
                print(f"  {filepath}:{line_num}")
            print()
    else:
        print("No duplicates found!")

if __name__ == '__main__':
    main()
