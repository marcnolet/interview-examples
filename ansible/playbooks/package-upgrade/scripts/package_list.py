#!/usr/bin/env python3
"""
This script generates a YAML file containing a list of packages.

It provides functions to:
- Write packages to a YAML file
- Validate folder paths
- Generate a package YAML file from a comma-separated list of packages

The main functionality can be accessed through the command line interface,
which accepts a comma-separated list of packages and an optional folder path.

Usage:
    python package_list.py <packages> [-f <folder>]

Example:
    python package_list.py "package1,package2,package3" -f "/path/to/folder"

The script will create a 'packages.yaml' file with the specified packages
and optionally move it to the specified folder.
"""

import argparse
import os
import sys
from typing import List, Optional
import yaml


def write_packages_to_yaml(packages: List[str], output_file: str) -> None:
    """
    This function creates a YAML file with the given packages listed under the 'packages' key.
    The YAML file starts with a '---' line and uses the default flow style for better readability.

    Args:
        packages (List[str]): A list of package names to be written to the YAML file.
        output_file (str): The name of the output YAML file.

    Returns:
        None
    """

    data = {"packages": packages}
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("---\n")
        yaml.dump(data, f, default_flow_style=False)


def validate_folder(folder_path: str) -> None:
    """
    Validate if the given folder path exists.

    Args:
        folder_path (str): The path of the folder to validate.

    Raises:
        SystemExit: If the folder does not exist, the script will exit with an error message.

    Returns:
        None
    """

    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.", file=sys.stderr)
        sys.exit(1)


def generate_package_yaml(packages: str, folder: Optional[str] = None) -> str:
    """
    Generate a YAML file containing a list of packages and optionally move it to a specified folder.

    This function takes a comma-separated string of package names, removes duplicates, 
    and writes them to a YAML file. If a folder is specified, it moves the file to that folder.

    Args:
        packages (str): A comma-separated string of package names.
        folder (Optional[str], optional): The folder path to move the generated file. 
        Defaults to None.

    Returns:
        str: The path to the generated YAML file.

    Raises:
        SystemExit: If the specified folder does not exist.
    """

    packages = [pkg.strip() for pkg in set(packages.split(','))]
    output_file = "packages.yaml"

    write_packages_to_yaml(packages, output_file)

    if folder:
        validate_folder(folder)
        new_path = os.path.join(folder, output_file)
        os.rename(output_file, new_path)
        return new_path

    return output_file


def main() -> None:
    """
    Main function to parse command-line arguments and generate a packages.yaml file.

    This function sets up an argument parser to handle user input, processes the
    arguments, and calls the generate_package_yaml function with the provided
    packages and optional folder path. It then prints the path of the created file.

    Returns:
        None
    """

    parser = argparse.ArgumentParser(description="Generate packages.yaml file csv style arguments")
    parser.add_argument("packages", help="Comma-separated list of packages")
    parser.add_argument("-f", "--folder", help="Optional folder path to move the generated file")
    args = parser.parse_args()

    result = generate_package_yaml(args.packages, args.folder)
    print(f"File '{result}' has been created")


if __name__ == "__main__":
    main()
