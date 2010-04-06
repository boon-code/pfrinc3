#!/usr/bin/env python

DEBUG_ = True

import socket
import sys
import os
import logging
import pfutil
import pfpacket
import pfinfo
import pfutil
import pfmanager
import pfdetainer

LOGGER_NAME = 'pf-server'

import __main__
if 'DEBUG_' in dir(__main__):
    __main__.LOG_LEVEL_ = logging.DEBUG
else:
    DEBUG_ = False

if 'LOG_LEVEL_' in dir(__main__):
    log = logging.getLogger(LOGGER_NAME)
    log.setLevel(__main__.LOG_LEVEL_)
    if len(log.handlers) <= 0:
        st_log = logging.StreamHandler(sys.stderr)
        st_log.setFormatter(
            logging.Formatter("%(name)s : %(threadName)s : %(levelname)s : %(message)s"))
        log.addHandler(st_log)
        del st_log
    del log
else:
    log = logging.getLogger(LOGGER_NAME)
    log.setLevel(logging.CRITICAL)


CMD_PORT = 10030
INFO_PORT = CMD_PORT + 1
UPDATE_INTERVAL = 1
HISTORY_SIZE = 20
ACCEPT_LOOP_TIMEOUT = 1.0
USER_TIMEOUT = 8.0
RECV_SIZE = 1

class pfserver(object):
    
    def __init__(self, cfg_path):
        
        if 'NPYCK_' in globals():
            self._npyck = True
        else:
            self._npyck = False
        
        self._cfg = self.__loadconfig(cfg_path)
        
        self._cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._cmd_sock.bind(('', CMD_PORT))
        self._cmd_sock.listen(100)
        self._cmd_sock.settimeout(ACCEPT_LOOP_TIMEOUT)
        
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
                conn.settimeout(USER_TIMEOUT)
                try:
                    self.__recvcmd(conn)
                except socket.timeout:
                    conn.send("connection timeout")
                finally:
                    conn.close()
            except socket.timeout:
                pass
            except BaseException, ex:
                self._cmd_sock.close()
                self._man.kill()
                self._running = False
                raise ex
        
        self._cmd_sock.close()
        self._man.kill()
    
    
    def __recvcmd(self, conn):
        
        buffer = ''
        recv_buffer = conn.recv(RECV_SIZE)
        while recv_buffer != '':
            buffer += recv_buffer
            pos = buffer.find('\n\n')
            if pos >= 0:
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
                return
                
            else:
                recv_buffer = conn.recv(RECV_SIZE)
                
        return


def main(args):
    "The main entry-point."
    
    path = "config.txt"
    if len(args) > 0:
        path = args[0]
    
    server = pfserver(cfg_path = path)
    server.mainloop()
    
if __name__ == "__main__": main(sys.argv[1:])
