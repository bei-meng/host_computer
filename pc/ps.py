import threading
import time
import socket
from cimCommand import CMD,CmdData,Packet

class PS():
    def __init__(self, host, port, delay=10*1e-3, debug = 0):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lock = threading.Lock()

        self.local_ip = "192.168.1.15"
        self.local_port = None      # 这里让他自动选择端口

        self.enable = True
        self.debug = debug

        try:
            s = self.socket
            s.bind((self.local_ip, 0))
            s.connect((self.host, self.port))
            self.local_ip, self.local_port = s.getsockname()
            print(f"Connected to {self.host}:{self.port}\nlocal ip: {self.local_ip} local port: {self.local_port}")
            self.enable = True

            self.socket.settimeout(10)
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.enable = False

    def set_debug(self,debug):
        self.debug = debug

    def receive_packet(self, bytes_num):
        if self.enable:
            res = b''
            with self.lock:
                try:
                    start_time = time.perf_counter()
                    while len(res)< bytes_num:
                        packet = self.socket.recv(min(bytes_num-len(res),1024))
                        res = res + packet

                        if self.debug&2>0:
                            print(f"收到信息: {len(res)}","".join(f'{byte:02x}' for byte in res))
                    end_time = time.perf_counter()
                    elapsed_time = end_time - start_time
                    if self.debug&2>0:
                        print(f"receive_packet收到消息用时: {elapsed_time:.6f} seconds")
                except socket.timeout:
                    print("receive_packet:接收超时!")
                except socket.error:
                    print(f"Failed to recv message")
            return res

    def send_packets(self, pkts: Packet,delay = None,recv = True):
        """
            将packer里面的所有上位机指令按顺序有间隔的发送下去
        """
        if self.enable or self.debug>0:
            with self.lock:
                try:
                    if self.debug & 1>0:
                        print(pkts)
                            
                    for cmd in pkts.get_bytes_list():
                        if self.debug & 1>0:
                            print("指令完整字节码: ","".join(f'{byte:02x}' for byte in cmd))

                        self.socket.sendall(cmd)
                        # ------------------------------------------------------------------------
                        if recv:
                            res = b''
                            while len(res)< 4:
                                start_time = time.perf_counter()
                                packet = self.socket.recv(4-len(res))
                                end_time = time.perf_counter()
                                elapsed_time = end_time - start_time
                                res = res + packet
                                if self.debug&2>0:
                                    print(f"send_packets收到55bb或55cc用时: {elapsed_time:.6f} seconds")
                                    print(f"收到信息: {len(packet)}","".join(f'{byte:02x}' for byte in packet))

                            tmp = "".join(f'{byte:02x}' for byte in res)
                            if not ((len(res) == 4 and tmp == "bb550000") or (len(res) == 4 and tmp == "cc550000")):
                                print("send_packets: 返回信息错误!",res)
                        # ------------------------------------------------------------------------
                except socket.timeout:
                    print("send_packets:接收超时!")
                except socket.error:
                    print(f"Failed to send message:")
                    
    def close(self):
        with self.lock:
            if self.socket:
                self.socket.close()
                print("Connection closed.")
            self.enable = False




