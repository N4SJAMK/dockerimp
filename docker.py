#!/usr/bin/env python

DOCUMENTATION = '''
---
module: docker-imp
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
        default: present
        choices: ["present", "running", "stopped", "absent", "restarted"]
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
                    ro = j[2] if len(j) == 3 else False
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

        return params

    def ensure_present(self):
        params = self.params
        if not params.get('name'):
            raise ContainerManagerException("This state requires name or id")
        if not params.get('image'):
            raise ContainerManagerException("This state requires image")
        container, _ = self.find_container(params.get('name'))
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
        params = self.params
        if not params.get('name'):
            raise ContainerManagerException("This state requires name or id")
        container, running = self.find_container(params.get('name'))
        if not container:
            raise ContaqinerManagerException("Container not found")
        if running:
            self.stop_container(container)

    def ensure_absent(self):
        params = self.params
        if not params.get('name'):
            raise ContainerManagerException("This state requires name or id")
        container, running = self.find_container(params.get('name'))
        if running:
            self.stop_container(container)
        if container:
            self.remove_container(container)

    def restart(self):
        params = self.params
        if not params.get('name'):
            raise ContainerManagerException("This state requires name or id")
        container, running = self.find_container(params.get('name'))
        if not container:
            raise ContainerManagerException("Container not found")
        if not running:
            raise ContainerManagerException("Container not running")
        self.restart_container(container)

    def find_container(self, name):
        containers = self.client.containers()
        c = [x for x in containers if 
                (x['Names'][0] == "/{0}".format(name)) or
                (x['Id'] == name)]
        if c:
            return c[0], True
        containers = self.client.containers(all = True)
        c = [x for x in containers if 
                (x['Names'][0] == "/{0}".format(name)) or
                (x['Id'] == name)]
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

        key_filter = [
            'image', 'command', 'hostname', 'user',
            'detach', 'stdin_open', 'tty', 'mem_limit',
            'ports', 'environment', 'dns', 'volumes',
            'volumes_from', 'network_disabled', 'name',
            'entrypoint', 'cpu_shares', 'working_dir',
            'memswap_limit'
        ]
        filtered = { x: params[x] for x in key_filter if x in params }

        container = self.client.create_container(**filtered) 
        info = self.get_info(container)
        self.write_log('CREATED', info)
        return container

    def start_container(self, container):
        params = self.params
        key_filter = [
            'binds', 'port_bindings', 'lxc_conf',
            'publish_all_ports', 'links', 'privileged',
            'dns', 'dns_search', 'volumes_from', 'network_mode',
            'restart_policy', 'cap_add', 'cap_drop'
        ]
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
        same = True
        if params['latest_image']:
            self.client.pull(params['image'])
            if not self.running_latest_image(container, params['image']):
                same = False
        return same

    def generate_message(self):
        if not self.has_changes():
            msg = "Up to date. No changes made"
        else:
            msg = self.changes_made
        return msg

    def write_log(self, action, info):
        key_filter = [
            'Name', 'Id', 'Image',
        ]
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
            'choices': ["present", "running", "stopped", "absent", "restarted"]
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
        module.exit_json(changed = manager.has_changes(), msg = manager.generate_message())

    except ContainerManagerException as e:
        module.fail_json(msg = str(e))
    except docker.errors.APIError as e:
        module.fail_json(msg = str(e))

from ansible.module_utils.basic import *
main()
