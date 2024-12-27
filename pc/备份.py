import socket
import threading

# 获取本地主机名,服务器将监听主机名对应的所有网络接口上的指定端口
# 如果主机名解析为多个IP地址，那么服务器将在所有这些地址上监听
host = socket.gethostname() 
# 这是一个特殊的主机名，始终指向当前主机的回环地址（127.0.0.1）。
# 这意味着服务器将只监听回环接口上的指定端口，只接受来自本机的连接。
host = "localhost"
port = 12345    

print(host,port)

# 定义一个锁，和退出标志用于保证线程的退出
lock = threading.Lock()
exit_flag = False


def handle_message(message):
    return message+"getmessage"

def handle_client(client_socket, addr):
    try:
        global exit_flag
        print(f"线程：客户端连接处理：{addr}")
        # 设置为非阻塞模式
        client_socket.setblocking(0)
        while True:
            #------------------------------------控制共享资源的访问
            lock.acquire()
            if exit_flag:
                lock.release()
                break
            lock.release()
            #------------------------------------控制共享资源的访问
            getmessage=None
            #------------------------------------非阻塞式的接收上传的数据
            try:
                # 尝试接收数据
                data = client_socket.recv(1024)
                if not data:
                    print("连接中断！")
                    break
                # 接收到信息
                getmessage=data.decode("UTF-8")
            except socket.error as e:
                # 没有数据
                pass
            #------------------------------------非阻塞式的接收上传的数据
            sendmessage=handle_message(getmessage)
            if sendmessage is None:
                continue
            #------------------------------------非阻塞式的发送数据
            try:
                if sendmessage == 'exit':
                    client_socket.send(sendmessage.encode("UTF-8"))
                    client_socket.close()
                    break
                client_socket.send(sendmessage.encode("UTF-8"))
            except socket.error as e:
                pass
            #------------------------------------非阻塞式的发送数据
    finally:
        client_socket.close()


# 使用IPv4地址+TCP协议
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # 绑定主机和端口
    s.bind((host, port))
    # 等待客户端连接，表示接受的连接数量
    s.listen(5)
    print(f"服务端已开始监听，正在等待客户端连接...")

    try:
        while True:
            # accept为阻塞式的
            client_sock, address = s.accept()
            print(f"接收到了客户端的连接，客户端的地址：{address}")
            # 创建线程处理对应客户端的连接
            thread = threading.Thread(target=handle_client, args=(client_sock, address))
            thread.start()
    finally:
        # 保证子线程的正确退出
        lock.acquire()
        exit_flag = True
        lock.release()

'''
# 连接的例子
import socket
# 创建socket对象
socket_client = socket.socket()
# 连接到服务器
socket_client.connect((host, port))
'''
