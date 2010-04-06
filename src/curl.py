import subprocess
import re
import os
import signal
import select
import copy
import kill_except
import time

FULL_EXTR =("\\s*(\\d{1,3})" + 
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" + 
            "\\s*(\\d{1,3})" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" +
            "\\s*(\\d{1,3})" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})" +
            "\\s*(\\d+[:]{1}\\d+[:]{1}\\d+)" +
            "\\s*(\\d+[:]{1}\\d+[:]{1}\\d+)" +
            "\\s*(\\d+[:]{1}\\d+[:]{1}\\d+)" +
            "\\s*([0-9.]+[k,M,m,G,g]{0,1})\\s*")

FULL_EXTR_EXPR = re.compile(FULL_EXTR)

STATUS_PERCENT = 'percent'
STATUS_RETURN = 'rc'
STATUS_SPEED = 'speed'
STATUS_RUNNING = 'run'

DEFAULT_WAITTIME = 1

def mklist(*elements):
    return elements

def simple_download(link, *args):
    """ simple_download(link, *args)
    Just starts curl: 'curl link args[0] args[1] ...'
    Returns output of curl on stdout (normally the downloaded file)
    Don't use for big files (use class curl instead...)
    """
    
    args = mklist('curl', link, *args)
    print args
    subp = subprocess.Popen(args, stdout=subprocess.PIPE)
    return subp.communicate()[0]

class curl(object):
    """ curl
    This is a download class which uses the tool curl to download stuff.
    It's quite easy to use, just create curl object and the process starts...
    To get some information about the progress just call update, or use
    update_loop which will repeadetly call a callback funtion.
    
    Note that this class is (due to it's compactness) not threadsafe...
    It could be made threadsafe quite easily, just protect self._status
    with some threading.RLock() ...
    """
    
    def __init__(self, link, dest, args=[], cookie=None):
        """ __init__(self, link, dest, *args)
        This constructor starts downloading link and safes it to 
        dest (file). Args will be passed to curl tool.
        """
        
        self._status = {STATUS_PERCENT : 0, STATUS_SPEED : "???", 
            STATUS_RUNNING : True, STATUS_RETURN : None}
        self._line = ""
        
        if cookie is None:
            args = mklist('curl', link, '-o', dest, *args)
            self._sproc = subprocess.Popen(args, stderr=subprocess.PIPE)
        else:
            args = mklist('curl', link, '-o', dest, "--cookie", "-", *args)
            self._sproc = subprocess.Popen(args, stderr = subprocess.PIPE,
                stdin = subprocess.PIPE)
            self._sproc.stdin.write(cookie)
            self._sproc.stdin.close()
    
    def __read_line(self):
        
        while True:
            ch = self._sproc.stderr.read(1)
        
            if ch == '\r' or ch == '\n':
                re_full = FULL_EXTR_EXPR.search(self._line)
                if not (re_full is None):
                    self._status[STATUS_PERCENT] = int(re_full.group(3))
                    self._status[STATUS_SPEED] = re_full.group(12)
                    self._line = ''
                    return True
            elif ch != '':
                self._line += ch
            else:
                return False
        
        
            
    def update(self, waittime=None):
        """ update(self, waittime=None)
        Here you can see the progress. waittime defines an additional wait
        time. None means don't wait.
        
        'update' runs reads up output-stream of curl until it blocks.
        
        'update' returns a copy of self._status (the current status) which
        is a dictionary which contains information like if curl still is working,
        if there was an error, return codes, progress etc..
        """
        
        stderr_no = self._sproc.stderr.fileno()
        rlist = [stderr_no]
        
        if not (waittime is None):
            time.sleep(waittime)
        
        while stderr_no in select.select(rlist, [], [], 0)[0]:
            ch = self._sproc.stderr.read(1)
        
            if ch == '\r' or ch == '\n':
                re_full = FULL_EXTR_EXPR.search(self._line)
                if not (re_full is None):
                    self._status[STATUS_PERCENT] = int(re_full.group(3))
                    self._status[STATUS_SPEED] = re_full.group(12)
                    self._line = ''
            elif ch != '':
                self._line += ch
            else:
                break
                
        if not (self._sproc.poll() is None):
            self._status[STATUS_RUNNING] = False
            self._status[STATUS_RETURN] = self._sproc.poll()
        
        return copy.copy(self._status)
    
    def update_loop(self, callback=None, waittime=DEFAULT_WAITTIME):
        """ update_loop(self, callback=None, waittime=DEFAULT_WAITTIME)
        This function blocks till curl has finished, it repeatedly calls
        callback if it's not None.
        """
        
        if waittime is None:
            waittime = DEFAULT_WAITTIME
        
        while self._status[STATUS_RUNNING]:
            
            if self.__read_line():
                if not (callback is None):
                    try:
                        status = copy.copy(self._status)
                        callback(status)
                    except kill_except.KillException:
                        self.kill()
                        return None
                    except:
                        print "callback failed"
            else:
                if self._sproc.poll() is None:
                    time.sleep(waittime)
                else:
                    self._status[STATUS_RUNNING] = False
                    self._status[STATUS_RETURN] = self._sproc.poll()
        
    def kill(self):
        " kill(self) sends a SIGTERM signal to the curl process"
        
        if self._sproc.poll() is None:
            os.kill(self._sproc.pid, signal.SIGTERM)
            return True
        else:
            return False

