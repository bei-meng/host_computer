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

            self.socket.settimeout(5)
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.enable = False
        # time.sleep(1)

    def set_delay(self,delay):
        self.delay = delay

    def set_debug(self,debug):
        self.debug = debug

    def receive_packet(self, bytes_num):
        if self.enable:
            packet = ""
            with self.lock:
                try:
                    packet = self.socket.recv(bytes_num)
                    res = "".join(f'{byte:02x}' for byte in packet)
                    print(res)
                    if not packet:
                        print("empty packet")
                    if self.debug:
                        print(f"Received: {packet}\n")

                except socket.timeout:
                    print("接收超时!")
                except socket.error:
                    print(f"Failed to recv message")
            return packet

    def send_packets(self, pkts: Packet,delay = None,recv = True):
        """
            将packer里面的所有上位机指令按顺序有间隔的发送下去
        """
        res = ""
        if self.enable or self.debug:
            with self.lock:
                try:
                    # pass
                    if self.debug:
                        print(pkts)
                    for cmd in pkts.get_bytes_list():
                        self.socket.sendall(cmd)
                        if recv:
                            packet = self.socket.recv(1024)
                            res = "".join(f'{byte:02x}' for byte in packet)
                            print(res)
                            if (len(packet) == 4 and res == "bb550000"):
                                pass
                            elif (len(packet) == 4 and res == "cc550000"):
                                pass
                            # else:
                            #     print("发送指令:返回信息错误!",packet)
                except socket.timeout:
                    print("发送/接收超时!")
                except socket.error:
                    print(f"Failed to send message:")
        return res

    def close(self):
        with self.lock:
            if self.socket:
                self.socket.close()
                print("Connection closed.")
            self.enable = False




