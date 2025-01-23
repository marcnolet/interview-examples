# README
This page provides an overview of the **package-upgrade** playbook only and not how to operate it.

**WARNING**  
Running this playbook directly with the ansible-playbook command will bypass critical guardrails necessary for safeguarding clustered instances during the upgrade and rebooting process.

Please use the `begin_patch.py` orchestrator in the **scripts** folder to run the playbook and see the 'scripts/README' for details.

###
# Package Upgrade Playbook
Created by:  Marc Nolet (mnolet@paloaltonetworks.com)

This playbook automates package upgrading in GCP environments and can upgrade an entire region of instances with one command using the orchestration script. It can also run targeting instance group types or a single host. 

## Playbook Operation Modes
The following operation modes can be configured but are handled automatically through `begin_patch.py` arguments:
- **run_pkgcheck**:    (default: false) --> `--pkgcheck`
- **run_precheck**:    (default: false) = default mode when running orchestrator with no additional args
- **run_upgrade**:     (default: false) = `--upgrade` and `--upgradepkgsonly`
- **run_validation**:  (default: false) = runs by default in all modes except `--pkgcheck`

## Guardrails
The playbook relies on Ansible's built-in '.retry' file feature along with a 'skiphost' file generated and updated by `begin_patch.py` to identify unhealthy instances and safeguard clustered instances from undergoing breaking updates or reboots, allowing the playbook to maximize the number of successful upgrades across an entire GCP environment while preventing potential disruption.

### Host & Role
Compares hostnames and roles for matches against hostnames listed in the 'skiphost', 'skiprole' and any existing '*.retry' files to prevent upgrading unhealthy instances or exacerbating any existing issue. Ansible creates a 'main.retry' file with instance hostnames who encounter a task failure throughout the playbook run.

**Location**: 'roles/common/tasks/guardrails.yaml'

**Note**  
You can preemptively skip individual instances with or every instance of a role group by issuing `--skiphost` or `--skiprole` followed by a comma-separated list of hostnames. See "scripts/README.md" for details.

### skip_host
**{ skip_host }** is a global fact used by the guardrails and validation playbooks to prevent the playbook from executing upgrades or rebooting unhealthy instances or instances clustered with them.

### Controller
Compares each instance by hostname to the local controller hostname currently executing the Ansible playbook and prevents it from undergoing a reboot when one is required. After the playbook finishes, please reboot the controller as the final step (if a reboot is required).

**Location**:  'roles/common/tasks/reboot_instance.yaml'

## Role: Common
Tasks common to every instance.

### get_package_info
* Checks if the "unattended-upgrades" package is installed and displays the configuration info if the service is running and enabled.
* Compares the list of packages provided at runtime to those installed and creates a dictionary of installed packages and versions.
* Displays the installed package versions, then displays what changes will be made during the upgrade.

### guardrails

#### Host
* Looks for matching hostnames in the '.retry', 'skiphost' and 'skiprole' files on the controller and sets 'skip_host' fact to 'true' if a match is found.

#### Role
* Looks for matching roles for the hostnames in the '.retry' and 'skiprole' files on the controller and sets 'skip_host' fact to 'true' if a role match is found. Instances in roles part of the **{ independent_hosts }** vars list are excluded from the role check.

**Note**  
Instances skipped with the **{ skip_host }** fact are not added to the 'skiphost' file.

### reboot_instance
* Checks if the local controller is the same as the remote host on which the play is running.
* Checks for a reboot flag on the remote host.
* Initiates a reboot if the remote host isn't the local controller and **upgrade_if_installed** is set to **true**.

### upgrade_package
* Upgrades the list of packages from the dictionary of installed packages previously created when getting package information.
* Display the upgrade log.

## Role: Validate
Validation plays for critical services used to detect unhealthy services and attempt to bring them to a healthy state by starting them. These tasks run during the pre-check stage before the upgrade and for the post-check stage. Instances with unhealthy services that can't be started are added to the '.retry' and 'skiprole' guardrails so they're skipped during the upgrade or their role counterparts are skipped to prevent exacerbating any existing issues.

### envoy
See **{ envoy_groups }** in 'roles/validation/vars/main.yaml' for in scope roles.
- Checks for the existence of an Envoy container 
- Tries to start the container if not already running.
- Gives the services 5 seconds to start before checking the status again.
- Sets **skip_host: true** if service remains down.

### kafka
See **{ kafka_groups }** in 'roles/validation/vars/main.yaml' for in scope roles.
- Tries to start the Zookeeper, Kafka or Kafka exporter services if they're not already running.
- Gives the services 5 seconds to start before checking their statuses again.
- Sets **skip_host: true** if any service remains down.

### mysql
See **{ mysql_groups }** in 'roles/validation/vars/main.yaml' for in scope roles.
- Tries to start the MySQL or MySQL exporter services if they're not already running.
- Gives the services 5 seconds to start before checking their statuses again.
- Displays MySQL role configuration (master or slave).
- Sets **skip_host: true** if any service remains down.

### named (Bind)
See **{ named_groups }** in 'roles/validation/vars/main.yaml' for in scope roles.
- Tries to start the Bind service if not already running.
- Gives the service 5 seconds to start before checking the status again.
- Sets **skip_host: true** if service remains down.

### rabbitmq
See **{ rabbitmq_groups }** in 'roles/validation/vars/main.yaml' for in scope roles.
- Tries to start the RabbitMQ or RabbitMQ exporter services if they're not already running.
- Gives the services 5 seconds to start before checking their statuses again.
- Sets **skip_host: true** if any service remains down.

###
# How To: Add new hosts to the upgrade process
1. Find the unique role group name for the new host and add it to the 'scripts/scope' file.
2. If the instance isn't clustered, add the role group to the **{ independent_hosts }** block in 'roles/common/vars/main.yaml'.
3. If the instance runs a critical validated service, add the role group to the relevant validation role block in 'roles/validation/vars/main.yaml'.
