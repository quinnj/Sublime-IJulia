import uuid, os, subprocess, threading, time, json
from ctypes import *
from subprocess import Popen
debug = 1
if not debug:
    import sublime, sublime_plugin

SETTINGS_FILE = 'Sublime-IJulia.sublime-settings'

def plugin_loaded():
    global zmq
    if not debug:
        settings = sublime.load_settings(SETTINGS_FILE)
        cmd = settings.get("zmq_shared_library")
        if sublime.platform() == 'windows':
            zmq = cdll.LoadLibrary(os.path.expanduser(cmd["windows"]))
        elif sublime.platform() == 'linux':
            zmq = cdll.LoadLibrary(os.path.expanduser(cmd["linux"]))
        else:
            zmq = cdll.LoadLibrary(os.path.expanduser(cmd["osx"]))
    else:
        zmq = cdll.LoadLibrary('C:/Users/karbarcca/.julia/ZMQ/deps/usr/lib/libzmq')
    #Return types
    zmq.zmq_msg_data.restype = c_char_p
    zmq.zmq_ctx_new.restype = c_void_p
    zmq.zmq_socket.restype = c_void_p
    zmq.zmq_setsockopt.restype = c_int
    zmq.zmq_connect.restype = c_int
    zmq.zmq_close.restype = c_int
    zmq.zmq_send.restype = c_int
    zmq.zmq_msg_recv.restype = c_int
    zmq.zmq_msg_size.restype = c_int
    zmq.zmq_strerror.restype = c_char_p
    #Argtypes
    zmq.zmq_socket.argtypes = [c_void_p, c_int]
    zmq.zmq_setsockopt.argtypes = [c_void_p, c_int, c_void_p, c_int]
    zmq.zmq_connect.argtypes = [c_void_p, c_char_p]
    zmq.zmq_close.argtypes = [c_void_p]
    zmq.zmq_send.argtypes = [c_void_p, c_void_p, c_size_t, c_int]
    zmq.zmq_msg_init.argtypes = [POINTER(_Message)]
    zmq.zmq_msg_recv.argtypes = [POINTER(_Message), c_void_p, c_int]
    zmq.zmq_msg_data.argtypes = [POINTER(_Message)]
    zmq.zmq_msg_size.argtypes = [POINTER(_Message)]

def zmq_error():
    err = zmq.zmq_errno()
    er = zmq.zmq_strerror(err)
    return er[:].decode()

def zmq_profile(filename, id):
    t = {"hb_port":5680 + (5*(id)),
         "control_port":5679 + (5*(id)),
         "stdin_port":5678 + (5*(id)),
         "ip":"127.0.0.1",
         "transport":"tcp",
         "shell_port":5681 + (5*(id)),
         "iopub_port":5682 + (5*(id)),
         "key":""}
    f = open(filename[1:-1], 'w')
    f.write(json.dumps(t))
    f.close()
    return t

PUB = 1
SUB = 2
REQ = 3
REP = 4
DEALER = 5
ROUTER = 6

NOBLOCK = 1
DONTWAIT = 1
SNDMORE = 2

class _Message(Structure):
    _fields_ = [
        ("w0", c_longlong),
        ("w1", c_longlong),
        ("w2", c_longlong),
        ("w3", c_longlong)]

class Message(object):
    def __init__(self):
        self.msg = _Message(0,0,0,0)
        zmq.zmq_msg_init(byref(self.msg))

class Msg(object):
    def __init__(self, idents, header, content, parent_header={}, metadata={}):
        self.idents = idents
        self.header = header
        self.content = content
        self.parent_header = parent_header
        self.metadata = metadata
    def __repr__(self):
        s1 = "idents: " + str(self.idents)
        s2 = "\nheader:" + str(self.header)
        s3 = "\ncontent:" + str(self.content)
        s4 = "\nparent_header:" + str(self.parent_header)
        s5 = "\nmetadata:" + str(self.metadata)
        return s1 + s2 + s3 + s4 + s5

class Context(object):
    def __init__(self):
        self.ptr = zmq.zmq_ctx_new()
        self.sockets = []

