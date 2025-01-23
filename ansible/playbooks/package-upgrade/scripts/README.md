# README

This page describes the files only within the **scripts** folder. For more information about the playbook, see the README file in the parent **package-upgrade** folder.

###
# Upgrade Orchestrator (begin_patch.py)

This script serves as a comprehensive tool for initializing, configuring, and executing the patching process for GCP systems, providing flexibility and control over various aspects of the operation. See `./begin_patch -h` for available options.

###
# Orchestration Features
The script uses of several key Ansible configurations in the `run_patch_playbook()` function by setting temporary environment variables when running the playbook.

- `ANSIBLE_RETRY_FILES_ENABLED: 'True'` - Enables Ansible's built-in '.retry' file feature to track instances that failed tasks during the playbook run.
- `ANSIBLE_CALLBACKS_ENABLED: 'tree,timer'` - Enables the Ansible callback plugins for displaying a timer providing the total runtime and the task execution tree summary.
- `ANSIBLE_LOG_PATH: "{self.config.logs_dir}/patch-{patchgroup}.log"` - Sets the path for the Ansible log file.
- `ANSIBLE_DISPLAY_SKIPPED_HOSTS: 'False'` - Disables the display of skipped hosts during the playbook run.
- `ANSIBLE_CALLBACK_TREE_DIR': f'{self.config.logs_dir}'` - Sets the directory for the Ansible task execution tree summary.

**Note**  
The [tree](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/tree_callback.html) callback generates a file per instance, with the hostname for the filename, in the specified directory containing a task summary for the corresponding host. For this playbook, the contents typically contain details of a successful upgrade or the reason for a failure, including the failed task and error messages. This feature is only available in Ansible-core 2.11.0 or later versions.

###
# Running The Orchestrator

### Generating a dynamic patch-groups inventory file
Required parameters:
- **[ packages ]** - list of packages to check or upgrade, comma-separated (e.g., "vim,wget,curl")
- `-r` or `--region` -  the region where the patching will be performed (e.g., "us-central1")

### Using a custom inventory file
Required parameters:
- **[ packages ]** - list of packages to check or upgrade, comma-separated (e.g., "vim,wget,curl")

### About the orchestrator script

