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
        self.client = docker.Client(base_url = module.params.get("client_url"))

    def ensure_present(self):
        params = self.module.params
        if not params.get("name"):
            raise ContainerManagerException("State 'present' requires name or id")
        if not params.get("image"):
            raise ContainerManagerException("State 'present' requires image")
        container = self.find_container(params.get("name"))
        if not container:
            self.create_container()
        elif not self.ensure_same(container):
            pass

    def ensure_running(self):
        pass

    def ensure_stopped(self):
        pass

    def ensure_absent(self):
        pass

    def restart(self):
        pass

    def find_container(self, name, all = True):
        containers = self.client.containers(all = all)
        c = [x for x in containers if x["Names"][0] == "/{0}".format(name)]
        if not c:
            return None
        return c[0]

    def create_container(self):
        key_filter = [
            'image', 'command', 'hostname', 'user',
            'detach', 'stdin_open', 'tty', 'mem_limit',
            'ports', 'environment', 'dns', 'volumes',
            'volumes_from', 'network_disabled', 'name',
            'entrypoint', 'cpu_shares', 'working_dir',
            'memswap_limit'
        ]
        params = { x: self.module.params[x] for x in key_filter if x in self.module.params }
        self.client.create_container(**params) 

    def ensure_same(self, container):
        pass

def main():
    arguments = {
        'state': {
            'required': True,
            'choises': ["present", "running", "stopped", "absent", "restarted"]
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
    module = AnsibleModule(argument_spec = arguments)
    try:
        manager = ContainerManager(module)
        state = module.params.get("state")
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
    except ContainerManagerException as e:
        module.fail_json(msg = str(e))
    except docker.errors.APIError as e:
        module.fail_json(msg = str(e))

from ansible.module_utils.basic import *
main()
