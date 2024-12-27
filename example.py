from cmd.commands import *
from CIMcommand.packetData import *
from pc.ps import *

ps = PS("192.168.1.10", 7)

cmd_list = [DAC_IN(0, 10), FAST_COMMAND_1(1)]    # 命令列表
packet = Packet(0, cmd_list)                            # 打包

try:
    ps.send_packet(bytes(packet))                              # 发送
    packet = ps.receive_packet()                               # 接收
    print(packet)                                               # 打印
except socket.error as e:
    print(f"出错: {e}")
finally:
    ps.close()
    print(f"socket closed")