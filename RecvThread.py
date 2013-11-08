import threading
import time

class RecvThread(threading.Thread):
    def __init__(self, kernel, julia_view):
        super(RecvThread, self).__init__()
        self.kernel = kernel
        self.heartbeat = kernel.heartbeat
        self.sub = kernel.sub
        self.jv = julia_view
        self.liveness = 5 #liveness
        self.handlers = {'': self.emp_h,
                     'pyin': self.pyin_h,
                     'pyout': self.pyout_h,
                     'pyerr': self.pyerr_h,
                     'stdout': self.stdout_h,
                     'stderr': self.stderr_h,
                     'status': self.status_h}

    def emp_h(self):
        l = self.liveness
        self.heartbeat.send()
        time.sleep(.1)
        response = self.heartbeat.recv()
        if response == '':
            l -= 1
            if l == 0:
                pass #for now

    def pyin_h(self):
        self.sub.recv()

    def pyout_h(self):
        count, data = self.kernel.get_execute_reply()
        self.jv.output(count,data)

    def pyerr_h(self):
        count, data = self.kernel.get_error_reply()
        self.jv.output(count,data)

    def stdout_h(self):
        data = self.kernel.get_stdout()
        self.jv.stdout_output(data)

    def stderr_h(self):
        data = self.kernel.get_stdout()
        self.jv.stdout_output(data)

    def status_h(self):
        status = self.kernel.get_status()
        if status == 'idle':
            self.jv.in_output()

    def run(self):
        while True:
            m = self.sub.recv_msg()
            self.handlers[m]()