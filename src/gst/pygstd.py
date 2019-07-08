import argparse
import cmd
import curses
import json
import pprint
import psutil
import socket
import subprocess
import sys
import time
import traceback

GSTD_PROCNAME = 'gstd'

terminator = '\x00'.encode('utf-8')
max_size = 8192
def recvall(sock):
    buf = b''
    count = max_size
    try:
        while count:
            newbuf = sock.recv(max_size//8)
            if not newbuf: return None
            if terminator in newbuf:
                # this is the last item
                buf += newbuf[:newbuf.find(terminator)]
                break
            else:
                buf += newbuf
                count -= len(newbuf)
    except socket.error:
        buf = json.dumps({"error":"socket error", "msg": traceback.format_exc(), "code": -1 })
    return buf

class GSTD(object):
    def __init__(self, ip='localhost', port=5000):
        self.ip = ip
        self.port = port
        self.proc = None
        self.pipes = []
        self.gstd_started = False
        self.test_gstd()

    def __del__(self):
        for pipe in self.pipes:
            self.pipeline_delete(pipe)
        if (self.gstd_started):
            self.proc.kill()

    def gstd_client(self, line):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.ip, self.port))
            s.send(' '.join(line).encode('utf-8'))
            data = recvall(s)
            data = data.decode('utf-8')
        except socket.error:
            data = None
        return data

    def pipeline_create(self, pipe_name,  pipe_desc):
        cmd_line = ['pipeline_create', pipe_name, pipe_desc]
        print(cmd_line)
        jresult = self.gstd_client(cmd_line)
        result = json.loads(jresult)
        if (result['code'] == 0):
            self.pipes.append(pipe_name)
        return [result['code'], result['description']]

    def pipeline_delete(self, pipe_name):
        cmd_line = ['pipeline_delete', pipe_name]
        try:
            jresult = self.gstd_client(cmd_line)
            result = json.loads(jresult)
            return [result['code'], result['description']]
        except Exception:
            traceback.print_exc()
            return None

    def pipeline_play(self, pipe_name):
        cmd_line = ['pipeline_play', pipe_name]
        try:
            jresult = self.gstd_client(cmd_line)
            result = json.loads(jresult)
            return [result['code'], result['description']]
        except Exception:
            traceback.print_exc()
            return None

    def pipeline_pause(self, pipe_name):
        cmd_line = ['pipeline_pause', pipe_name]
        try:
            jresult = self.gstd_client(cmd_line)
            result = json.loads(jresult)
            return [result['code'], result['description']]
        except Exception:
            traceback.print_exc()
            return None

    def pipeline_stop(self, pipe_name):
        cmd_line = ['pipeline_stop', pipe_name]
        try:
            jresult = self.gstd_client(cmd_line)
            result = json.loads(jresult)
            return [result['code'], result['description']]
        except Exception:
            traceback.print_exc()
            return None

    def read(self, uri):
        cmd_line = ['read', uri]
        try:
            jresult = self.gstd_client(cmd_line)
            result = json.loads(jresult)
            return result
        except Exception:
            traceback.print_exc()
            return None

    def element_set(self, pipe_name, element, prop, value):
        cmd_line = ['element_set', pipe_name, "%s %s %s" % (element, prop, value) ]
        jresult = self.gstd_client(cmd_line)
        code = -1
        try:
            result = json.loads(jresult)
            code = [result['code'], result['description']]
            value = float(result['response']['value'])
        except ValueError:
            value = result['response']['value']
            if value=='true':
                value = True
            elif value=='false':
                value = False
        except KeyError:
            # The data did not contain a valid response
            value = None
        except TypeError:
            # This happens when jresult is not buf/str
            value = None
        if value!=None:
            ptzr[prop] = value
        return code

    def gstd_element_get(self, pipe_name, element, prop):
        cmd_line = ['element_get', pipe_name, "%s %s" % (element, prop) ]
        jresult = self.gstd_client(cmd_line)
        code = -1
        try:
            result = json.loads(jresult)
            code = [result['code'], result['description']]
            value = float(result['response']['value'])
        except ValueError:
            value = result['response']['value']
            if value=='true':
                value = True
            elif value=='false':
                value = False
        except KeyError:
            # The data did not contain a valid response
            value = None
        except TypeError:
            # This happens when jresult is not buf/str
            value = None
        if value==None:
            raise ValueError("invalid value received")
        return value

    def start_gstd(self):
        try:
            gstd_bin = subprocess.check_output(['which',GSTD_PROCNAME])
            gstd_bin = gstd_bin.rstrip()
            print("Starting GStreamer Daemon...")
            subprocess.Popen([gstd_bin])
            time.sleep(3)
            if self.test_gstd():
                self.gstd_started = True
                print("GStreamer Daemon started successfully!")
                return True
            else:
                print("GStreamer Daemon did not start correctly...")
                return False
        except subprocess.CalledProcessError:
            # Did not find gstd
            print("GStreamer Daemon is not running and it is not installed.")
            print("To get GStreamer Daemon, visit https://www.ridgerun.com/gstd.")
        return False

    def test_gstd(self):
        if self.ip not in ['localhost', '127.0.0.1']:
            # bypass process check, we don't know how to start gstd remotely
            print("Assuming GSTD is running in the remote host at %s" % self.ip )
            return True
        for proc in psutil.process_iter():
        # check whether the process name matches
            if proc.name() == GSTD_PROCNAME:
                self.proc = proc
        if self.proc or self.start_gstd():
            # we already had gstd or were able to start it.
            return True
        else:
            # we didn't had it, and we couldn't start it.
            return False
