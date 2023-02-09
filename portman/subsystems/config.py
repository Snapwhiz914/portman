from schema import Schema
from yaml.scanner import ScannerError
from yaml.parser import ParserError
import yaml
import os

conf_schema = Schema({
    "access_code": str,
    "router_ip": str,
    "nginx_site_loc": str,
    "cert_loc": str
})

def get_config_object():
    try:
        file_obj = open("/etc/portman.yaml", "r")
        result = yaml.safe_load(file_obj)
        validated = conf_schema.validate(result)
        if not (os.path.isfile(validated["nginx_site_loc"]) and os.path.isdir(validated["cert_loc"])):
            raise Exception("nginx_site_loc or cert_loc has an invalid path. Make sure nginx_site_loc points to a nginx config file and cert_loc points to a directory with .pem files")
        return validated
    except FileNotFoundError as e:
        raise Exception("Config file not found.")
    except ScannerError as e:
        raise Exception(f"YAML scanner error when trying to load config: {e}")
    except ParserError as e:
        raise Exception(f"YAML Parser error: check config syntax: {e}")