#!/usr/bin/env python

DOCUMENTATION = '''
---
module: dockerimp
short_description: improved docker container management module
description:
    - Manage docker containers with ansible
options:
    name:
        description:
            - Set the name of the container
        required: false
        default: null
        aliases: ["id"]
    state:
        description:
            - Set the state of the container
        required: true
        default: null
        choices: [
            "present", "running", "stopped", "absent",
            "restarted", "image_present", "image_latest",
            "image_absent"
        ]
        aliases: []
    image:
        description:
            - Set the image for the container
        required: false
        default: null
        aliases: []
    env:
        description:
            - Set the container environment variables
        required: false
        default: null
        aliases: []
    volumes:
        description:
            - Mount voulumes for the container
        required: false
        default: null
        aliases: []
    ports:
        description:
            - Map ports for container
        required: false
        default: null
        aliases: []
    command:
        description:
            - Set the command for container
        required: false
        default: null
        aliases: []
    expose:
        description:
            - Expose ports
        required: false
        default: null
        aliases: []
    links:
        description:
            - Link containers
        required: false
        default: null
        aliases: []
    client_url:
        description:
            - Client base url
        required: false
        default: "unix://var/run/docker.sock"
        aliases: []
'''
import sys
import copy
try:
    import docker.client
except ImportError as e:
    print("Failed to import module {1}".format(e))
    sys.exit(1)

class ContainerManagerException(Exception):
    pass

