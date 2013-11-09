from .ZMQ import *
#from ZMQ_test import *
import uuid
import os
import subprocess
import threading
import time

class KernelManager(object):
    def __init__(self, cmd, id, profile):
        self.id = id
        if os.name == "nt":
            creationflags = 0x8000000 # CREATE_NO_WINDOW
        else:
            creationflags = 0
        print("cmd: %s" % cmd)
        self.kernel = subprocess.Popen(cmd, creationflags=creationflags)
        ip = profile['transport'] + '://' + profile['ip'] + ':'
        self.context = Context()
        self.heartbeat = Socket(self.context, REQ)
        self.heartbeat.connect(ip + str(profile['hb_port']))
        self.shell = Socket(self.context, REQ)
        self.shell.connect(ip + str(profile['shell_port']))
        self.sub = Socket(self.context, SUB)
        self.sub.connect(ip + str(profile['iopub_port']))

    def execute(self, code):
        execute_request = Msg(["execute_request"], 
            {"msg_id": str(uuid.uuid4()), 
             "username": str(self.id), 
             "session": str(uuid.uuid4()), 
             "msg_type": "execute_request"}, 
             {"code": code, 
              "silent": False, 
              "store_history": False, 
              "user_variables": list(), 
              "user_expressions": {}, 
              "allow_stdin": True}, {})
        ret = self.shell.send(execute_request)
        #Next is getting the response back from the kernel, which can be
        #tricky if the kernel blocks upon executing code, so we just know
        #we need to get 6 messages and recv_msg() non-blocks otherwise
        count = 6
        while count:
            m = self.shell.recv_msg()
            if m:
                count -= 1
            else:
                time.sleep(.1)

    def shutdown(self, restart):
        shutdown_request = Msg(["shutdown_request"], 
            {"msg_id": str(uuid.uuid4()), 
             "username": str(self.id), 
             "session": str(uuid.uuid4()), 
             "msg_type": "shutdown_request"}, 
             {"restart": restart}, {})
        ret = self.shell.send(shutdown_request)
        #Next is getting the response back from the kernel, which can be
        #tricky if the kernel blocks, so we just know
        #we need to get 6 messages and recv_msg() non-blocks otherwise
        count = 6
        while count:
            m = self.shell.recv_msg()
            if m:
                count -= 1
            else:
                time.sleep(.1)

    def hb_send(self):
        self.heartbeat.send_msg( str(time.time()) )

    def hb_recv(self):
        return self.heartbeat.recv_msg()

    def get_execute_reply(self):
        m = self.sub.recv_block()
        count = m.content['execution_count']
        data = m.content['data']['text/plain']
        return count, data

    def get_stdout(self):
        m = self.sub.recv_block()
        data = m.content['data']
        return data

    def get_error_reply(self):
        m = self.sub.recv_block()
        count = m.content['execution_count']
        data = m.content['evalue']
        return count, data  

    def get_status(self):
        m = self.sub.recv_block()
        return m.content['execution_state']   

class RecvThread(threading.Thread):
    def __init__(self, kernel, julia_view):
        super(RecvThread, self).__init__()
        self.kernel = kernel
        self.heartbeat = kernel.heartbeat
        self.sub = kernel.sub
        self.jv = julia_view
        self.startup = 1
        self.liveness = 5 #liveness
        self.handlers = {'': self.emp_h,
                     'pyin': self.pyin_h,
                     'pyout': self.pyout_h,
                     'pyerr': self.pyerr_h,
                     'stdout': self.stdout_h,
                     'stderr': self.stderr_h,
                     'status': self.status_h}

    def emp_h(self):
        r = self.kernel.hb_send()
        time.sleep(.1)
        response = self.kernel.hb_recv()
        if self.startup or response or r:
            return 1
        else:
            return 0

    def pyin_h(self):
        self.sub.recv()
        return 1

    def pyout_h(self):
        count, data = self.kernel.get_execute_reply()
        self.jv.output(count,data)
        return 1

    def pyerr_h(self):
        count, data = self.kernel.get_error_reply()
        self.jv.output(count,data)
        return 1

    def stdout_h(self):
        data = self.kernel.get_stdout()
        self.jv.stdout_output(data)
        return 1

    def stderr_h(self):
        data = self.kernel.get_stdout()
        self.jv.stdout_output(data)
        return 1

    def status_h(self):
        status = self.kernel.get_status()
        if status == 'idle':
            self.jv.in_output()
            self.jv._view.set_status("kernel","")
        else:
            self.jv._view.set_status("kernel","Julia kernel is working...")
        return 1

    def run(self):
        l = self.liveness
        while True:
            m = self.sub.recv_msg()
            r = self.handlers.get(m, self.pyin_h)()
            if r:
                l = 5
            else:
                l -= 1
            if l == 0:
                break