class Socket(object):
    def __init__(self, context, sock_type):
        self.ptr = zmq.zmq_socket(context.ptr, sock_type)
        self.alive = True
        context.sockets.append(self)
        if sock_type == SUB:
            zmq.zmq_setsockopt(self.ptr, 6, b'', 0)
            zmq.zmq_setsockopt(self.ptr, 27, 1000, 0)
        else:
            zmq.zmq_setsockopt(self.ptr, 28, 100, 0)

    def connect(self, endpoint):
        ret = zmq.zmq_connect(self.ptr, endpoint.encode())
        if ret != 0:
            print(zmq_error())

    def close(self):
        zmq.zmq_close(self.ptr)
        self.alive = False

    def send_msg(self, msg, flag=0):
        if self.alive:
            ret = zmq.zmq_send(self.ptr, msg.encode(), len(msg), flag)
            return ret
        else:
            return 0

    def send(self, m):
        self.send_msg(m.idents[0], SNDMORE)
        self.send_msg('<IDS|MSG>', SNDMORE)
        header = json.dumps(m.header)
        parent_header = json.dumps(m.parent_header)
        metadata = json.dumps(m.metadata)
        content = json.dumps(m.content)
        # self.send_msg(hmac(header, parent_header, metadata, content), SNDMORE)
        self.send_msg("", SNDMORE) #placeholder for no security
        self.send_msg(header, SNDMORE)
        self.send_msg(parent_header, SNDMORE)
        self.send_msg(metadata, SNDMORE)
        self.send_msg(content)

    def recv_msg(self):
        if self.alive:
            m = Message()
            zmq.zmq_msg_recv(byref(m.msg),self.ptr,NOBLOCK)
            data = zmq.zmq_msg_data(byref(m.msg))
            length = zmq.zmq_msg_size(byref(m.msg))
            return data[:length].decode()
        else:
            return ''

    def recv(self):
        msg = self.recv_msg()        
        signature = self.recv_msg()
        request = {}
        header = self.recv_msg()
        parent_header = self.recv_msg()
        metadata = self.recv_msg()
        content = self.recv_msg()
        m = Msg([""], json.loads(header), json.loads(content), json.loads(parent_header), json.loads(metadata))
        return m

    def recv_msg_block(self):
        m = Message()
        zmq.zmq_msg_recv(byref(m.msg),self.ptr,0)
        data = zmq.zmq_msg_data(byref(m.msg))
        length = zmq.zmq_msg_size(byref(m.msg))
        return data[:length].decode()

    def recv_block(self):
        msg = self.recv_msg_block()
        idents = []
        while msg != "<IDS|MSG>":
            idents.append(msg)
            msg = self.recv_msg_block()

        signature = self.recv_msg_block()
        request = {}
        header = self.recv_msg_block()
        parent_header = self.recv_msg_block()
        metadata = self.recv_msg_block()
        content = self.recv_msg_block()
        m = Msg(idents, json.loads(header), json.loads(content), json.loads(parent_header), json.loads(metadata))
        return m
        
class KernelManager(object):
    def __init__(self, id):
        self.id = id
        if not debug:
            settings = sublime.load_settings(SETTINGS_FILE)
            cmd = settings.get("julia_command")
            if sublime.platform() == 'windows':
                cmd = cmd["windows"]
            else:
                cmd = cmd["unix"]
            filename = '\"' + sublime.packages_path() + '/User/profile-' + str(id) + '.json\"'
        else:
            cmd = "julia-readline"
            filename = '\"C:/Users/karbarcca/AppData/Roaming/Sublime Text 3/Packages/User/profile-' + str(id) + '.json\"'
        profile = zmq_profile(filename, id)
        cmd = cmd + ' ' + os.path.expanduser('~/.julia/IJulia/src/kernel.jl ') + filename
        if not debug:
            if sublime.platform() == "windows":
                creationflags = 0x8000000 # CREATE_NO_WINDOW
            else:
                creationflags = 0
        else:
            creationflags = 0x8000000 # CREATE_NO_WINDOW
        print('Command Executed: %s' % cmd)
        self.kernel = Popen(cmd, shell=True, creationflags=creationflags)
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

    def shutdown(self, restart):
        shutdown_request = Msg(["shutdown_request"], 
            {"msg_id": str(uuid.uuid4()), 
             "username": str(self.id), 
             "session": str(uuid.uuid4()), 
             "msg_type": "shutdown_request"}, 
             {"restart": restart}, {})
        print("just about to send shutdown_request")
        ret = self.shell.send(shutdown_request)

    def hb_send(self):
        self.heartbeat.send_msg( str(time.time()) )

    def hb_recv(self):
        return self.heartbeat.recv_msg()

    def get_execute_reply(self):
        m = self.sub.recv()
        count = m.content['execution_count']
        data = m.content['data']['text/plain']
        return count, data

    def get_stdout(self):
        m = self.sub.recv()
        data = m.content['data']
        return data

    def get_error_reply(self):
        m = self.sub.recv()
        count = m.content['execution_count']
        data = m.content['evalue']
        return count, data  

    def get_status(self):
        m = self.sub.recv()
        return m.content['execution_state']

    def get_display_data(self):
        m = self.sub.recv()
        return

class RecvThread(threading.Thread):
    def __init__(self, kernel, julia_view):
        super(RecvThread, self).__init__()
        self.kernel = kernel
        self.heartbeat = kernel.heartbeat
        self.sub = kernel.sub
        self.shell = kernel.shell
        self.jv = julia_view
        self.startup = 1
        self.liveness = 5
        self.handlers = {'': self.emp_h,
                     'pyin': self.pyin_h,
                     'pyout': self.pyout_h,
                     'pyerr': self.pyerr_h,
                     'stdout': self.stdout_h,
                     'stderr': self.stderr_h,
                     'status': self.status_h,
                     'display_data': self.display_data_h}

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
            self.jv._view.set_status("kernel","IJulia kernel is working...")
        return 1

    def display_data_h(self):
        data = self.kernel.get_display_data()
        #self.jv.display_data_output(data)
        return 1

    def run(self):
        l = self.liveness
        while True:
            self.shell.recv_msg()
            m = self.sub.recv_msg()
            r = self.handlers.get(m, self.pyin_h)()
            if r:
                l = 5
            else:
                print("Heartbeat didn't get a response")
                l -= 1
            if l == 0:
                print("Kernel died, closing sockets....")
                self.kernel.heartbeat.close()
                self.kernel.sub.close()
                self.kernel.shell.close()
                print("Sockets closed...")
                self.jv.kernel_died()
                break