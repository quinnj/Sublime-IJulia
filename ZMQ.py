from ctypes import *
import json
import os, sublime, sublime_plugin

pkg_dir = os.path.expanduser("~/.julia")
if sublime.platform() == 'windows':
    zmq = cdll.LoadLibrary(pkg_dir + "/ZMQ/deps/usr/lib/libzmq")
elif sublime.platform() == 'osx':
    zmq = cdll.LoadLibrary("libzmq")
else:
    zmq = cdll.LoadLibrary(pkg_dir + "/ZMQ/deps/usr/lib/libzmq.so.3.0.0")

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
            #what's the return for zmq_msg_recv? is there where we're blocking?
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