import numpy as np
from compiler.chipSetting import CHIPSETTING
from command.singleCmdInfo import *
class SIMULATOR:
    din_ram = None
    dout_ram = None
    ins_ram = None
    reg = None

    pc = None
    ins_num = None
    din_num = None
    dout_num = None

    def __init__(self):
        """
            Functions:
                初始化相关ram空间和reg空间
        """
        self.reset()

    
    def reset(self):
        self.din_ram = [0]*CHIPSETTING.din_ram_length
        self.dout_ram = [0]*CHIPSETTING.dout_ram_length
        self.ins_ram = [0]*CHIPSETTING.ins_ram_length
        self.reg = [0]*CHIPSETTING.REG_NUM

        self.pc = 0
        self.ins_num = 0
        self.din_num = 0
        self.dout_num = 0

    def load_bit_cmd(self,cmd:bytes):
        """
        Args:
            cmd: 要执行的指令字节码
        """
        cmd_mode = int(cmd[2:3].hex(),16)
        data_addr = int(cmd[3:5].hex(),16)
        data_len = int(cmd[5:7].hex(),16)

        pos = 7
        if cmd_mode == 4:                           # 4表示ins_ram
            data_size = int(CHIPSETTING.ins_ram_size/8)
            for i in range(data_len):
                self.ins_ram[data_addr+i]=int(cmd[pos:pos+data_size].hex(),16)
                pos = pos+data_size
            self.ins_num = data_addr+data_len

        elif cmd_mode == 5:                         # 5表示din_ram
            data_size = int(CHIPSETTING.din_ram_size/8)
            for i in range(data_len):
                self.din_ram[data_addr+i]=int(cmd[pos:pos+data_size].hex(),16)
                pos = pos+data_size
            self.din_num = data_addr+data_len

    def roll_back(self,num:int = -1):
        self.pc = self.pc-num

    def execut_one(self,cmdType="PL"):
        if self.pc>=self.ins_num:
            print("指令已全部执行。")
            self.pc = 0
            return
        cmd_bytes = self.ins_ram[self.pc]
        cmd_addr = (cmd_bytes>>24)&0xFF
        reg2 = (cmd_bytes>>16)&0xFF
        reg1 = (cmd_bytes>>8)&0xFF
        reg0 = cmd_bytes&0xFF
        if cmdType=="PL":
            record = -1
            cmd = PL_ADDR_TO_CMD[cmd_addr] 
            print(f"执行指令:{hex(self.ins_ram[self.pc])}",cmd["command_name"])
            if cmd == PL_ADDI:
                self.reg[reg1] = self.reg[reg0]+reg2
                record = reg1
            elif cmd == PL_LOAD_DIN_RAM:
                self.reg[reg1] = self.din_ram[self.reg[reg0]]
                record = reg1
            elif cmd == PL_ADD:
                self.reg[reg2] = self.reg[reg1]+self.reg[reg0]
                record = reg2
            elif cmd == PL_SUB:
                self.reg[reg2] = self.reg[reg1]-self.reg[reg0]
                record = reg2
            elif cmd == PL_XORI:
                self.reg[reg1] = self.reg[reg0]^reg2
                record = reg1
            elif cmd == PL_SLL:
                self.reg[reg2] = self.reg[reg1]<<self.reg[reg0]
                record = reg2
            elif cmd == PL_SRL:
                self.reg[reg2] = self.reg[reg1]>>self.reg[reg0]
                record = reg2
            else:
                pass
            if record>0:
                print(f"reg:{record}\t改变后的值:{hex(self.reg[record])}")
        else:
            cmd = PL_ADDR_TO_CMD[cmd_addr] 
            print("执行指令:",cmd["command_name"])

        self.pc = self.pc+1

    def print_reg(self):
        print("reg信息:")
        for i in range(8):
            for j in range(4):
                index = i * 4 + j
                print(f"reg:{index:<{4}}值:{hex(self.reg[index]):<{12}}", end="")  # 左对齐
            print()

    def print_din_ram(self):
        print("din_ram信息:")
        for i in range(int(self.din_num/4)):
            for j in range(4):
                index = i * 4 + j
                print(f"din:{index:<{4}}值:{hex(self.din_ram[index]):<{12}}", end="")  # 左对齐
            print()