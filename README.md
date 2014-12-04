# dockerimp ansible module
This is an ansible module made for controlling docker containers and images
at target machines. This is similar but improved version from docker module
that comes with the ansible core. This module checks the state of running
containers and destroys and restarts a new container if it is not at the
requested state.

## Features

### State check
At the moment this module checks these container settings:
- Volume configurations
- Env variables
- Image name
- Command
If requested values for these settings do not match the values in the
existing container, then the container is destroyed and a new one
is created.

### Container states
**running**
Makes sure that the container is running and it is in the right state
**running_latest**
Makes sure that the container is running and that it is running the
latest image that exists locally
**absent**
Makes sure that the container does not exist
**restarted**
Restarts the container

### Image states
**Image_present**
Makes sure that image is present
**Image_latest**
Pulls image every time
**Image_absent**
Removes the image

## Todo
- Improve documentation
- Add state checks for port configuration
- Add tests
- Implement container linking
- Implement support for check mode
