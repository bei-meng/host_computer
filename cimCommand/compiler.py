from cimCommand.singleCmd import CMD
from cimCommand.singleCmdData import CmdData

from cimCommand.singleCmdInfo import *
class COMPILER:
    ins_data = []                                           # 存放CMD
    ass_ins = []                                            # 汇编指令(name,参数2, 参数1, 参数0)
    reg_flag = [0]*INS2_INFO.REG_NUM                        # 寄存器使用标志, 使用为1,未使用为0
    need_replace_label = []                                 # 需要进行label提供的指令(ins_pos,label_name,start,length)
    labels = {}                                             # 标签
    variable = {}                                           # 变量对应的reg号
    ins_pos = 0                                             # 最后一条指令的位置

    def __init__(self):
        self.ins_data = []                                           # 存放CMD
        self.ass_ins = []                                            # 汇编指令(name,参数2, 参数1, 参数0)
        self.reg_flag = [0]*INS2_INFO.REG_NUM                        # 寄存器使用标志, 使用为1,未使用为0
        self.need_replace_label = []                                 # 需要进行label提供的指令(ins_pos,label_name,start,length)
        self.labels = {}                                             # 标签
        self.variable = {}                                           # 变量对应的reg号
        self.ins_pos = 0                                             # 最后一条指令的位置
        self.get_variable("zero")


    def __str__ (self):
        res = ""
        for k,v in self.variable.items():
            res += f"变量名: {k:<{30}}: 寄存器编号: {v}\n"
        
        res += "\n"
        num = 0
        for ins in self.ass_ins:
            if ins[0]:
                res += ins[1]+":" + "\t" + str(num)
            else:
                res += str(num)
                num += 1
                res += "\t" + ins[1][3:] +"\t"
                if len(ins)>2:
                    for i in range(2,len(ins)):
                        if i!=2: res += ", "
                        # print(ins[1],ins)
                        res += ins[i]
            res += "\n"
        return res
    
    def get_ins_data(self):
        """
            获取ins_data
        """
        for ins_pos,label,start,length in self.need_replace_label:
            new_data = self.labels.get(label,None)
            if new_data is not None:
                self.ins_data[ins_pos].command_data.replace_bit(start,length,new_data)
            else:
                raise Exception(f"标签{label}未定义!")
        return self.ins_data
    
    def get_variable(self,variable_name,init=True):
        """
            Args:
                variable_name: 变量名
                init: True表示未定义就需要定义
            获取variable_name名字对应的reg号,
            如果已经定义过, 就直接返回对应的reg号,
            如果未定义, 就分配一个reg给这个变量
        """
        reg_num = self.variable.get(variable_name,None)
        if reg_num is None:
            if init:
                flag = False
                for i, v in enumerate(self.reg_flag):
                    if v == 0:
                        flag = True
                        reg_num = i
                        self.variable[variable_name] = i
                        self.reg_flag[i] = 1
                        break
                if not flag: raise Exception("寄存器不够!")
            else:
                raise Exception(f"变量{variable_name}未定义!")
        return reg_num
    
    def del_variable(self,variable_name):
        """
            删除变量所用寄存器空间
        """
        reg_num = self.variable.get(variable_name,None)
        if reg_num is not None:
            self.reg_flag[reg_num] = 0
            del self.variable[variable_name]
        else:
            raise Exception(f"变量{variable_name}未定义!")
    
    def add_label(self,label_name:str):
        """
            添加一个label
        """
        self.labels[label_name] = self.ins_pos
        self.ass_ins.append((1, label_name))

    def bge(self,reg1:str,reg0:str,label:str):
        """
            bge reg1, reg0, label
            如果reg1 >= reg0, 跳转到label
        """
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_BGE,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, INS2_INFO.BGE_INS_ADDR_START_POS, INS2_INFO.INS_RAM_ADDR_LENGTH))

    def addi(self,reg1:str,reg0:str,imm:int):
        """
            reg1 = reg0 + imm
        """
        reg_1 = self.get_variable(reg1)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_ADDI,command_data=CmdData(imm<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0, str(imm)))
        self.ins_pos += 1

    def exit(self):
        """
            exit
        """
        ins = CMD(PL_EXIT)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def load_din_ram(self,reg1:str,reg0:str):
        """
            reg1 = din_ram[reg0]
        """
        reg_0 = self.get_variable(reg0,init=False)
        reg_1 = self.get_variable(reg1)
        ins = CMD(PL_LOAD_DIN_RAM,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0))
        self.ins_pos += 1

    def add(self,reg2:str,reg1:str,reg0:str):
        """
            reg2 = reg1 + reg0
        """
        reg_2 = self.get_variable(reg2)
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_ADD,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def sub(self,reg2:str,reg1:str,reg0:str):
        """
            reg2 = reg1 - reg0
        """
        reg_2 = self.get_variable(reg2)
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_SUB,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def xori(self,reg1:str,reg0:str,imm:int):
        """
            reg1 = reg0 ^ imm
        """
        reg_1 = self.get_variable(reg1)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_XORI,command_data=CmdData(imm<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0, str(imm)))
        self.ins_pos += 1

    def sll(self,reg2:str,reg1:str,reg0:str):
        """
            reg2 = reg1 << reg0
        """
        reg_2 = self.get_variable(reg2)
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_SLL,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def srl(self,reg2:str,reg1:str,reg0:str):
        """
            reg2 = reg1 >> reg0
        """
        reg_2 = self.get_variable(reg2)
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_SRL,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def set_row_bank(self,reg1:str,reg0:str):
        """
            Args:
                reg1: row_bank_mask
                reg0: row_index_mask
        """
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_SET_ROW_BANK,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0))
        self.ins_pos += 1

    def set_col_bank(self,reg1:str,reg0:str):
        """
            Args:
                reg1: col_bank_mask
                reg0: col_index_mask
        """
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_SET_COL_BANK,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0))
        self.ins_pos += 1

    def row_read(self,reg2:str,reg1:str,reg0:str):
        """
            Args:
                reg2: tia[0,15]
                reg1: dout_ram_addr
                reg0: dout_ram块(0,1)
        """
        reg_2 = self.get_variable(reg2,init=False)
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_READ_ROW_PULSE_TIA,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def col_read(self,reg2:str,reg1:str,reg0:str):
        """
            Args:
                reg2: tia[0,15]
                reg1: dout_ram_addr
                reg0: dout_ram块(0,1)
        """
        reg_2 = self.get_variable(reg2,init=False)
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_READ_COL_PULSE_TIA,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def dout_return(self,reg2:str,reg1:str,reg0:str):
        """
            Args:
                reg2: 数据长度
                reg1: dout_ram_addr
                reg0: dout_ram块(0,1)
        """
        reg_2 = self.get_variable(reg2,init=False)
        reg_1 = self.get_variable(reg1,init=False)
        reg_0 = self.get_variable(reg0,init=False)
        ins = CMD(PL_RETURN_OUT,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1


    def jump(self,label:str):
        ins = CMD(PL_JUMP)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, INS2_INFO.INS_RAM_ADDR_LENGTH))