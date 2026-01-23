import time
import socket

class PS():
    def __init__(self, local_ip, remote_ip, remote_port, max_packet_size=65536,debug=0):
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.local_ip = local_ip
        self.local_port = None      # 这里让他自动选择端口

        self.debug = debug
        self.delay = 0

        self.historic_pkts = []

        # 分配固定缓冲区，加速
        self._buffer = bytearray(max_packet_size)
        self._buffer_view = memoryview(self._buffer)
        try:
            self.socket.bind((self.local_ip, 0))
            self.socket.connect((self.remote_ip, self.remote_port))
            self.local_ip, self.local_port = self.socket.getsockname()
            self.socket.settimeout(1)
            print(f"Connected to {self.remote_ip}:{self.remote_port}\nlocal ip: {self.local_ip} local port: {self.local_port}")


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
        total_received = 0
        try:
            start_time = time.perf_counter()
            while total_received < bytes_num:
                bytes_received = self.socket.recv_into(self._buffer_view[total_received:], bytes_num - total_received)
                if bytes_received == 0:
                    raise ConnectionError("Socket connection closed")
                total_received += bytes_received
            end_time = time.perf_counter()
            if self.debug & 0x02 > 0:
                elapsed_time = end_time - start_time
                print(f"用时：{elapsed_time:.6f}秒，大小: {total_received}, 数据：{self._buffer[:total_received].hex()}")
        except socket.timeout:
            print(f"接收超时! 期望大小：{bytes_num},实际大小：{total_received},数据：{self._buffer[:total_received].hex()}")
        except socket.error:
            print(f"接收信息错误!")

        return self._buffer[:total_received]
    
    def receive_packet_check(self,bytes_num,message_check):
        message = self.receive_packet(bytes_num=bytes_num).hex()
        if message != message_check:
            print(f"接收信息错误,期待接收:{message_check},实际接收:{message}")
            return False
        return True

    def send_packets(self, pkts,message_check = "bb550000"):
        """
            将packer里面的所有上位机指令按顺序有间隔的发送下去
        """
        if self.debug & 0x01 > 0:
            for i in pkts.all_bytes():print("完整字节码:",i)
            print(pkts)
        if self.debug >0:
            self.historic_pkts.append(pkts)
        try:
            cmd_list = pkts.get_bytes_list()
            for cmd in cmd_list:
                self.socket.sendall(cmd)
                if self.delay>1e-3:
                    time.sleep(self.delay)
                if message_check is not None:
                    self.receive_packet_check(bytes_num=4,message_check=message_check)
        except socket.error:
            print(f"Failed to send message:")
                    
    def close(self):
        self.socket.close()
        print(f"Connection closed:\nremote ip: {self.remote_ip}:{self.remote_port}\nlocal ip: {self.local_ip} local port: {self.local_port}")

    def __del__(self):
        self.close()




