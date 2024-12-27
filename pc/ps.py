import threading
import time
import socket
from cimCommand import CMD,CmdData,Packet

class PS():
    def __init__(self, host, port, delay=10*1e-3, debug = False):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lock = threading.Lock()

        self.local_ip = "192.168.1.15"
        self.local_port = None      # 这里让他自动选择端口

        self.enable = True
        self.debug = debug

        self.history = []

        self.delay = delay                # 延迟时间为10ms

        try:
            s = self.socket
            s.bind((self.local_ip, 0))
            s.connect((self.host, self.port))
            self.local_ip, self.local_port = s.getsockname()
            print(f"Connected to {self.host}:{self.port}\nlocal ip: {self.local_ip} local port: {self.local_port}")
            self.enable = True
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.enable = False
        time.sleep(1)

    def set_delay(self,delay):
        self.delay = delay

    def set_debug(self,debug):
        self.debug = debug

    def receive_packet(self,name=""):
        if self.enable:
            with self.lock:
                packet = ""
                try:
                    packet = self.socket.recv(1024)  # 每次最多接收 1024 字节
                    if not packet:
                        print("empty packet")
                    print(f"---Received---\n{packet}\n")
                    self.history.append(dict(
                        name = name,
                        message = packet
                    ))
                except socket.error:
                    print(f"Failed to recv message")
            return packet

    def send_packets(self, pkts: Packet):
        """
            将packer里面的所有上位机指令按顺序有间隔的发送下去
        """
        if self.enable:
            with self.lock:
                try:
                    if self.debug:
                        print(f"------------------------------ 发送指令: ------------------------------ ")
                        print(pkts)
                    for cmd in pkts.get_bytes_list():
                        self.socket.sendall(cmd)
                        time.sleep(self.delay)
                    if self.debug:
                        print(f"------------------------------ 指令发送完成！------------------------------ \n") 
                except socket.error:
                    print(f"Failed to send message:")

    def close(self):
        with self.lock:
            if self.socket:
                self.socket.close()
                print("Connection closed.")
            self.enable = False




