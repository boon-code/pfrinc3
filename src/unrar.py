import subprocess
import re
import os
import signal
import select
import copy
import kill_except
import time

UNRAR_CRC_ERROR = re.compile("CRC failed in ([A-Za-z0-9,\\/, ,\\.,_,\\-,\\,,#]+)")
UNRAR_PERCENT = re.compile("(\\d+)%")
UNRAR_MISSING_VOLUME = re.compile("Cannot find volume ([A-Za-z0-9,\\/, ,\\.,_,\\-,\\,,#]+)")
UNRAR_ALL_OK = re.compile("All OK")
UNRAR_NOOPEN = re.compile("Cannot open ([A-Za-z0-9,\\/, ,\\.,_,\\-,\\,,#]+)")

STATUS_PERCENT = 'percent'
STATUS_OK = 'success'
STATUS_RETURN = 'rc'
STATUS_MSG = 'status'
STATUS_RUNNING = 'run'

DEFAULT_WAITTIME = 1

def mklist(*elements):
    return elements

class unrar(object):
    """ the 'unrar' class
    
    This class uses the unrar program to extract the given file (filepath)
    to the dst_dir directory. Filepath must be an absolut path because
    the program will be started with the working directory set to dst_path
    (well you could relativ paths to the working directory...)
    
    It should be quite easy to use this class, just create an instance
    and call update to see unrar processing your files. 
    You could also call update_loop and give it a callback function. This
    function will be called each time unrar produces some wired output... ;P
    
    Take care that you only uses this class in one thread because it's not
    designed for beeing used in multithreaded environments. Note that it could
    very easily be made thread safe, just protect self._status with some
    threading.RLock() for example...
    """
    
    def __init__(self, filepath, dst_dir, pwd):
        """"__init__(self, filepath, dst_dir, pwd)
        
        starts extraction of filepath (absolut path) to dst_dir with 
        pwd (password)
        Note that this class will always use a password... (ugly)
        """
        
        self._status = {STATUS_MSG : "extracting", STATUS_PERCENT : 0,
            STATUS_RETURN : None, STATUS_OK : False,
            STATUS_RUNNING : True}
        
        self._err_crc = None
        self._err_miss = None
        self._no_open = None
        self._line = ''
        
        args = mklist("unrar", "-ierr", "e", "-o+", '-p' + pwd, filepath)
        self._sproc = subprocess.Popen(args, stderr=subprocess.PIPE,
            cwd=dst_dir)
    
    def __read_line(self):
        
        while True:
            ch = self._sproc.stderr.read(1)
            
            if ch == '\r' or ch == '\n':
                self.__update_line()
                self._line = ''
                return True
            elif ch == '\x08':
                re_percent = UNRAR_PERCENT.search(self._line)
        
                if not (re_percent is None):
                    self._status[STATUS_PERCENT] = int(re_percent.group(1))
                    self._line = self._line[re_percent.end():]
                    return True
            elif ch != '':
                self._line += ch
            else:
                return False
    
    def update(self, waittime=None):
        """ update(self, waittime = None)
        Here you can see the progress. waittime defines an additional wait
        time. None means don't wait.
        
        'update' runs reads up output-stream of unrar until it blocks.
        
        'update' returns a copy of self._status (the current status) which
        is a dictionary which contains info like if unrar still is working,
        if there was an error, return codes etc..
        """
        
        if waittime is None:
            waittime = DEFAULT_WAITTIME
        
        stderr_no = self._sproc.stderr.fileno()
        rlist = [stderr_no]
        
        while stderr_no in select.select(rlist, [], [], 0)[0]:
            ch = self._sproc.stderr.read(1)
            
            if ch == '\r' or ch == '\n':
                self.__update_line()
                self._line = ''
            elif ch == '\x08':
                re_percent = UNRAR_PERCENT.search(self._line)
        
                if not (re_percent is None):
                    self._status[STATUS_PERCENT] = int(re_percent.group(1))
                    self._line = self._line[re_percent.end():]
            elif ch != '':
                self._line += ch
            else:
                break
                
        if not (self._sproc.poll() is None):
            self._status[STATUS_RUNNING] = False
            self._status[STATUS_RETURN] = self._sproc.poll()
        
        return copy.copy(self._status)
    
    def __update_line(self):
        
        re_error = UNRAR_CRC_ERROR.search(self._line)
        re_missing = UNRAR_MISSING_VOLUME.search(self._line)
        re_ok = UNRAR_ALL_OK.search(self._line)
        re_percent = UNRAR_PERCENT.search(self._line)
        re_noopen = UNRAR_NOOPEN.search(self._line)
        
        if not (re_percent is None):
            self._status[STATUS_PERCENT] = int(re_percent.group(1))
        
        if not (re_error is None):
            self._err_crc = re_error.group(1)
            
        if not (re_missing is None):
            self._err_miss = re_missing.group(1)
        
        if not (re_noopen is None):
            self._no_open = re_noopen.group(1)
            
        if not (re_ok is None):
            self._status[STATUS_OK] = True
        
        if not (self._no_open is None):
            self._status[STATUS_MSG] = ("couldn't open file(s) %s" % 
                self._no_open)
        elif not (self._err_miss is None):
            self._status[STATUS_MSG] = ("missing file(s) %s" % 
                self._err_miss)
        elif not (self._err_crc is None):
            self._status[STATUS_MSG] = ("crc error or wrong pwd in %s " %
                self._err_crc)
    
    def update_loop(self, callback=None, waittime=DEFAULT_WAITTIME):
        """ update_loop(self, callback = None, timeout = None)
        This function blocks till unrar has finished, it repeatedly calls
        callback if it's not None.
        """
        
        while self._status[STATUS_RUNNING]:
            
            if self.__read_line():
                if not (callback is None):
                    try:
                        status = copy.copy(self._status)
                        callback(status)
                    except kill_except.KillException:
                        self.kill()
                        return
                    except TypeError:
                        print "callback failed"
            else:
                if self._sproc.poll() is None:
                    time.sleep(waittime)
                else:
                    self._status[STATUS_RUNNING] = False
                    self._status[STATUS_RETURN] = self._sproc.poll()
        
    def kill(self):
        " kill(self) sends a SIGTERM signal to the unrar process"
        
        if self._sproc.poll() is None:
            os.kill(self._sproc.pid, signal.SIGTERM)
            return True
        else:
            return False
