#!/usr/bin/env python3
"""
This script manages the patching process for GCP systems.

It includes classes for configuration management (ConfigManager),
inventory management (InventoryManager), playbook execution (PlaybookRunner),
and overall patch management (PatchManager).

The script handles tasks such as:
- Parsing command-line arguments
- Setting up directory structures
- Generating and managing patch groups
- Executing Ansible playbooks for patching
- Processing retry files
- Validating inputs and configurations

Usage:
    python begin_patch.py <region> <packages> [options]

The script can be run in debug mode or normal mode, and supports
various options for customizing the patching process.
"""

import os
import stat
import sys
import re
import shutil
import argparse
import random
import subprocess
from datetime import datetime
from typing import List
from package_list import generate_package_yaml
from patch_groups import generate_patch_groups


class ConfigManager:
    """
    ConfigManager class handles configuration settings and directory.

    Attributes:
        current_time (str): Current timestamp in 'YYYYMMDD-HHMMSS' format.
        main_dir (str): Main directory name for the patching process.
        home_dir (str): User's home directory path.
        main_dir_path (str): Full path to the main directory.
        vars_dir (str): Path to the variables directory.
        logs_dir (str): Path to the logs directory.
        script_dir (str): Path to the script directory.
        playbook_dir (str): Path to the playbook directory.
        skip_host_file (str): Path to the skip host file.
        skip_role_file (str): Path to the skip role file.
        setup_vars_file (str): Path to the setup variables file.
        region (str): Region for the patching process.

    Methods:
        create_directories(): Creates the necessary directory structure.
        create_setup_vars_file(): Creates the setup variables file with YAML content.
        append_skip_file(hostnames, skiptype): Appends hostnames to a skip file.
    """

    def __init__(self, region):
        self.current_time = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.main_dir = f"patch-{self.current_time}"
        self.home_dir = os.path.expanduser("~")
        self.main_dir_path = os.path.join(self.home_dir, self.main_dir)
        self.vars_dir = os.path.join(self.main_dir_path, "vars")
        self.logs_dir = os.path.join(self.main_dir_path, "logs")
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.playbook_dir = os.path.dirname(self.script_dir)
        self.skip_host_file = os.path.join(self.vars_dir, "skiphost")
        self.skip_role_file = os.path.join(self.vars_dir, "skiprole")
        self.setup_vars_file = os.path.join(self.vars_dir, "setupvars.yaml")
        self.region = region

    def create_directories(self) -> None:
        """
        This method creates the following necessary directories for the patching process 
        if they don't already exist and doesn't raise an error if they do.
        """

        os.makedirs(self.main_dir_path, exist_ok=True)
        os.makedirs(self.vars_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        print(f"Created folder structure in: {self.main_dir_path}")

    def create_setup_vars_file(self) -> None:
        """
        This method generates a YAML file the path specified by self.setup_vars_file 
        containing setup variables if it doesn't already exist.
        """

        if not os.path.exists(self.setup_vars_file):
            with open(self.setup_vars_file, 'w', encoding='utf-8') as f:
                yaml_content = f"""
region: {self.region}
setup_dir: {self.main_dir_path}
setup_vars_dir: {self.vars_dir}
logs_dir: {self.logs_dir}
"""
                f.write(yaml_content.strip())
            print(f"Created setup.yaml in {self.vars_dir}")

    def append_skip_file(self, hostnames: List[str], skiptype: str) -> None:
        """
        This method takes a list of hostnames and appends unique entries to appropriate skip file.
        Each hostname is written on a new line after being stripped of leading/trailing whitespace.
        """

        if skiptype == "host":
            skip_file = self.skip_host_file
        else:
            skip_file = self.skip_role_file

        existing_hosts = set()
        if os.path.exists(skip_file):
            with open(skip_file, 'r', encoding='utf-8') as f:
                existing_hosts = set(line.strip() for line in f)

        with open(skip_file, 'a', encoding='utf-8') as f:
            for hostname in hostnames:
                hostname = hostname.strip()
                if hostname not in existing_hosts:
                    f.write(f"{hostname}\n")
                    existing_hosts.add(hostname)

        print(f"Appending unique hostnames to {skip_file}")


class InventoryManager:
    """
    Manages inventory-related operations for patching processes.

    This class handles the generation and management of patch groups,
    as well as file validation and patch group counting.

    Attributes:
        config (ConfigManager): Configuration manager instance.

    Methods:
        generate_and_move_patch_groups(): Generates patch groups and moves the file.
        validate_file(file_path): Validates existence and permissions of a file.
        count_patch_groups(file_path): Counts the number of patch groups in a file.
    """

    def __init__(self, config_manager):
        self.config = config_manager

    def generate_and_move_patch_groups(self) -> str:
        """
        Generates patch groups and moves the resulting file to the appropriate directory.

        This method performs the following steps:
        1. Generates patch groups using the `generate_patch_groups()` function.
        2. Validates the generated patch group file.
        3. Moves the file to the specified variables directory.

        Returns:
            str: The new path of the moved patch group file.

        Raises:
            FileNotFoundError: If the patch group file was not created or is empty.
            SystemExit: If an error occurs during patch group generation or file moving.
        """
        generate_patch_groups()

        patch_group_file = f"patch-groups-{self.config.region}.yaml"

        try:
            if self.validate_file(patch_group_file):
                patch_group_new_path = os.path.join(self.config.vars_dir, patch_group_file)
                shutil.move(patch_group_file, patch_group_new_path)
                print(f"File '{patch_group_file}' has been moved to {self.config.vars_dir}")
        except (shutil.Error, OSError) as e:
            print(f"Error moving patch group file: {str(e)}")
            sys.exit(1)

        return patch_group_new_path

    @staticmethod
    def validate_file(file_path: str) -> bool:
        """
        This method checks if the file exists, is a regular file, is not empty,
        and has the necessary read permissions and prints error messages to stdout
        for each validation failure.
        """

        if not os.path.exists(file_path):
            print(f"File does not exist: {file_path}")
            return False

        if not os.path.isfile(file_path):
            print(f"Path is not a file: {file_path}")
            return False

        if os.path.getsize(file_path) == 0:
            print(f"File is empty: {file_path}")
            return False

        if not os.access(file_path, os.R_OK):
            print(f"File is not readable: {file_path}")
            return False

        file_stats = os.stat(file_path)
        if not file_stats.st_mode & stat.S_IRUSR:
            print(f"File does not have read permissions for the owner: {file_path}")
            return False

        return True

    @staticmethod
    def count_patch_groups(file_path: str) -> int:
        """
        This method reads the content of the file at the given path, counts
        the occurrences of patch group identifiers (e.g., 'pg1:', 'pg2:') and
        returns an integer of the number of the number of patch groups found.
        """

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return len(re.findall(r'pg\d+:', content))


class PlaybookRunner:
    """
    PlaybookRunner class for executing Ansible playbooks and processing retry files.

    This class is responsible for running Ansible playbooks with specified configurations,
    environment variables, and command-line arguments. It also handles the processing
    of retry files generated during playbook execution.

    Attributes:
        config (ConfigManager): An instance of ConfigManager for accessing configuration settings.

    Methods:
        run_patch_playbook: Executes an Ansible playbook with the given parameters.
        process_retry_file: Processes the retry file and updates skip file with failed hosts.
    """

    def __init__(self, config_manager):
        self.config = config_manager

    def run_patch_playbook(self, patchgroup: str, inv_file: str, creds: str, exvars: str,
                           debug: bool = False) -> None:
        """
        Executes an Ansible playbook for patch management.

        Args:
            patchgroup (str): The patch group to be processed.
            inv_file (str): Path to the inventory file.
            creds (str): Credentials for Ansible execution.
            exvars (str): Extra variables for the playbook.
            debug (bool, optional): If True, prints the command without executing. 
            Defaults to False.

        This method sets up the Ansible environment variables, constructs the command to run
        the playbook, and executes it. It also processes any retry files generated during
        the playbook execution.

        If debug is True, it only prints the command without executing it.
        If an error occurs during execution, it catches and prints the error message.

        After execution, it processes the retry file and updates the skiprole file if necessary.

        Note: "tree" callbacks require ansible-core >= 2.11
        """

        ans_vars = {
            'ANSIBLE_RETRY_FILES_ENABLED': 'True',
            'ANSIBLE_CALLBACKS_ENABLED': 'tree,timer',
            'ANSIBLE_LOG_PATH': f"{self.config.logs_dir}/patch-{patchgroup}.log",
            'ANSIBLE_DISPLAY_SKIPPED_HOSTS': 'False',
            'ANSIBLE_CALLBACK_TREE_DIR': f'{self.config.logs_dir}'
        }

        env = os.environ.copy()
        env.update(ans_vars)

        cmd = [
            'ansible-playbook',
            '-i', inv_file,
            '-i', '/etc/ansible/inventory.gcp.yaml',
            *creds.split(),
            '-e', f'@{self.config.setup_vars_file}',
            '-e', f'{{"host_list": ["{patchgroup}"]}}',
            '-e', f'{{{exvars}}}',
            f'{self.config.playbook_dir}/main.yaml'
        ]

        if debug:
            print(f"Debug: {' '.join(cmd)}")
        else:
            try:
                print(f"Executing: {' '.join(cmd)}")
                subprocess.run(cmd, env=env, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error executing patch playbook: {e}")

        retry_hostlist = self.process_retry_file()
        if retry_hostlist:
            print(f"Processed .retry file and added {len(retry_hostlist)} hosts to skiprole file\n")

    def process_retry_file(self) -> List[str]:
        """
        Process the retry file generated during playbook execution.

        This method searches for a .retry file in the playbook directory,
        reads its contents, and adds the listed hosts to the skiprole file.

        Returns:
            list: A list of hostnames found in the retry file.
        """

        hostlist = []
        skiptype = "role"

        for file in os.listdir(self.config.playbook_dir):
            if file.endswith(".retry"):
                retry_file_path = os.path.join(self.config.playbook_dir, file)
                if InventoryManager.validate_file(retry_file_path):
                    with open(retry_file_path, 'r', encoding='utf-8') as f:
                        hostlist = [line.strip() for line in f if line.strip()]

                    if hostlist:
                        self.config.append_skip_file(hostlist, skiptype)
                    break

        return hostlist


class PatchManager:
    """
    PatchManager class for initializing and managing the patching process.

    This class handles the following responsibilities:
    - Parsing command-line arguments
    - Validating and setting up the patching environment
    - Running the patch playbook in either debug or normal mode

    The class uses ConfigManager, InventoryManager, and PlaybookRunner to manage
    configuration, inventory, and playbook execution respectively.

    Attributes:
        args: Parsed command-line arguments
        config: ConfigManager instance
        inventory: InventoryManager instance
        playbook_runner: PlaybookRunner instance

    Methods:
        parse_arguments: Parse command-line arguments
        validate_and_setup: Validate inputs and set up the environment
        validate_region: Validate the provided region format
        get_exvars: Get extra variables based on command-line flags
        get_creds: Get credentials for playbook execution
        run_debug_mode: Run the patch playbook in debug mode
        run_normal_mode: Run the patch playbook in normal mode
        run: Main method to execute the patching process
    """

    def __init__(self):
        self.args = self.parse_arguments()
        self.config = ConfigManager(self.args.region if self.args.region else "default")
        self.inventory = InventoryManager(self.config)
        self.playbook_runner = PlaybookRunner(self.config)

    @staticmethod
    def parse_arguments() -> argparse.Namespace:
        """
        Parse command-line arguments for the patching process.

        Returns:
            argparse.Namespace: An object containing the parsed arguments.

        The following arguments are supported:
        - region: Region in the GCP format <geography>-<region><number>
        - packages: Packages to be upgraded
        - --pkgcheck: Get current package versions and show what will change post upgrade
        - --upgrade: Upgrade packages and reboot hosts if required
        - --upgradepkgsonly: Upgrade packages but don't reboot hosts even if required
        - --nocreds: Don't use the default GCP environment credentials
        - --askpass: Prompt for SSH connection password
        - --askpassbecome: Prompt for SSH connection password and become password
        - -g/--grouplist: Comma-separated list of hosts or host groups to patch
        - -i/--inventory: Override the generated patch-groups file with a custom inventory
        - -s/--skiphost: Comma-separated list of hostnames to skip
        - --debug: Run in debug mode
        """

        parser = argparse.ArgumentParser(description="Initialize patching process")
        parser.add_argument("packages",
                            help="Packages to be upgraded")
        parser.add_argument("--pkgcheck", action="store_true", default=False,
                            help="Get current package versions and show what will change post \
                                upgrade")
        parser.add_argument("--upgrade", action="store_true", default=False,
                            help="Upgrade packages and reboot hosts if required")
        parser.add_argument("--upgradepkgsonly", action="store_true", default=False,
                            help="Upgrade packages but don't reboot hosts even if required \
                                (check for required reboots only)")
        parser.add_argument("--nocreds", action="store_true", default=False,
                            help="Don't use the default GCP credentials and run the \
                                playbook with no credentials")
        parser.add_argument("--askpass", action="store_true", default=False,
                            help="Passes '-k' flag to Ansible to prompt for SSH connection \
                                password")
        parser.add_argument("--askpassbecome", action="store_true", default=False,
                            help="Passes '-kK' flags to Ansible to prompt for SSH connection \
                                password and become password")
        parser.add_argument("-g", "--grouplist",
                            help="Comma-separated list of hosts or host groups to patch")
        parser.add_argument("-i", "--inventory",
                            help="Override the generated patch-groups file with a filepath \
                            to your own inventory")
        parser.add_argument("-r", "--region",
                            help="Region in the GCP format <geography>-<region><number>")
        parser.add_argument("--skiphost",
                            help="Comma-separated list of hostnames to skip hostname")
        parser.add_argument("--skiprole",
                            help="Comma-separated list of hostnames to skip by common role")
        parser.add_argument("--debug", action="store_true",
                            help="Displays the Ansible commands without running them")
        args = parser.parse_args()

        if not args.inventory and not args.region:
            parser.error("region is required when not using -i/--inventory")

        return args

    def validate_and_setup(self) -> None:
        """
        Validate inputs and set up the patching environment.

        This method performs the following tasks:
        - Validates the inventory file if provided
        - Validates the region format (GCP format)
        - Creates necessary directories
        - Creates the setup variables file
        - Appends hosts to skip files if specified
        - Generates a package YAML file

        Raises:
            Exception: If there's an error generating the package YAML file
        """

        if self.args.inventory:
            self.inventory.validate_file(self.args.inventory)
        else:
            self.validate_region()

        self.config.create_directories()
        self.config.create_setup_vars_file()

        if self.args.skiphost:
            skiptype = "host"
            skiplist = [hostname.strip() for hostname in self.args.skiphost.split(',')]
            self.config.append_skip_file(skiplist, skiptype)

        if self.args.skiprole:
            skiptype = "role"
            skiplist = [hostname.strip() for hostname in self.args.skiprole.split(',')]
            self.config.append_skip_file(skiplist, skiptype)

        package_file = generate_package_yaml(self.args.packages, self.config.vars_dir
                                             if self.config else None)
        print(f"Created '{package_file}' file")

    def validate_region(self) -> None:
        """
        This method checks if the provided region matches the GCP region format:
        <geography>-<region><number> (e.g., us-central1). If the region format is
        invalid, it prints an error message and exits.
        """

        region_pattern = r'^[a-z]+-[a-z]+\d+'
        if not re.match(region_pattern, self.args.region):
            print(f"Invalid region format: {self.args.region}")
            print("Region should be in the format: <geography>-<region><number>")
            print("Example: us-central1")
            sys.exit(1)

    def get_exvars(self) -> str:
        """
        Generates extra variables for Ansible playbook execution based on command-line arguments.

        Returns:
            str: A string containing Ansible extra variables based on the following conditions:
                - If --pkgcheck is specified, returns "run_pkgcheck: true"
                - If --upgradepkgsonly is specified, returns variables for upgrade without reboot
                - If --upgrade is specified, returns variables for upgrade with potential reboot
                - Otherwise, returns variables for pre-checks and host validations

        Note:
            This method also prints informational messages about the selected operation mode.
        """

        if self.args.pkgcheck:
            if self.args.upgrade or self.args.upgradepkgsonly:
                print("Warning: Upgrade flag cannot be used with pkgcheck. Running pkgcheck only!")
            return "run_pkgcheck: true"

        if self.args.upgradepkgsonly:
            print("Info: Upgrade packages only. Skipping reboots even if required.")
            return "run_precheck: true, run_upgrade: true, reboot_if_required: false"

        if self.args.upgrade:
            print("Info: Upgrade packages and rebooting hosts if required.")
            return "run_precheck: true, run_upgrade: true"

        print("Info: Running pre-checks and host validations")
        return "run_precheck: true, run_upgrade: false"

    def get_creds(self) -> str:
        """
        Get credentials for Ansible playbook execution.

        This method determines the credentials to be used based on command-line arguments:
        - If --nocreds is specified, returns an empty string (no credentials).
        - If --askpass is specified, returns "-k" to prompt for SSH password.
        - If --askpassbecome is specified, returns "-kK" to prompt for SSH and sudo passwords.
        - Otherwise, returns credentials using DEPLOY environment variable and SSH key.

        Returns:
            str: A string containing the appropriate credential options for Ansible.
        """

        if self.args.nocreds:
            return ""

        if self.args.askpass:
            return "-k"

        if self.args.askpassbecome:
            return "-kK"

        ans_user = os.environ.get('DEPLOY')
        ans_key = os.path.join(self.config.home_dir, '.ssh', 'deploy')
        return f'--user {ans_user} --private-key {ans_key}'

    def run_debug_mode(self) -> None:
        """
        Run the patch playbook in debug mode.

        This method executes the patch playbook with debug settings enabled. It handles both
        inventory-based and non-inventory-based scenarios, running the playbook for specified
        host groups or randomly generated patch groups.

        The method uses the extra variables and credentials obtained from get_exvars() and
        get_creds() methods respectively. It also respects the --grouplist argument if provided.

        In non-inventory mode, it generates a random number of patch groups (1-6) and runs
        the playbook for each which simply prints the command to be executed without 
        actually running the playbook.

        Raises:
            ValueError: If the inventory file doesn't contain valid patch groups.
        """

        exvars = self.get_exvars()
        creds = self.get_creds()

        if self.args.inventory:
            patch_group_file = self.args.inventory
            if self.args.grouplist:
                hostlist = self.args.grouplist.strip("'\"")
                self.playbook_runner.run_patch_playbook(hostlist, patch_group_file, creds, exvars,
                                                        debug=self.args.debug)
            else:
                try:
                    num_patch_groups = self.inventory.count_patch_groups(patch_group_file)
                    if num_patch_groups <= 0:
                        raise ValueError("Inventory file must have one or more defined patch \
                                         groups with the group in the format \"pg#\". \
                                         Example: pg1, pg2, pg3")
                except ValueError as e:
                    print(f"Error: {str(e)}")
                    sys.exit(1)
                for i in range(1, num_patch_groups + 1):
                    self.playbook_runner.run_patch_playbook(f"pg{i}", patch_group_file, creds,
                                                            exvars, debug=self.args.debug)
        else:
            patch_group_file = f"{self.config.vars_dir}/patch-groups-{self.args.region}.yaml"
            num_patch_groups = random.randint(1, 6)
            for i in range(1, num_patch_groups + 1):
                self.playbook_runner.run_patch_playbook(f"pg{i}", patch_group_file, creds,
                                                        exvars, debug=self.args.debug)

    def run_normal_mode(self) -> None:
        """
        Run the patch playbook in normal mode.

        This method executes the patch playbook with standard settings. It handles both
        inventory-based and non-inventory-based scenarios, running the playbook for specified
        host groups or all patch groups in the inventory.

        The method uses the extra variables and credentials obtained from get_exvars() and
        get_creds() methods respectively. It also respects the --grouplist argument if provided.

        In non-inventory mode, it generates a patch group file and runs the playbook for each
        patch group or the specified hostlist.

        Raises:
            ValueError: If the inventory file doesn't contain valid patch groups.
        """

        exvars = self.get_exvars()
        creds = self.get_creds()

        if self.args.inventory:
            patch_group_file = self.args.inventory
            if self.args.grouplist:
                hostlist = self.args.grouplist.strip("'\"")
                self.playbook_runner.run_patch_playbook(hostlist, patch_group_file, creds, exvars)
            else:
                try:
                    num_patch_groups = self.inventory.count_patch_groups(patch_group_file)
                    if num_patch_groups <= 0:
                        raise ValueError("Inventory file must have one or more defined patch \
                                         groups with the group in the format \"pg#\". \
                                         Example: pg1, pg2, pg3")
                except ValueError as e:
                    print(f"Error: {str(e)}")
                    sys.exit(1)
                for i in range(1, num_patch_groups + 1):
                    self.playbook_runner.run_patch_playbook(f"pg{i}", patch_group_file, creds,
                                                            exvars)
        else:
            patch_group_file = self.inventory.generate_and_move_patch_groups()
            if self.args.grouplist:
                hostlist = self.args.grouplist.strip("'\"")
                self.playbook_runner.run_patch_playbook(hostlist, patch_group_file, creds, exvars)
            else:
                num_patch_groups = self.inventory.count_patch_groups(patch_group_file)
                for i in range(1, num_patch_groups + 1):
                    self.playbook_runner.run_patch_playbook(f"pg{i}", patch_group_file, creds,
                                                            exvars)

    def run(self) -> None:
        """
        This method performs the following steps:
        1. Validates input and sets up the environment.
        2. Runs in debug mode if the debug flag is set.
        3. Otherwise, runs in normal mode.

        Raises:
            ValueError: If there's an issue with input validation or setup.
        """

        try:
            self.validate_and_setup()

            if self.args.debug:
                self.run_debug_mode()
            else:
                self.run_normal_mode()
        except ValueError as e:
            print(f"Error: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    PatchManager().run()
