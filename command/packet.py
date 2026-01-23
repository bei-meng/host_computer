from command.singleCmd import CMD
from command.singleCmdInfo import (
    BYTE_ORDER
)
class Packet:
    delimiter = " "

    def __init__(self):
        self.instruction_list = []
        self.header = bytes.fromhex('55aa')

    def __iter__(self):
        return self.instruction_list.__iter__()
    
    def get_bytes_list(self):
        """
            得到需要发送的所有上位机指令的字节, 
            返回一个列表, 每个元素都是一条上位机指令
        """
        res=[]
        for k in self.instruction_list:
            cmdbytes = self.header + k[0].to_bytes(1, BYTE_ORDER)
            for v in k[1]:
                if k[0]==3:
                    pass
                elif k[0]==2:
                    cmdbytes += v.get_addr()
                else:
                    cmdbytes += v.get_command()
            res.append(cmdbytes)
        return res
        
    def append_single(self, cmd:list[CMD], mode:int = 1,):
        """
            Args:
                cmd: 需要发送的单条指令(可能包含多条小指令)

            Functions:
                往packet添加单条指令的浅拷贝数据
        """
        self.instruction_list.append((mode, cmd.copy()))
    
    def append_cmdlist(self,cmdlist:list[CMD], mode:int = 1):
        """
        Args:
            cmdlist: CMD对象列表。注意：存储的是对象引用，请确保传入对象在外部不会被修改。
            mode: 模式

        Functions:
            用于往packet添加一条指令包对应一条指令情况
        """
        for cmd in cmdlist:
            self.instruction_list.append((mode,[cmd]))

    def clear(self):
        """
            清除所有命令
        """
        self.instruction_list.clear()
    
    def __str__ (self):
        max_cmd_name_len = 0
        for cmd in self.instruction_list:
            for k in cmd[1]:
                max_cmd_name_len = max(max_cmd_name_len, len(k.data["command_name"]))

        res = ""
        for cmd in self.instruction_list:
            # 获取指令的模式和名字
            res += "模式: "+str(cmd[0]) + "\n"
            cmdbytes = self.header + cmd[0].to_bytes(1, BYTE_ORDER)
            res += f"\t帧头: {'':<{max_cmd_name_len}}\t字节码: "+self.delimiter.join(f'{byte:02x}' for byte in cmdbytes) + "\n"
            for k in cmd[1]:
                if cmd[0]==3:
                    pass
                elif cmd[0]==2:
                    cmdbytes = k.get_addr()
                    res += f"\t指令: {str(k.data["command_name"]):<{max_cmd_name_len}}\t字节码: " + self.delimiter.join(f'{byte:02x}' for byte in cmdbytes) + "\n"
                else:
                    cmdbytes = k.get_command()
                    res += f"\t指令: {str(k.data["command_name"]):<{max_cmd_name_len}}\t字节码: " + self.delimiter.join(f'{byte:02x}' for byte in cmdbytes) + "\n"
        return res
    
    def all_bytes(self):
        """
            返回每条完整指令的字节码
        """
        res = []
        for cmd in self.get_bytes_list():
            res.append("".join(f'{byte:02x}' for byte in cmd))
        return res
    
    def all_bytes_line(self, show_mode:bool=False):
        max_cmd_name_len = 0
        for cmd in self.instruction_list:
            for k in cmd[1]:
                max_cmd_name_len = max(max_cmd_name_len, len(k.data["command_name"]))

        res = ""
        for cmd in self.instruction_list:
            if show_mode:
                # 获取指令的模式和名字
                res += "模式: "+str(cmd[0]) + "\n"
                cmdbytes = self.header + cmd[0].to_bytes(1, BYTE_ORDER)
                res += f"{self.delimiter}".join(f'{byte:02x}' for byte in cmdbytes) + "\n"

            for k in cmd[1]:
                if cmd[0]==3:
                    pass
                elif cmd[0]==2:
                    cmdbytes = k.get_addr()
                    res += f"{self.delimiter}".join(f'{byte:02x}' for byte in cmdbytes) + "\n"
                else:
                    cmdbytes = k.get_command()
                    res += f"{self.delimiter}".join(f'{byte:02x}' for byte in cmdbytes) + "\n"
        return res