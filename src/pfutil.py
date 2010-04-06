import socket
import Queue
import threading
import re
# BAD: on windows this wouldn't be possible
import os
import time
import subprocess
import unrar
import curl

DEFAULT_SOCKET_TIMEOUT = 0.5
DEFAULT_TIMEOUT = 1.0
DEFAULT_RECV_SIZE = 10
UPDATE_INTERVAL = 0.5
LINK_FINDER_STR = "http://([^\",^\n^/,^\\s,^<,^>]+)([^\",^\\s,^\n,^<,^>]*)"
LINK_FINDER_RE = re.compile(LINK_FINDER_STR)
PACKET_NAME_RE = re.compile(".*/([^/]*)[.]{1}part\\d+[.]{1}rar")
PACKET_NAME_SIMPLE_RE = re.compile(".*/([^/]*)[.]{1}rar")
FILENAME_RE = re.compile(".*/([^/]*)")

def mklist(*elements):
    return elements

class extractor(object):
    
    def __init__(self, source, dest, pwds):
        "Creates and configures an extractor-object"
        
        self._to = dest
        self._from = source
        self._pwd = pwds
    
    def extract(self, filename, proc=None):
        "Starts extractor-utility and extracts packets."
        
        file_path = os.path.join(self._from, filename)
        
        for pwd in self._pwd:
            unr = unrar.unrar(file_path, self._to, pwd)
            unr.update_loop(callback=proc)
            
            if unr.update()[unrar.STATUS_OK]:
                return True
        
        return False


def scanlinks(data):
    "Scans data and finds links, converts them to rapidshare-links."
    
    def __sjdecode(link):
        "Extract Rapidshare link from Serienjunkies."
        
        site = curl.simple_download(link, '-L')
        result = LINK_FINDER_RE.search(site)
        if result is None:
            return ''
        else:
            return "".join(result.groups())
    
    def __rsdecode(link):
        "Prepare Rapidshare link for final download."
        
        if link == '':
            return ''
        
        site = curl.simple_download(link, '-L')
        pos = site.find("form action")
        
        if pos != -1:
            site = site[pos:]
        
        item = LINK_FINDER_RE.search(site)
        if item is None:
            return ''
        
        path = os.path.split(item.group(2))
        link_end = os.path.join(path[0], 'dl', path[1])
        link = "".join(("http://", item.group(1), link_end))
        return link
        
    lsf = LINK_FINDER_RE.findall(data)
    links = []
        
    for i in lsf:
        link = "".join(i)
        if i[0] == "download.serienjunkies.org":
            link = __sjdecode(link)
            link = __rsdecode(link)
            if link != '':
                links.append(link)
                
        elif i[0] == "rapidshare.com":
            link = __rsdecode(link)
            if link != '':
                links.append(link)
        
    return links

def loadconfig(path):
    
    f = open(path, 'r')
    cfg = {}
    
    for line in f:
        line = line.rstrip('\n')
        line = line.rstrip('\r')
        if line.startswith('from'):
            cfg['from'] = line.lstrip('from').strip(' ')
        elif line.startswith('to'):
            cfg['to'] = line.lstrip('to').strip(' ')
        elif line.startswith('pwd'):
            cfg['pwd'] = line.lstrip('pwd').strip(' ').split(' ')
        elif line.startswith('work'):
            cfg['work'] = line.lstrip('work').strip(' ')
        elif line.startswith('cfg'):
            cfg['cfg'] = line.lstrip('cfg').strip(' ')
        
    cfg['rapid-share'] = os.path.join(cfg['cfg'], 
            "rapidshare-cookie")
    
    cfg['extractor'] = os.path.join(cfg['work'], "extractor")
    
    cfg['last-links-file'] = os.path.join(cfg['cfg'], "last-links")
    
    cfg['finished-file'] = os.path.join(cfg['cfg'], "finished-packets")
    
    f.close()
    return cfg

def shutdown():
    args = ['smbstatus', '--locks']
    subp = subprocess.Popen(args, stdout = subprocess.PIPE)
    result = subp.communicate()[0]
    
    if result.find("Locked files") < 0:
        args = ['gnome-power-cmd.sh', 'shutdown']
        subp = subprocess.Popen(args, stdout = subprocess.PIPE)
        result = subp.communicate()[0]
        return "init shutdown: " + result
    else:
        return ("failed because of locked files\n%s\n" % result)