class ContainerManager():

    def __init__(self, module):
        self.module = module
        self.client = docker.Client(base_url = module.params.get('client_url'))
        self.changed = False
        self.check_mode = module.check_mode
        self.changes_made = []
        self.params = self.fix_parameters()

    def fix_parameters(self):
        params = copy.deepcopy(self.module.params)
        if params.get('volumes'):
            try:
                if type(params['volumes']) is str:
                    volumes = params['volumes'].split(",")
                elif type(params['volumes']) is list:
                    volumes = params['volumes']
                else:
                    raise ContainerManagerException({'Invalid argument': params['volumes']})
                mount_points = [x.split(":")[1] for x in volumes]

                binds = {}
                for i in volumes:
                    j = i.split(":")
                    len_j = len(j)
                    if len_j != 2 and len_j != 3:
                        raise ContainerManagerException({'Invalid argument': params['volumes']})
                    ro = False
                    if len_j == 3:
                        if j[2] == "ro":
                            ro = True
                        elif j[2] == "rw":
                            ro = False
                        else:
                            raise ContainerManagerException({'Invalid argument': params['volumes']})

                    binds[j[0]] = {'bind': j[1], 'ro': ro}

                params['binds'] = binds
                params['volumes'] = mount_points
            except IndexError as e:
                raise ContainerManagerException({'Invalid argument': params['volumes']})

        if params.get('ports'):
            try:
                if type(params['ports']) is str:
                    port_params = params['ports'].split(",")
                elif type(params['ports']) is list:
                    port_params = params['ports']
                else:
                    raise ContainerManagerException({'Invalid argument': params['ports']})

                ports = []
                for i in port_params:
                    values = i.split(":")
                    len_values = len(values)
                    if len_values != 2 and len_values != 3:
                        raise ContainerManagerException({'Invalid argument': params['ports']})
                    port_and_prot = values[-1].split("/")
                    len_port_and_prot = len(port_and_prot)
                    if len_port_and_prot > 2:
                        raise ContainerManagerException({'Invalid argument': params['ports']})
                    p = (port_and_prot[0], port_and_prot[1]) if len_port_and_prot == 2 else port_and_prot[0]
                    ports.append(p)

                port_bindings = {}
                for i in port_params:
                    values = i.split(":")
                    len_values = len(values)
                    if len_values == 2:
                        host_port = values[0]
                        prot_and_port = values[1]
                        bind_ip = None
                    elif len_values == 3:
                        host_port = values[1]
                        prot_and_port = values[2]
                        bind_ip = values[0]
                    else:
                        raise ContainerManagerException({'Invalid argument': params['ports']})
                    prot_and_port = prot_and_port.split("/")
                    len_prot_and_port = len(prot_and_port)
                    if len_prot_and_port == 2:
                        key = "{0}/{1}".format(prot_and_port[0], prot_and_port[1])
                    elif len_prot_and_port == 1:
                        key = prot_and_port[0]
                    else:
                        raise ContainerManagerException({'Invalid argument': params['ports']})
                    if bind_ip:
                        val = (bind_ip, host_port) if host_port else (bind_ip,)
                    else:
                        val = host_port or None
                    port_bindings[key] = val

                params['ports'] = ports
                params['port_bindings'] = port_bindings

            except IndexError as e:
                raise ContainerManagerException({'Invalid argument': params['ports'], 'error': e})

        if params.get('env'):
            if type(params['env']) is str:
                envs = params['env'].split(",")
            elif type(params['env']) is list:
                envs = params['env']
            elif type(params['env']) is dict:
                envs = ["{0}={1}".format(x, params['env'][x]) for x in params['env']]
            else:
                raise ContainerManagerException({'Invalid argument': params['env']})

            # Add special ANSIBLE_MANAGED_ENVS variable so we can track which
            # variables are managed by ansible
            envs.append("ANSIBLE_MANAGED_ENVS={0}".format(":".join([x.split("=")[0] for x in envs])))

            params['environment'] = envs

        return params

    def ensure_present(self):
        required_params = ("name", "image")
        self.check_required_parameters(required_params)

        container, _ = self.find_container(self.params.get('name'))
        if not container:
            container = self.create_container()
        elif not self.ensure_same(container):
            self.ensure_absent()
            container = self.ensure_present()
        return container

    def ensure_running(self):
        container = self.ensure_present()
        if not self.find_container(container['Id'])[1]:
            self.start_container(container)

    def ensure_stopped(self):
        required_params = ("name",)
        self.check_required_parameters(required_params)

        container, running = self.find_container(self.params.get('name'))
        if not container:
            raise ContainerManagerException("Container not found")
        if running:
            self.stop_container(container)

    def ensure_absent(self):
        required_params = ("name",)
        self.check_required_parameters(required_params)

        container, running = self.find_container(self.params.get('name'))
        if running:
            self.stop_container(container)
        if container:
            self.remove_container(container)

    def restart(self):
        required_params = ("name",)
        self.check_required_parameters(required_params)

        container, running = self.find_container(self.params.get('name'))
        if not container:
            raise ContainerManagerException("Container not found")
        if not running:
            raise ContainerManagerException("Container not running")
        self.restart_container(container)

    def ensure_image_present(self):
        pass

    def ensure_image_latest(self):
        pass

    def ensure_image_absent(self):
        pass

    def check_required_parameters(self, required):
        for i in required:
            if not self.params.get(i):
                state = self.params['state']
                error_msg = "{0} required for {1} satate".format(i, state)
                raise ContainerManagerException(error_msg)

    def find_container(self, name):
        # Search from containers that are running
        containers = self.client.containers()
        c = [x for x in containers if
                ((x['Names'] or [""])[0] == "/{0}".format(name)) or
                (len(name) > 9 and x['Id'].startswith(name))]
        if c:
            return c[0], True
        # Search from all existing containers
        containers = self.client.containers(all = True)
        c = [x for x in containers if
                ((x['Names'] or [""])[0] == "/{0}".format(name)) or
                (len(name) > 9 and x['Id'].startswith(name))]
        if c:
            return c[0], False
        return None, False

    def running_latest_image(self, container, image):
        if not container.get('Config'):
            container_info = self.client.inspect_container(container)
        else:
            container_info = container
        image_info = self.get_image_info(image)
        if image_info['Id'] == container_info['Image']:
            return True
        else:
            return False

    def get_info(self, container):
        return self.client.inspect_container(container)

    def get_image_info(self, image):
        return self.client.inspect_image(image)

    def create_container(self):
        params = self.params

        key_filter = (
            'image', 'command', 'hostname', 'user',
            'detach', 'stdin_open', 'tty', 'mem_limit',
            'ports', 'environment', 'dns', 'volumes',
            'volumes_from', 'network_disabled', 'name',
            'entrypoint', 'cpu_shares', 'working_dir',
            'memswap_limit'
        )
        filtered = { x: params[x] for x in key_filter if x in params }

        # Hack - Try to start container. If no image is found try to pull it
        #        and try again
        for _ in range(2):
            try:
                container = self.client.create_container(**filtered)
                break

            except docker.errors.APIError as e:
                self.client.pull(filtered['image'])

                # Hack - docker-py pull does not return easilly readable
                #        data about if the pull was successefull or not.
                #        Calling inspect_image raises an error if image is
                #        not present
                self.client.inspect_image(filtered['image'])
                continue

        info = self.get_info(container)
        self.write_log('CREATED', info)
        return container

    def start_container(self, container):
        params = self.params
        key_filter = (
            'binds', 'port_bindings', 'lxc_conf',
            'publish_all_ports', 'links', 'privileged',
            'dns', 'dns_search', 'volumes_from', 'network_mode',
            'restart_policy', 'cap_add', 'cap_drop'
        )
        filtered = { x: params[x] for x in key_filter if x in params }

        self.client.start(container, **filtered)
        info = self.get_info(container)
        self.write_log('STARTED', info)

    def stop_container(self, container):
        self.client.stop(container)
        info = self.get_info(container)
        self.write_log('STOPPED', info)

    def remove_container(self, container):
        self.client.remove_container(container)
        c, _ = self.find_container(container['Id'])
        if c:
            raise ContainerManagerException("Could not remove the container")
        self.write_log('REMOVED', container)

    def restart_container(self, container):
        self.client.restart(container)
        info = self.get_info(container)
        self.write_log('RESTARTED', info)

    def ensure_same(self, container):
        params = self.params
        require_restart = False

        container_info = self.client.inspect_container(container)

        # Ensure running the right image
        if container_info['Config']['Image'] != params['image']:
            require_restart = True

        # Ensure running latest image if the parameter is provided
        same = True
        if params.get('latest_image'):
            self.client.pull(params['image'])
            if not self.running_latest_image(container_info, params['image']):
                same = False
                require_restart = True

        # Ensure environment vars are up to date
        for i in container_info['Config']['Env']:
            if "ANSIBLE_MANAGED_ENVS" in i:
                ansible_managed_envs = i.split("=")[1].split(":")

                # Add the magic ANSIBLE_MANAGED_ENVS key value here
                # so that the two lists are easily comparable with
                # set() below
                ansible_managed_envs.append("ANSIBLE_MANAGED_ENVS")
                has_ansible_managed_envs = True
                break
        else:
            has_ansible_managed_envs = False
        has_env_params = params.get('environment') != None
        if has_env_params or has_ansible_managed_envs:
            if has_env_params and has_ansible_managed_envs:
                env_params = params['environment']

                # Check same variables are set
                if set(ansible_managed_envs) != set([x.split("=")[0] for x in env_params]):
                    require_restart = True

                # Check that the values are right
                else:
                    for env in env_params:
                        if env not in container_info['Config']['Env']:
                            require_restart = True
                            break
            else:
                require_restart = True

        # Ensure volume mountings are right
        container_binds = container_info['HostConfig']['Binds']
        bind_params = params.get('binds')
        if container_binds or bind_params:
            if container_binds and bind_params:
                _bind_params = [
                    ":".join([
                        x, bind_params[x]['bind'], "ro" if bind_params[x]['ro'] else "rw"
                    ]) for x in bind_params
                ]
                if set(_bind_params) != set(container_binds):
                    require_restart = True
            else:
                require_restart = True

        if params.get('command'):
            if params['command'] != container['Command']:
                require_restart = True

        return require_restart != True

    def generate_message(self):
        if not self.has_changes():
            msg = "Up to date. No changes made"
        else:
            msg = self.changes_made
        return msg

    def write_log(self, action, info):
        key_filter = (
            'Name', 'Id', 'Image',
        )
        filtered = { x: info[x] for x in key_filter if x in info }
        self.changes_made.append({action: filtered})

    def has_changes(self):
        if self.changes_made:
            return True
        return False

