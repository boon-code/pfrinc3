#!/usr/bin/env python

DEBUG_ = True

import socket
import sys
import os
import pfutil
import pfpacket
import pfinfo
import pfutil
import pfmanager
import pfdetainer

CMD_PORT = 10030
INFO_PORT = CMD_PORT + 1
UPDATE_INTERVAL = 1
HISTORY_SIZE = 20
DEFAULT_BLOCK_TIME = 5.0

class pfserver(object):
    
    def __init__(self, cfg_path):
        
        print globals()
        if 'NPYCK_' in globals():
            self._npyck = True
        else:
            self._npyck = False
        
        self._cfg = self.__loadconfig(cfg_path)
        
        self._cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._cmd_sock.bind(('', CMD_PORT))
        self._cmd_sock.listen(100)
        self._cmd_sock.settimeout(pfutil.DEFAULT_SOCKET_TIMEOUT)
        
        self._det = pfdetainer.mem_detainer()
        self._info = pfinfo.info_server(INFO_PORT)
        self._man = pfmanager.manager(self._cfg, self._det, self._info)
        
        self._running = True
    
    def __loadconfig(self, cfg_path):
        
        data = None
        
        if self._npyck:
            data = NPYCK_.ne_read(cfg_path)
        
        if data is None:
            f = open(cfg_path, "r")
            data = f.read()
            f.close()
        
        cfg = {}
        
        for line in data.split('\n'):
            line = line.strip('\r')
            if line.startswith('from'):
                cfg['from'] = line.lstrip('from').strip(' ')
            elif line.startswith('to'):
                cfg['to'] = line.lstrip('to').strip(' ')
            elif line.startswith('pwd'):
                cfg['pwd'] = line.lstrip('pwd').strip(' ').split(' ')
            elif line.startswith('cfg'):
                cfg['cfg'] = line.lstrip('cfg').strip(' ')
        
        data = None
        
        if self._npyck:
            data = NPYCK_.read("rapidshare-cookie")
        
        if data is None:
            f = open(os.path.join(cfg['cfg'], "rapidshare-cookie"), 'r')
            data = f.read()
            f.close()
        
        cfg['rapidshare'] = data
        
        return cfg
    
    
    def mainloop(self):
        
        while self._running:
            try:
                conn, address = self._cmd_sock.accept()
                conn.setblocking(DEFAULT_BLOCK_TIME)
                
                self.__recvcmd(conn)
            except socket.timeout:
                pass
        
        self._cmd_sock.close()
        self._man.kill()
    
    
    def __recvcmd(self, conn):
        
        buffer = ''
        while 1:
            recv_buffer = conn.recv(pfutil.DEFAULT_RECV_SIZE)
            buffer += recv_buffer
            pos = buffer.find('\n\n')
            if recv_buffer == '':
                return
            elif pos >= 0:
                data = buffer[0:pos].split(' ', 1)
                if data[0] == 'add':
                    link_count = self._man.padd(data[1].split(' '))
                    conn.send("added %d links" % link_count)
                elif data[0] == 'start':
                    if self._man.pstart(data[1]):
                        conn.send("ok")
                    else:
                        conn.send("failed")
                elif data[0] == 'exit-force-bad':
                    conn.send("failed, not implemented")
                elif data[0] == 'shutdown':
                    result = pfutil.shutdown()
                    if result:
                        conn.send(result)
                elif data[0] == 'exit':
                    self._running = False
                    conn.send("ok, state set")
                elif data[0] == 'update':
                    #self.infoserver_update()
                    #conn.send("ok")
                    conn.send("failed, not implemented")
                elif data[0] == 'get-last-links':
                    conn.send("not imlemented")
                elif data[0] == 'tmp-add-pwd':
                    if len(data) > 1:
                        self._man.tmp_add_pwd(data[1])
                        conn.send("ok")
                    else:
                        conn.send("failed")
                elif data[0] == 'pwd-list':
                    p_list = "\n".join(self._cfg['pwd'])
                    conn.send(p_list)
                elif data[0] == 'history':
                    lt = '\n'.join(self._det.get_finished(count = 20))
                    conn.send(lt)
                else:
                    conn.send("wrong cmd")
                
                conn.close()
                return


def main(args):
    "The main entry-point."
    
    path = "config.txt"
    if len(args) > 0:
        path = args[0]
    
    server = pfserver(cfg_path = path)
    server.mainloop()
    
if __name__ == "__main__": main(sys.argv[1:])
