import nginx
import socket
import os

#Expected nginx config file pattern:
#stream {
#    server{}
#    server{}
#    server{}
#}

def get_bind_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    sn = s.getsockname()[0]
    s.close()
    return sn

def generate_stream_block(port):
    srv = nginx.Server()
    srv.add(
        nginx.Key("listen", get_bind_ip() + ":" + str(port) + " udp"),
        nginx.Key("listen", get_bind_ip() + ":" + str(port)),
        nginx.Key("proxy_pass", "127.0.0.1:" + str(port))
    )
    return srv

def generate_ssl_block(port, cert_file_loc):
    srv = nginx.Server()
    srv.add(
        nginx.Key("listen", get_bind_ip() + ":" + str("port") + " ssl"),
        nginx.Key("server_name", "res-no1.asilvers.com"),
        nginx.Location("/", 
            nginx.Key("proxy_pass", "http://127.0.0.1:" + str(port)),
            nginx.Key("proxy_set_header", "X-Real-IP $remote-addr"),
            nginx.Key("proxy_set_header", "X-Forwarded-For $proxy_add_x_forwarded_for"),
            nginx.Key("proxy_set_header", "X-Forwarded-Host $host:$server_port;"),
            nginx.Key("proxy_set_header", "X-Forwarded-Proto $scheme;"),
            nginx.Key("proxy_set_header", "X-Nginx-Proxy true"),
            nginx.Key("proxy_http_version", "1.1"),
            nginx.Key("proxy_set_header", "Upgrade $http_upgrade"),
            nginx.Key("proxy_set_header", 'Connection "upgrade"'),
            nginx.Key("proxy_set_header", "Host $host"),
            nginx.Key("client_max_body_size", "100M"),
            nginx.Key("proxy_buffering", "off"),
            nginx.Key("proxy_read_timeout", "64800"),
            nginx.Key("proxy_send_timeout", "64800"),
            nginx.Key("proxy_connect_timeout", "64800"),
            nginx.Key("proxy_socket_keepalive", "on"),
            nginx.Key("keepalive_requests", "1000"),
            nginx.Key("keepalive_timeout", "64800"),
            nginx.Key("send_timeout", "64800"),
        ),
        nginx.Key("ssl_certificate", os.path.join(cert_file_loc, "fullchain.pem")),
        nginx.Key("ssl_certificate_key", os.path.join(cert_file_loc, "privkey.pem")),
        nginx.Key("include", "/etc/letsencrypt/options-ssl-nginx.conf"),
        nginx.Key("ssl_dhparam", "/etc/letsencrypt/ssl-dhparams.pem")
    )
    return srv

class NginxConfig():
    def __init__(self, config_file_loc, cert_file_loc, hostname):
        self.config_file_loc = config_file_loc
        self.cert_file_loc = cert_file_loc
        self.hostname = hostname
        self.conf = nginx.loadf(self.config_file_loc)
        self.top_level = self.conf.children[0]
    
    def _does_server_exist(self, port):
        for server in self.top_level.children:
            if str(port) == server.children[0].value.split(" ")[0]: return True
        return False
    
    def add_stream(self, port, ssl):
        if self._does_server_exist(port): raise Exception("Server for port " + str(port) + " already exists")
        if ssl:
            self.top_level.add(generate_ssl_block(port))
        else:
            self.top_level.add(generate_stream_block(port))
        
    def close_stream(self, port):
        if not self._does_server_exist(port): raise Exception("Server for port " + str(port) + " does not exist")
        for server in self.top_level.children:
            if str(port) == server.children[0].value.split(" ")[0]:
                self.top_level.remove(server)
    
    def save(self):
        self.conf.remove(self.conf.children[0])
        self.conf.add(self.top_level)
        nginx.dumpf(self.conf, self.config_file_loc)