def main():
    arguments = {
        'state': {
            'required': True,
            'choices': [
                "present", "running", "stopped",
                "absent", "restarted", "image_present",
                "image_latest",
            ]
        },
        'name':          { 'default': None, 'aliases': ["id"] },
        'image':         { 'default': None },
        'env':           { 'default': None },
        'volumes':       { 'default': None },
        'ports':         { 'default': None },
        'command':       { 'default': None },
        'expose':        { 'default': None },
        'links':         { 'default': None },
        'latest_image':  { 'default': False, 'choises': 'booleans' }
    }
    #module = AnsibleModule(argument_spec = arguments, supports_check_mode = True)
    module = AnsibleModule(argument_spec = arguments)
    try:

        manager = ContainerManager(module)
        state = module.params.get('state')
        if state == "present":
            manager.ensure_present()
        elif state == "running":
            manager.ensure_running()
        elif state == "stopped":
            manager.ensure_stopped()
        elif state == "absent":
            manager.ensure_absent()
        elif state == "restarted":
            manager.restart()
        elif state == "image_present":
            manager.ensure_image_present()
        elif state == "image_latest":
            manager.ensure_image_latest()
        elif state == "image_absent":
            manager.ensure_image_absent()
        module.exit_json(changed = manager.has_changes(), msg = manager.generate_message())

    except ContainerManagerException as e:
        module.fail_json(msg = str(e))
    except docker.errors.APIError as e:
        module.fail_json(msg = str(e))

from ansible.module_utils.basic import *
main()
