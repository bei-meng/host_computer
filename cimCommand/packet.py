from cimCommand.singleCmd import CMD
from cimCommand.singleCmdInfo import (
    BYTE_ORDER
)
class Packet:
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
            cmdbytes = self.header + k["mode"].to_bytes(1, BYTE_ORDER)
            for v in k["cmd"]:
                if k["mode"]==3:
                    pass
                elif k["mode"]==2:
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
        self.instruction_list.append(dict(
            mode = mode,
            cmd = cmd.copy(),
        ))
    
    def append_cmdlist(self,cmdlist:list[CMD], mode:int = 1):
        """
            cmd列表里面都是相同mode模式的单条指令
        """
        for cmd in cmdlist:
            self.instruction_list.append(dict(
                mode = mode,
                cmd = [cmd],
            ))

    def clear(self):
        """
            清除所有命令
        """
        self.instruction_list.clear()
    
    def __str__ (self):
        max_cmd_name_len = 0
        for cmd in self.instruction_list:
            for k in cmd["cmd"]:
                max_cmd_name_len = max(max_cmd_name_len, len(k.command_name))

        # res =  " ".join(f'{byte:02x}' for byte in self.header)
        res = ""
        for cmd in self.instruction_list:
            # 获取指令的模式和名字
            res += "模式: "+str(cmd["mode"]) + "\n"
            cmdbytes = self.header + cmd["mode"].to_bytes(1, BYTE_ORDER)
            res += f"\t帧头: {'':<{max_cmd_name_len}}\t字节码: "+" ".join(f'{byte:02x}' for byte in cmdbytes) + "\n"
            for k in cmd["cmd"]:
                if cmd["mode"]==3:
                    pass
                elif cmd["mode"]==2:
                    cmdbytes = k.get_addr()
                    res += f"\t指令: {str(k.command_name):<{max_cmd_name_len}}\t字节码: " + " ".join(f'{byte:02x}' for byte in cmdbytes) + "\n"
                else:
                    cmdbytes = k.get_command()
                    res += f"\t指令: {str(k.command_name):<{max_cmd_name_len}}\t字节码: " + " ".join(f'{byte:02x}' for byte in cmdbytes) + "\n"
        return res