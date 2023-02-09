#What this needs to do:
# take in cli args
# open port on router
# based on ssl arg, add nginx server block to stream normal or ssl
# restart nginx

import argparse
from .subsystems import NginxConfig
from .subsystems import Router
from .subsystems import get_config_object
import os
import subprocess
import sys

def get_hostname_from_fn(path):
    fn = os.path.basename(path)
    if fn.endswith(".conf"):
        return fn[0:len(fn)-5]
    return fn

def main():
    ap = argparse.ArgumentParser(
        prog="portman",
        usage="Open a port on bgw210 router, add a server block to nginx, and optionally proxy it through ssl"
    )

    ap.add_argument("port", help="The port you want to open", type=int)
    ap.add_argument("-s", "--ssl", help="Modify the first nginx site config in sites-availble to listen on this port as well (assumes the port you want to open is bound to localhost)", default=False, type=bool)
    ap.add_argument("-c", "--close", help="Add this if you would like to close the port, instead of opening it.", default=False, type=bool)

    args = ap.parse_args()
    
    conf = get_config_object()
    router = Router(conf["access_code"], conf["router_ip"])
    ng = NginxConfig(conf["nginx_site_loc"], conf["cert_loc"], get_hostname_from_fn(conf["nginx_site_loc"]))
    
    router.login()
    if not args["close"]:
        try:
            #Open a port
            print("[ROUTER] Ensuring port service exists")
            if not router.port_service_exsits(args["port"]):
                print("[ROUTER] Creating port service...")
                router.create_port_service(args["port"])
                print("[ROUTER] Opening port...")
                router.open_port(args["port"])
            else:
                print("[ROUTER] Port service exsists, ensuring it is not already open...")
                if router.is_port_open(args["port"]):
                    print(str(args["port"]) + " is already open")
                else:
                    print("[ROUTER] Opening port...")
                    router.open_port()
        except Exception as e:
            if not input(f"There was an error trying to open { str(args['port']) }: {e}. Would you like to continue? y for yes").lower() == 'y': sys.exit(1)
        print("Done with router port open, adding nginx config block...")
        ng.add_stream(args["port"], args["ssl"])
        ng.save()
        print("Restarting nginx...")
        subprocess.run("systemctl restart nginx.service", shell=True)
        print("Done!")
    else:
        try:
            #close a port
            print("[ROUTER] Ensuring port is open")
            if router.is_port_open(args["port"]):
                print("[ROUTER] Closing port")
                router.close_port(args["port"])
            else:
                if not input(f"{ str(args['port']) } is already closed. Would you like to continue? y for yes").lower() == 'y': sys.exit(1)
        except:
            if not input(f"There was an error trying to close { str(args['port']) }: {e}. Would you like to continue? y for yes").lower() == 'y': sys.exit(1)
        print("Done with router port close, deleting nginx config block...")
        ng.close_stream(args["port"])
        ng.save()
        print("Restarting nginx...")
        subprocess.run("systemctl restart nginx.service", shell=True)
        print("Done!")