1. Parses command-line arguments for the region, packages, and various options.
2. Sets up the necessary directory structure for the patching process ( *${HOME}/patch-{yyyymmdd-hhmmss}/* ).
3. Validates the provided region format ([ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html)).
4. Creates configuration files and variables for the patching process.
5. Generates a package YAML file based on the specified packages.
6. Handles host exemptions by appending them to a 'skiphost' or 'skiprole' file.
7. Generates patch groups and manages the inventory.
8. Executes Ansible playbooks for patching with appropriate configurations.
9. Processes retry files generated during playbook execution.
10. Manages credentials for Ansible execution.
11. Supports both debug and normal execution modes.
12. Allows for custom inventory files or generates patch groups automatically.
13. Provides options for package checking and upgrading with or without reboots.
14. Handles different credential scenarios (no credentials, password prompts, or default credentials).
15. Logs the patching process and stores output in specified directories.

### Setup
1. Determine what packages need upgrading.
2. Determine which environment and region of GCP instances need patching.
3. Login to the relevant Ansible controller.
4. Become the deploy user (e.g., `sudo su - deploy`).
5. Navigate to the **scripts** directory within the **package-upgrade** playbook (controller default location: "${HOME}/ansible/playbooks/package-upgrade/scripts")

###
# Running A Controlled Regional Package Upgrade (every instance by generated patch group)
Enabled with rebooting when running `begin_patch.py` with `--upgrade`.
* Runs playbook with: "run_precheck: true", "upgrade_if_installed: true", and "reboot_if_required: true"
* Playbook sets "run_validation: true"

Enabled without rebooting when running `begin_patch.py` with `--upgradepkgsonly`.
* Runs playbook with: "run_precheck: true", "upgrade_if_installed: true", and "reboot_if_required: false"
* Playbook sets "run_validation: true"

### Playbook Behavior
1. Runs host and group guardrail checks.
2. Runs pre-checks (package checks, reboot-required check, gets change info, service validation health checks)
3. Upgrades only on installed packages.
4. Initiates instance reboot if `--upgrade` passed and a reboot-required flag detecte (skips this step if `--upgradepkgsonly` passed).
5. Runs post-upgrade service validation health checks.
6. Attempts to start any down services discovered (see "Role: Validation" in parent README for details)

### Reboot (if required)
`./begin_patch.py "vim,wget,curl" -r us-central1 --upgrade`

### Don't reboot (even if required)
`./begin_patch.py "vim,wget,curl" -r us-central1 --upgradepkgsonly`

## Alternative Patching Methods

### One generated patch group (pg1, pg2, pg3, etc)
`./begin_patch.py "vim,wget,curl" -r us-central1 -g pg1 --upgrade`

### One role type (performs ordered upgrade by patch group)
`./begin_patch.py "vim,wget,curl" -r us-central1 -g label_role_be_kafka --upgrade`

### Multiple role types (performs ordered upgrade by patch group)
`./begin_patch.py "vim,wget,curl" -r us-central1 -g "label_role_be_kafka,label_role_be_coredb" --upgrade`

### Upgrade a single instance
`./begin_patch.py "vim,wget,curl" -r us-central1 -g kafka-dev-us-central1-1 --upgrade`

###
# Package Check (--pkgcheck)
Calling `begin_patch.py` with the `--pkgcheck` argument will run the package checks without performing the upgrade. These steps also run in "pre-check" mode (no arguments) and upgrade mode using `--upgrade`, or `--upgradepkgsonly`.

- Runs playbook with: "run_precheck: true"
- Playbook sets: "get_pkgonly: true"

### Playbook Behavior
1. Obtains the current package versions installed on the remote hosts from the provided list of packages.
2. Updates the apt cache to ensure the latest package versions are available.
3. Displays verbose apt upgrade output to see package changes that will happen during the upgrade.

### Check each patch group consecutively
`./begin_patch.py "vim,wget,curl" -r us-central1 --pkgcheck`

### Check all patch groups together
`./begin_patch.py "vim,wget,curl" -r us-central1 -g "pg*" --upgrade`

###
# Pre-Checks (default mode)
Calling `begin_patch.py` with no argument will run pre-checks without performing the upgrade. These steps also run using the `--upgrade` or `--upgradepkgsonly` arguments.
- Runs playbook with: "run_precheck: true"

### Playbook Behavior
1. Runs host and group guardrail checks.
2. Runs package checks.
3. Checks for an existing reboot-required flag for the remote host.
4. Initiates service validation tasks to ensure critical services are running correctly.
5. Attempts to start any down services discovered (see "Role: Validation" in parent README for details)

### Run pre-checks on each patch group consecutively
`./begin_patch.py "vim,wget,curl" -r us-central1`

###
# Using a custom patch group or inventory file
You can supply a custom inventory file with predefined patch groups or host associations by passing the `-i` or `--inventory` argument to `begin_patch.py` along with the path to your inventory file.

If using a custom inventory, you must ensure the inventory file is formatted correctly and that the patch group names are defined as expected by the `begin_patch.py` script. For example, you might have an inventory file that looks like this:

File: '${HOME}/my_custom_inventory.yaml'
```
pg1:
 hosts:
 kafka-dev-us-central1-3
 postfix-dev-us-central1-1
pg2:
 hosts:
 kafka-dev-us-central1-2
pg3:
 hosts:
 kafka-dev-us-central1-1
 controller-dev-us-central1-1
```
The orchestrator script will patch the target groups consecutively as if it had generated the inventory file. Execute patching with the following command:

`./begin_patch.py "vim,wget,curl" -i ${HOME}/my_custom_inventory.yaml --upgrade`

**Note**  
The **{ region }** argument isn't required in this case because it's used primarily for generating the dynamic patch group inventory file for hosts in one region at a time; Custom inventory files can have hosts in multiple regions.

###
# Using a custom inventory with custom group names
Suppose you want to use a custom inventory file with predefined patch groups that don't conform to the "pg#" style naming convention. Accomplish this by passing the inventory file to the orchestrator script with the `-i` argument and the group name or names with the `-g` or `--grouplist` argument.

For example, let's say your inventory file looks like this:

File: '${HOME}/my_custom_inventory.yaml'
```
mygroup1:
 hosts:
 kafka-dev-us-central1-3
 postfix-dev-us-central1-1
mygroup2:
 hosts:
 kafka-dev-us-west1-1
mygroup3:
 hosts:
 kafka-dev-us-central1-1
 controller-dev-us-central1-1
```
You can execute patching on one group with the following command:

`./begin_patch.py "vim,wget,curl" -i ${HOME}/my_custom_inventory.yaml -g mygroup1 --upgrade`

On multiple groups at once:

`./begin_patch.py "vim,wget,curl" -i ${HOME}/my_custom_inventory.yaml -g "mygroup1,mygroup3" --upgrade`

Or on all of the groups at once:

`./begin_patch.py "vim,wget,curl" -i ${HOME}/my_custom_inventory.yaml -g "mygroup*" --upgrade`

**Note**  
The orchestrator will <u>not</u> loop through and patch each group consecutively unless the group names follow the "pg#" style naming convention.

###
# Excluding instances from the upgrade
You can preemptively exclude instances from the upgrade process by specifying them in a comma-separated list after the `--skiphost` or `--skiprole` argument to the orchestrator. Hostnames are added to a 'skiphost' or 'skiprole' file within the 'vars' patch directory created at runtime.
- '${HOME}/patch-{yyyymmdd-hhmmss}/vars
    - /skiphost
    - /skiprole

This will exclue the one Kafka instance from the upgrade:

`./begin_patch.py "vim,wget,curl" -r us-central1 --skiphost kafka-dev-us-central1-2`

This will exclude every Kafka instance from the upgrade:

`./begin_patch.py "vim,wget,curl" -r us-central1 --skiprole kafka-dev-us-central1-2`

This will exclude two Kafka instances and every Sharddb instance from the upgrade:

`./begin_patch.py "vim,wget,curl" -r us-central1 --skiphost "kafka-dev-us-central1-2,kafka-dev-us-central1-3" --skip role sharddb-dev-us-central1-1`

**Note**  
Instances part of a role in the **{ independent_hosts }** vars list are exempt from the <u>role</u> guardrail because they are not configured as a cluster with other hosts. See 'roles/comon/vars/main.yaml'.

###
# Orchestrator Debugging
Using the `--debug` option with `begin_patch.py` will do the following:
- Performs variable validation 
- Sets up directories, variable and skip files within the `${HOME}/patch-{yyyymmdd-hhmmss}/vars` directory.
- Prints the Ansible command that it would run if not in Debug mode.

**Note**
Debug mode doesn't generate the actual patch files. It forms a path to a dummy patch file and selects a random number between 1-6 to represent the patch groups. This setup mimics the behavior of the orchestrator script when run in debug mode in a non-controller environment.

###
# Dynamic Inventory (patch_groups.py)
This script generates patch group files based on the current GCP project and role groups listed in the 'scope' file by region.

### Usage:
- `./patch_groups.py` or `./patch_groups.py --debug`

Using the `--debug` option will output a JSON list of instances retrieved along with the generated patch groups separated by region to stdout in addition to writing the files to disk.

### How it works
1. It retrieves the current GCP project ID using `gcloud config get-value`.
2. It reads the list of in-scope role groups from the 'scope' file.
3. Obtains a list of instances using `gcloud compute instances list` based on the scope and project.
4. It sorts the instances by role and region.
5. Reverses the order of hosts for each role in each region.
6. Separates non-sharddb roles from sharddb roles.
7. Creates patch groups for non-sharddb roles, distributing hosts evenly in reverse order.
8. Handles sharddb roles separately, placing them in patch groups 1 and 2.
8. Writes the patch group definitions to files by region in the format 'patch-groups-{region}.yaml'.

Example:
- patch-group-us-central1.yaml
- patch-groupp-us-west1.yaml

This organizational pattern takes each cluster configuration type into account. It ensures that either one host is getting patched at a time (e.g., Kafka and RabbitMQ) or the secondary (slave) host gets patched first, followed by the primary (master) host. Patching and rebooting instances using this pattern helps maintain high availability and minimizes downtime while streamlining the process.

From a hostname perspective, sharddb instances get clustered in a non-linear configuration, so they're handled separately and divided into the first two patch groups. All secondary (slave) hosts are patched first in group pg1, followed by the primary (master) hosts in group pg2.

###
# Package Upgrade Vars (package_list.py)
This script generates a list of package names in a file called 'packages.yaml' based on the names provided in comma-separated format. The script can move the generated file to a specified directory using the `-f` or `--folder` argument.

### Usage
- `./package_list.py "vim,wget,curl"`
### Move the generated packages.yaml file to a specified directory 
- `./pac kage_list.py "vim,wget,curl" -f #{HOME}/patch/vars`

Example: packages.yaml
```
---
packages:
- vim
- wget
- curl
```
