import requests
import bs4
import hashlib
import json
import os
import datetime
import pandas
import socket

class Router:
    def __init__(self, access_code, ip, hn=""):
        self.access_code = access_code
        self.hn = hn
        self.sess = requests.Session()
        self.addr = "http://" + ip
        self.sess_id = self._get_sess_id_from_file()
    
    def _get_sess_id_from_file(self):
        path = os.path.join(
            os.path.expanduser('~'),
            ".portman_sess_id_save"
        )
        print("Trying to load SessionID from " + path)
        if not os.path.exists(path):
            f = open(path, "w+")
            f.write("{}")
            f.close()
            print("save load unsuccessful, requesting a sessionid")
            #self.sess.get(self.addr + "/cgi-bin/home.ha") #Just to get a sesssionid cookie
            return
        f = open(path, "r")
        sid_file = json.load(f)
        if sid_file["login_time"] < (datetime.datetime.now()+datetime.timedelta(minutes=20)).timestamp() and sid_file["sid"] != "":
            print("save load successful")
            self.sess.cookies.set("SessionID", sid_file["sid"])
        else:
            print("save load unsuccesful")
    
    def _set_sess_id(self):
        path = os.path.join(
            os.path.expanduser('~'),
            ".portman_sess_id_save"
        )
        print("Trying to save SessionID to " + path)
        f = open(path, "r")
        sid_file = json.load(f)
        sid_file["sid"] = self.sess.cookies.get("SessionID", "")
        sid_file["login_time"] = datetime.datetime.now().timestamp()
        json.dump(sid_file, open(path, "w+"))
    
    def _get_a_sess_id(self):
        self.sess.get(self.addr + "/cgi-bin/home.ha")
    
    def _get_a_nonce(self, page):
        html = bs4.BeautifulSoup(self.sess.get(self.addr + page).content, "html.parser")
        return self._get_a_nonce_from_html(html)
    
    def _get_a_nonce_from_html(self, html):
        for inp in html.find_all("input"):
            if inp.get("name") == "nonce": return inp.get("value")
        raise Exception("Could not get a nonce from page with title: " + html.head.title.string)

    def _is_page_prompt_for_login(self, html):
        return html.text.find("Access Code Required") != -1

    def is_logged_in(self):
        res = self.sess.get(self.addr + "/cgi-bin/apphosting.ha")
        html = bs4.BeautifulSoup(res.content, "html.parser")
        return not self._is_page_prompt_for_login(html)
    
    def login(self):
        #login
        if self.is_logged_in():
            print("Already logged in")
            return
        nonce = self._get_a_nonce("/cgi-bin/apphosting.ha")
        hash = hashlib.md5((self.access_code + nonce).encode("utf-8")).hexdigest()
        res = self.sess.post(self.addr+"/cgi-bin/login.ha", data={
            "nonce": nonce,
            "password": "*" * len(self.access_code),
            "hashpassword": hash,
            "Continue": "Continue"
        }, allow_redirects=False)
        if res.status_code != 302: raise Exception("Login ended in invalid status code: " + str(res.status_code) + " (should be 302)")
        self._set_sess_id()
    
    def port_service_exsits(self, port):
        html = self.sess.get(self.addr + "/cgi-bin/services.ha").content
        if self._is_page_prompt_for_login(bs4.BeautifulSoup(html, "html.parser")): raise Exception("Not logged in yet!")
        df = pandas.read_html(html)[0]
        return df["Host Port"].isin([port]).any()
    
    def create_port_service(self, port):
        nonce = self._get_a_nonce("/cgi-bin/services.ha")
        res = self.sess.post(self.addr+"/cgi-bin/services.ha", data={
            "nonce": nonce,
            "Service": "Port " + str(port),
            "extMinPort": port,
            "extMaxPort": port,
            "intStartPort": port,
            "protocol": "both",
            "Add": "Add"
        }, allow_redirects=False)
        if res.status_code != 302: raise Exception("Create port service ended in invalid status code: " + str(res.status_code) + " (should be 302)")
    
    def is_port_open(self, port):
        html = self.sess.get(self.addr + "/cgi-bin/apphosting.ha").content
        if self._is_page_prompt_for_login(bs4.BeautifulSoup(html, "html.parser")): raise Exception("Not logged in yet!")
        df = pandas.read_html(html)[0]
        return df["Ports"].isin(["TCP/UDP: " + str(port)]).any()

    def _get_mac_addr_of_dev_from_page(self, page_html):
        hn = self.hn if self.hn != "" else socket.gethostname()
        host_dev_table = page_html.find("select", {"id": "hostdevice"})
        mac_addr = ""
        for option in host_dev_table.findChildren("option"):
            if option.string == hn: mac_addr = option["value"]
        if mac_addr == "": raise Exception("Could not find mac address for " + hn)
        return mac_addr
    
    def open_port(self, port):
        page_html = bs4.BeautifulSoup(self.sess.get(self.addr + "/cgi-bin/apphosting.ha").content, "html.parser")
        if self._is_page_prompt_for_login(page_html): raise Exception("Not logged in yet!")
        nonce = self._get_a_nonce_from_html(page_html)
        
        res = self.sess.post(self.addr+"/cgi-bin/apphosting.ha", data={
            "nonce": nonce,
            "service": "Port " + str(port),
            "device": self._get_mac_addr_of_dev_from_page(page_html),
            "Add": "Add"
        }, allow_redirects=False)
        if res.status_code != 302: raise Exception("Open port ended in invalid status code: " + str(res.status_code) + " (should be 302)")
    
    def close_port(self, port):
        page_html = bs4.BeautifulSoup(self.sess.get(self.addr + "/cgi-bin/apphosting.ha").content, "html.parser")
        if self._is_page_prompt_for_login(page_html): raise Exception("Not logged in yet!")
        nonce = self._get_a_nonce_from_html(page_html)
        
        delete_btns = page_html.find_all("input", {"type": "submit", "class": "cssbtn smallbtn"})
        del_btn = ""
        for btn in delete_btns:
            if btn.parent.parent.find("td", {"scope": "row", "class": "heading"}).string.strip() == "Port " + str(port):
                del_btn = btn["name"]
        if del_btn == "": raise Exception("Close port could not find the delete button for " + str(port) + ", is it open?")
        
        res = self.sess.post(self.addr+"/cgi-bin/apphosting.ha", data={
            "nonce": nonce,
            del_btn: "Delete",
            "service": "Port " + str(port),
            "device": self._get_mac_addr_of_dev_from_page(page_html)
        }, allow_redirects=False)
        if res.status_code != 302: raise Exception("Close port ended in invalid status code: " + str(res.status_code) + " (should be 302)")