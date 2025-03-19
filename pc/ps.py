import threading
import time
import socket
from command import CMD,CmdData,Packet

class PS():
    def __init__(self, host, port, delay=10*1e-3, debug = 0):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self.lock = threading.Lock()

        self.local_ip = "192.168.1.15"
        self.local_port = None      # 这里让他自动选择端口

        self.debug = debug

        self.historic_pkts = []

        try:
            self.socket.bind((self.local_ip, 0))
            self.socket.connect((self.host, self.port))
            self.local_ip, self.local_port = self.socket.getsockname()
            print(f"Connected to {self.host}:{self.port}\nlocal ip: {self.local_ip} local port: {self.local_port}")

            self.socket.settimeout(5)
        except Exception as e:
            print(f"Failed to connect: {e}")

    def set_time_out(self,time_out):
        self.socket.settimeout(time_out)

    def set_debug(self,debug):
        """
            debug&1>0:会输出指令字节码信息
            debug&2>0:输出接收的信息,接收信息用时
        """
        self.debug = debug

    def receive_packet(self, bytes_num):
        res = b''
        try:
            start_time = time.perf_counter()
            while len(res)< bytes_num:
                packet = self.socket.recv(bytes_num-len(res))
                res = res + packet
            if self.debug&2>0:
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                print(f"收到信息: {len(res)}","".join(f'{byte:02x}' for byte in res))
                print(f"receive_packet收到消息用时: {elapsed_time:.6f} seconds")
        except socket.timeout:
            print(f"接收超时! 期望大小{bytes_num},实际大小{len(res)}")
        except socket.error:
            print(f"Failed to recv message")
        return res
    
    def receive_packet_check(self,bytes_num,message_check):
        message = self.receive_packet(bytes_num=bytes_num)
        ans = "".join(f'{byte:02x}' for byte in message)
        assert ans == message_check,f"接收信息错误,期待接收:{message_check},实际接收:{ans}"

    def send_packets(self, pkts: Packet,message_check = "bb550000"):
        """
            将packer里面的所有上位机指令按顺序有间隔的发送下去
        """
        if self.debug >0:
            self.historic_pkts.append(pkts)
        try:
            if self.debug & 1>0:
                for i in pkts.all_bytes():print("完整字节码:",i)
                print(pkts)
            for cmd in pkts.get_bytes_list():
                self.socket.sendall(cmd)
                if message_check is not None:
                    self.receive_packet_check(bytes_num=4,message_check=message_check)
        except socket.error:
            print(f"Failed to send message:")
                    
    def close(self):
        self.socket.close()
        print("Connection closed.")




