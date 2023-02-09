#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "This must be run as root (to create config file)."
  exit
fi

#Install packages
#Uninstall in case already installed
python3 -m pip uninstall -y portman

if python3 -m pip install .; then
    echo "Package install succeeded."
else
    echo "Package install failed! Check and resolve using errors above."
    exit
fi

#Create a config file
CONFIG_TEMPLATE=$'access_code: <insert_ac_here>
router_ip: 192.168.1.254
nginx_site_loc: /etc/nginx/sites-available/default
cert_loc: /etc/certbot/'

if [ -f "/etc/portman.yaml" ]
then
    echo "/etc/portman.yaml has already been created, not overwriting..."
else
    touch /etc/portman.yaml
    echo "$CONFIG_TEMPLATE" > /etc/portman.yaml
fi

echo "Check the output above and make sure at was installed."