#!/usr/bin/env python3
"""
Generates patch groups for upgrading packages across different roles and regions.

This script performs the following tasks:
1. Retrieves the list of compute instances from Google Cloud Platform.
2. Groups the instances by role and region.
3. Generates patch groups for upgrading packages, considering the following rules:
   - Non-sharddb roles are distributed evenly across patch groups.
   - Sharddb roles are handled separately, with special allocation rules.
4. Creates patch group files for each region.

The script supports a --debug flag for additional output during execution.

Usage:
    python3 patch_groups.py [--debug]

Requirements:
    - Google Cloud SDK (gcloud) must be installed and configured.
    - A 'scope' file must exist in the same directory, containing the scope for instance filtering.

Output:
    - Creates 'patch-groups-{region}' files for each region, containing the patch group allocations.
"""

import argparse
import subprocess
import json
from collections import defaultdict
from typing import List, Dict
import yaml


def get_gcloud_config(setting: str) -> str:
    """
    Retrieves and returns the project id of a the current Google Cloud configuration setting.

    Raises:
        subprocess.CalledProcessError: If the gcloud command fails.
    """

    return subprocess.check_output(f"gcloud config get-value {setting}", \
                                   shell=True).decode().strip()


def read_scope_file() -> List[str]:
    """
    Reads and returns the content of the 'scope' file.

    Returns:
        A list of strings, where each string is a line from the 'scope' file.
    """

    with open("scope", "r", encoding='utf-8') as f:
        return f.read().strip().split()


def get_hosts() -> Dict[str, Dict[str, List[str]]]:
    """
    Retrieves and organizes compute instances from Google Cloud Platform.

    This function performs the following tasks:
    1. Gets the current GCP project ID.
    2. Reads the scope from the 'scope' file.
    3. Executes a gcloud command to list compute instances based on the scope and project.
    4. Organizes the instances by role and region.
    5. Reverses the order of hosts for each role in each region.

    Returns:
        A nested dictionary where the outer key is the region, the inner key is the role,
        and the value is a list of host names, reversed from their original order.
    """

    project_id = get_gcloud_config("project")
    scope = " OR ".join(read_scope_file())

    cmd = f"gcloud compute instances list \
            --project={project_id} \
            --filter=\"({scope}) AND NOT status:TERMINATED\" \
            --sort-by=name --format=json"
    instances = json.loads(subprocess.check_output(cmd, shell=True))

    hosts_by_role_and_region = defaultdict(lambda: defaultdict(list))
    for instance in instances:
        role = next((v for k, v in instance['labels'].items() if k.startswith('role')), None)
        region = instance['labels'].get('region', 'unknown')
        if role:
            hosts_by_role_and_region[region][role].append(instance['name'])

    # Reverse the order of hosts for each role in each region
    for region in hosts_by_role_and_region:
        for role in hosts_by_role_and_region[region]:
            hosts_by_role_and_region[region][role].reverse()

    return hosts_by_role_and_region


def create_patch_groups(hosts_by_role: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Generates patch groups from the given hosts by role.

    This function performs the following tasks:
    1. Separates non-sharddb roles from sharddb roles.
    2. Creates patch groups for non-sharddb roles, distributing hosts evenly in reverse order.
    3. Handles sharddb roles separately, placing them in patch groups 1 and 2.

    Args:
        hosts_by_role (dict): A dictionary where keys are role names and values are lists of hosts.

    Returns:
        dict: A dictionary of patch groups, where keys are group names (e.g., "pg1", "pg2")
              and values are lists of hosts in that group.
    """

    non_sharddb_roles = {role: hosts for role, hosts in hosts_by_role.items() \
                         if role != "be-sharddb"}
    max_hosts = max(len(hosts) for hosts in non_sharddb_roles.values()) if non_sharddb_roles else 0
    patch_groups = defaultdict(list)

    for i in range(max_hosts):
        for role, hosts in non_sharddb_roles.items():
            if i < len(hosts):
                patch_groups[f"pg{i+1}"].append(hosts[i])

    if "be-sharddb" in hosts_by_role:
        sharddb_hosts = hosts_by_role["be-sharddb"]
        if len(sharddb_hosts) == 1:
            patch_groups["pg1"].extend(sharddb_hosts)
        else:
            mid = len(sharddb_hosts) // 2
            patch_groups["pg2"].extend(sharddb_hosts[:mid])
            patch_groups["pg1"].extend(sharddb_hosts[mid:])

    return dict(patch_groups)


def create_patch_group_files(patch_groups: Dict[str, List[str]], region: str) -> None:
    """
    Creates a file containing patch groups for a specific region.

    This function writes the patch groups to a file named 'patch-groups-{region}'.
    Each patch group is written as a YAML-like structure with the group name,
    followed by the hosts in that group.

    Args:
        patch_groups (dict): A dictionary of patch groups, where keys are group names
                            and values are lists of hosts in that group.
        region (str): The region for which the patch groups are being created.
    """

    filename = f"patch-groups-{region}.yaml"
    with open(filename, "w", encoding='utf-8') as f:
        for group, hosts in patch_groups.items():
            f.write(f"{group}:\n")
            f.write("  hosts:\n")
            for host in hosts:
                f.write(f"    {host}:\n")


def generate_patch_groups(debug: bool = False) -> None:
    """
    Generate patch groups for all regions and create patch group files.

    This function retrieves hosts by role and region, creates patch groups for each region,
    and writes the patch groups to files. If debug mode is enabled, it prints additional
    information about hosts and patch groups.

    Args:
        debug (bool, optional): Enable debug output. Defaults to False.
    """

    hosts_by_role_and_region = get_hosts()
    if debug:
        print("Hosts by role and region:")
        print(json.dumps(hosts_by_role_and_region, indent=2))

    for region, hosts_by_role in hosts_by_role_and_region.items():
        patch_groups = create_patch_groups(hosts_by_role)
        if debug:
            print(f"\nPatch groups for region {region}:")
            print(json.dumps(patch_groups, indent=2))

        create_patch_group_files(patch_groups, region)


def main() -> None:
    """
    Main function to parse command line arguments and generate patch groups.

    This function sets up an argument parser to handle the '--debug' flag,
    parses the command line arguments, and calls the generate_patch_groups
    function with the debug option.

    Returns:
        None
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    generate_patch_groups(args.debug)


if __name__ == "__main__":
    main()
