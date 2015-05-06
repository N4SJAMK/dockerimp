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
    insecure_registry:
        description:
            - Trust insecure registrys
        required: false
        default: false
        aliases: []
'''
try:
    import docker.client
except ImportError as e:
    print("Failed to import module {0}".format(e))
    sys.exit(1)

def image_case(params):
    return "Not yet implemented", False

def container_case(params):
    desired_state, err = get_desired_state(module.params)
    if err:
        return err, False

    current_state, err = get_current_state(params.get['name'])
    if err:
        return err, False

    actions, err = create_actions(current_state, desired_state)
    if err:
        return err, False

    log = []
    for action, msg in actions:
        err = action()
        if err:
            return err, False
        log.append(msg)

'''
container state dict

* state: String

* name: String
* image: String
* command: String

* envs:
    - "SOME_ENV=something"
    - ...
* ports:
    - '80/tcp': [{'HostIp': '', 'HostPort': '80'}]
    - '8080/udp': None
    - ...
* volumes:
    - "/tmp/test:/tmp:rw"
    - "/etc/config.cfg:/etc/config.cfg:ro"
    - ...
* links:
    - container1
    - container2
    - ...
'''
def get_desired_state(params):

    desired_state = {}
    desired_state['ports'] = parse_port_params(params.get('ports'))

def parse_port_params(ports):
    # Parse port params
    if ports:
        if type(params['ports']) is str:
            ports = params['ports'].split(",")
        elif type(params['ports']) is list:
            ports = params['ports']
        else:
            return None, {"Invalid parameter": params['ports']}

        port_bindings = []
        #for p in ports:

        #    halfs = p.split(":")
        #    len_halfs = len(halfs)

        #    if len_halfs != 2 and len_halfs != 3:
        #        return None, {"Invalid parameter": params['ports']}

        #    port_prot = values[-1].split("/")
        #    len_port_prot = len(port_prot)

        #    if len_port_prot > 2:
        #        return None, {"Invalid parameter": params['ports']}

        #    p = (port_prot[0], port_prot[1]) if len_port_prot == 2 else port_prot[0]
        #    ports.append(p)


        for p in ports:

            halfs = p.split(":")
            len_halfs = len(halfs)
            
            if len_halfs == 2:
                host_port = halfs[0]
                prot_port = halfs[1]
                bind_ip = None

            elif len_halfs == 3:
                host_port = halfs[1]
                prot_port = halfs[2]
                bind_ip = halfs[0]

            else:
                return None, {"Invalid parameter": params['ports']}

            prot_port_halfs = prot_port.split("/")
            len_prot_port = len(prot_and_port)

            if len_prot_port == 2:
                key = "{0}/{1}".format(prot_port[0], prot_port[1])

            elif len_prot_and_port == 1:
                key = prot_port[0]

            else:
                return None, {"Invalid parameter": params['ports']}

            if bind_ip:
                val = (bind_ip, host_port) if host_port else (bind_ip,)

            else:
                val = host_port or None

            port_bindings[key] = val

    else:
        return None

def get_current_state(client_url):
    pass

def main():
    arguments = {
        'state': {
            'required': True,
            'choices': [
                "present", "running", "running_latest",
                "stopped", "absent", "restarted",
                "image_present", "image_latest",
            ]
        },
        'name':                 { 'default': None, 'required': True },
        'image':                { 'default': None },
        'env':                  { 'default': None },
        'volumes':              { 'default': None },
        'ports':                { 'default': None },
        'command':              { 'default': None },
        'expose':               { 'default': None },
        'links':                { 'default': None },
        'insecure_registry':    { 'default': False, 'choises': BOOLEANS },
    }

    module = AnsibleModule(argument_spec = arguments)

    if module.params['state'] in ["image_present", "image_latest", "image_absent"]:
        msg, ok = image_case(module.params)
    else:
        msg, ok = container_case(module.params)

    if not ok:
        module.fail_json(msg = msg)
    elif len(msg):
        module.exit_json(msg = msg, changed = True)
    else:
        module.exit_json(changed = False)

from ansible.module_utils.basic import *
main()