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
        self.changes_made = {}

    def ensure_present(self):
        params = self.module.params
        if not params.get('name'):
            raise ContainerManagerException("This state requires name or id")
        if not params.get('image'):
            raise ContainerManagerException("This state requires image")
        container, _ = self.find_container(params.get('name'))
        if not container:
            container = self.create_container()
        elif not self.ensure_same(container):
            pass
        return container

    def ensure_running(self):
        container = self.ensure_present()
        if not self.find_container(container['Id'])[1]:
            self.start_container(container)

    def ensure_stopped(self):
        params = self.module.params
        if not params.get('name'):
            raise ContainerManagerException("This state requires name or id")
        container, running = self.find_container(params.get('name'))
        if not container:
            raise ContaqinerManagerException("Container not found")
        if running:
            self.stop_container(container)


    def ensure_absent(self):
        params = self.module.params
        if not params.get('name'):
            raise ContainerManagerException("This state requires name or id")
        container, running = self.find_container(params.get('name'))
        if running:
            self.stop_container(container)
        if container:
            self.remove_container(container)

    def restart(self):
        params = self.module.params
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

    def create_container(self):
        params = copy.deepcopy(self.module.params)
        try:
            if params.get('volumes'):
                if type(params['volumes']) is str:
                    volumes = params['volumes'].split(",")
                elif type(params['volumes']) is list:
                    volumes = params['volumes']
                else:
                    raise ContainerManagerException({'Invalid argument': params['volumes']})
                mount_points = [x.split(":")[1] for x in volumes]
                params['volumes'] = mount_points
        except IndexError as e:
            raise ContainerManagerException({'Invalid argument': params['volumes']})

        key_filter = [
            'image', 'command', 'hostname', 'user',
            'detach', 'stdin_open', 'tty', 'mem_limit',
            'ports', 'environment', 'dns', 'volumes',
            'volumes_from', 'network_disabled', 'name',
            'entrypoint', 'cpu_shares', 'working_dir',
            'memswap_limit'
        ]
        filtered = { x: params[x] for x in key_filter if x in params }

        container_id = self.client.create_container(**filtered) 
        container, _ = self.find_container(container_id['Id'])
        self.write_log('CREATED', container)
        return container

    def start_container(self, container):
        params = copy.deepcopy(self.module.params)
        if params.get('volumes'):
            try:
                if type(params['volumes']) is str:
                    volumes = params['volumes'].split(",")
                elif type(params['volumes']) is list:
                    volumes = params['volumes']
                else:
                    raise ContainerManagerException({'Invalid argument': params['volumes']})
                binds = {}
                for i in volumes:
                    j = i.split(":")
                    ro = j[2] if len(j) is 3 else False
                    binds[j[0]] = {'bind': j[1], 'ro': ro}
                params['binds'] = binds
            except IndexError as e:
                raise ContainerManagerException({'Invalid argument': params['volumes']})

        key_filter = [
            'binds', 'port_bindings', 'lxc_conf',
            'publish_all_ports', 'links', 'privileged',
            'dns', 'dns_search', 'volumes_from', 'network_mode',
            'restart_policy', 'cap_add', 'cap_drop'
        ]
        filtered = { x: params[x] for x in key_filter if x in params }

        self.client.start(container, **filtered)
        container, _ = self.find_container(container['Id'])
        self.write_log('STARTED', container)

    def stop_container(self, container):
        self.client.stop(container)
        container, _ = self.find_container(container['Id'])
        self.write_log('STOPPED', container)

    def remove_container(self, container):
        self.client.remove_container(container)
        c, _ = self.find_container(container['Id'])
        if c:
            raise ContainerManagerException("Could not remove the container")
        self.write_log('REMOVED', container)

    def restart_container(self, container):
        self.client.restart(container)
        container, _ = self.find_container(container['Id'])
        self.write_log('RESTARTED', container)

    def ensure_same(self, container):
        pass

    def generate_message(self):
        if not self.has_changes():
            msg = "Up to date. No changes made"
        else:
            msg = self.changes_made
        return msg

    def write_log(self, action, info):
        if not self.changes_made.get(action):
            self.changes_made[action] = []
        self.changes_made[action].append(info)


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
        'name':     { 'default': None, 'aliases': ["id"] },
        'image':    { 'default': None },
        'env':      { 'default': None },
        'volumes':  { 'default': None },
        'ports':    { 'default': None },
        'command':  { 'default': None },
        'expose':   { 'default': None },
        'links':    { 'default': None },
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
