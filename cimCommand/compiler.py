from cimCommand.singleCmd import CMD
from cimCommand.singleCmdData import CmdData

from cimCommand.singleCmdInfo import *
from typing import List, Union
class COMPILER:
    ins_data = None                                                 # 存放CMD
    ass_ins = None                                                  # 汇编指令(name,参数2, 参数1, 参数0)
    reg_flag = None                                                 # 寄存器使用标志, 使用为1,未使用为0
    need_replace_label = None                                       # 需要进行label提供的指令(ins_pos,label_name,start,length)
    need_replace_const = None                                       # 需要替换的常量符号(ins_pos,label_name,start,length)
    labels = None                                                   # 标签
    variable = None                                                 # 变量对应的reg号
    const_variable = None                                                    # 常量,用于立即数
    ins_pos = None                                                  # 最后一条指令的位置
    offset = 0                                                      # 当前指令的偏移

    def __init__(self):
        self.ins_data = []                                           # 存放CMD
        self.ass_ins = []                                            # 汇编指令(name,参数2, 参数1, 参数0)
        self.reg_flag = [0]*INS2_INFO.REG_NUM                        # 寄存器使用标志, 使用为1,未使用为0
        self.need_replace_label = []                                 # 需要进行label提供的指令(ins_pos,label_name,start,length)
        self.need_replace_const = []
        self.labels = {}                                             # 标签
        self.variable = {}                                           # 变量对应的reg号
        self.const_variable = {}
        self.ins_pos = 0                                             # 最后一条指令的位置
        self.get_reg_variable("zero")                                # 寄存器默认初始化就为0,不要改0寄存器的值
        self.offset = 0


    def __str__ (self):
        res = ""
        for k,v in self.const_variable.items():
            res += f"const: {k:<{30}}: 常量值: {v}\n"
        
        res += "\n"
        
        for k,v in self.variable.items():
            res += f"变量名: {k:<{30}}: 寄存器编号: {v}\n"
        
        res += "\n"
        for k,v in self.labels.items():
            res += f"标签: {k:<{30}}: 指令地址: {v}\n"

        res += "\n"
        # res += "start:\t0\n"
        num = 0
        for ins in self.ass_ins:
            if ins[0] == 1:
                if num!=0:
                    res += "\n"
                res += str(num)+ "\t" + ins[1]+":"
            elif ins[0]==0:
                res += str(num)
                num += 1
                res += "\t\t" + ins[1][3:] +"\t"
                if len(ins)>2:
                    for i in range(2,len(ins)):
                        if i!=2: res += ", "
                        # print(ins[1],ins)
                        res += ins[i]
            elif ins[0]==2:
                res += str(num)
                res += "\t\t" + ins[1][3:] +"\t"
                if len(ins)>2:
                    for i in range(2,len(ins)):
                        if i!=2: res += ", "
                        # print(ins[1],ins)
                        res += ins[i]

            res += "\n"
        return res
    
    def add_offset(self,offset:int):
        """
            修改汇编代码里面的label的偏移
        """
        need_offset = offset - self.offset
        for label_name,ins_pos in self.labels.items():
            self.labels[label_name] = ins_pos + need_offset
        self.offset = offset

    
    def get_assembler_ins(self):
        """
            返回对应的汇编指令
        """
        res = ""
        num = 0
        for ins in self.ass_ins:
            if ins[0]:
                if num!=0:
                    res += "\n"
                res += ins[1]+":" + "\t"
            else:
                num += 1
                res += "\t" + ins[1][3:] +"\t"
                if len(ins)>2:
                    for i in range(2,len(ins)):
                        if i!=2: res += ", "
                        # print(ins[1],ins)
                        res += ins[i]
            res += "\n"
        return res
                
    def get_ins_data(self)->list[CMD]:
        """
            获取ins_data
            返回ins_data的副本
        """
        for ins_pos,label,start,length in self.need_replace_label:
            new_data = self.labels.get(label,None)
            if new_data is not None:
                self.ins_data[ins_pos].command_data.replace_bit(start,length,new_data)
            else:
                raise Exception(f"标签{label}未定义!")
            
        for ins_pos,label,start,length in self.need_replace_const:
            new_data = self.get_const_variable(label)
            if new_data is not None:
                self.ins_data[ins_pos].command_data.replace_bit(start,length,new_data)
            else:
                raise Exception(f"常量{label}未定义!")
            
        return self.ins_data.copy()
    
    def load_assembler_ins(self,filename:str,encoding:str = 'utf-8'):
        """
            从filename中加载汇编代码
        """
        with open(filename, 'r', encoding=encoding) as file:
            for line in file:
                # 删除注释,同时删除首尾空格和\t符号
                line = line.split('#')[0].strip()
                
                if line == '':
                    continue
                if line[-1] == ':':
                    self.add_label(line[:-1])
                else:
                    pos = line.find(' ')
                    if pos>0:
                        cmd_name = line[:pos] or line
                        cmd_data = line[pos:].replace(' ','').split(',')
                    else:
                        cmd_name = line
                        cmd_data = []
                    getattr(self, cmd_name)(*cmd_data)

    #------------------------------------------------------------------------------------------
    # *********************************** 常量相关函数 ***********************************
    #------------------------------------------------------------------------------------------
    def add_const_variable(self,variable_name:str,value:int):
        self.const_variable[variable_name] = value

    def get_const_variable(self,variable_name:str)->Union[int|None]:
        """
            获取常量变量的值
        """
        return self.const_variable.get(variable_name,None)
    
    def const_str_to_int(self,imm:Union[int|str]):
        isConst = False
        if type(imm)==str:
            imm_c = self.get_const_variable(imm)
            if imm_c is None:
                imm_c = int(imm,0)
            else:
                isConst = True
        elif type(imm)==int:
            imm_c = imm
        else:
            raise Exception(f"立即数{imm}类型错误!")
        return imm_c,isConst
    
    #------------------------------------------------------------------------------------------
    # *********************************** 变量相关函数 ***********************************
    #------------------------------------------------------------------------------------------
    def get_reg_variable(self,variable_name,init=True):
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
    
    def del_reg_variable(self,variable_name):
        """
            删除变量所用寄存器空间
        """
        reg_num = self.variable.get(variable_name,None)
        if reg_num is not None:
            self.reg_flag[reg_num] = 0
            del self.variable[variable_name]
        else:
            raise Exception(f"变量{variable_name}未定义!")
    
    #------------------------------------------------------------------------------------------
    # *********************************** 编译汇编文件的函数 ***********************************
    #------------------------------------------------------------------------------------------
    def add_label(self,label_name:str):
        """
            添加一个label
        """
        self.labels[label_name] = self.ins_pos
        self.ass_ins.append((1, label_name))

    def consti(self,variable_name:str,value:Union[int|str]):
        """
            Args:
                variable_name: 变量名
                value: 变量值
            新增非寄存器的变量, 用于编译转字节码
        """
        if type(value)==str:
            value = int(value,0)
        self.add_const_variable(variable_name,value)
        self.ass_ins.append((2, "pl_consti", variable_name, str(value)))

    def addi(self,reg1:str,reg0:str,imm:Union[int|str]):
        """
            reg1 = reg0 + imm
        """
        imm_c,isConst = self.const_str_to_int(imm)
        reg_1 = self.get_reg_variable(reg1)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_ADDI,command_data=CmdData(imm_c<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0, str(imm)))
        self.ins_pos += 1

        if isConst:
            self.need_replace_const.append((self.ins_pos-1, imm, 16, 8))

    def add(self,reg2:str,reg1:str,reg0:str):
        """
            reg2 = reg1 + reg0
        """
        reg_2 = self.get_reg_variable(reg2)
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_ADD,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def sub(self,reg2:str,reg1:str,reg0:str):
        """
            reg2 = reg1 - reg0
        """
        reg_2 = self.get_reg_variable(reg2)
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_SUB,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def xori(self,reg1:str,reg0:str,imm:Union[int|str]):
        """
            reg1 = reg0 ^ imm
        """
        imm_c,flag = self.const_str_to_int(imm)
        reg_1 = self.get_reg_variable(reg1)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_XORI,command_data=CmdData(imm_c<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0, str(imm)))
        self.ins_pos += 1

        if flag:
            self.need_replace_const.append((self.ins_pos-1, imm, 16, 8))

    def sll(self,reg2:str,reg1:str,reg0:str):
        """
            reg2 = reg1 << reg0
        """
        reg_2 = self.get_reg_variable(reg2)
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_SLL,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def srl(self,reg2:str,reg1:str,reg0:str):
        """
            reg2 = reg1 >> reg0
        """
        reg_2 = self.get_reg_variable(reg2)
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_SRL,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def bge(self,reg1:str,reg0:str,label:str):
        """
            bge reg1, reg0, label
            如果reg1 >= reg0, 跳转到label
        """
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_BGE,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, INS2_INFO.BGE_INS_ADDR_START_POS, INS2_INFO.INS_RAM_ADDR_LENGTH))

    def jump(self,label:str):
        """
            pc跳转至label指令处
        """
        ins = CMD(PL_JUMP,command_data=CmdData(0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, INS2_INFO.INS_RAM_ADDR_LENGTH))

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
        reg_0 = self.get_reg_variable(reg0,init=False)
        reg_1 = self.get_reg_variable(reg1)
        ins = CMD(PL_LOAD_DIN_RAM,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0))
        self.ins_pos += 1

    def set_row_bank(self,reg1:str,reg0:str):
        """
            Args:
                reg1: row_bank_mask
                reg0: row_index_mask
        """
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
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
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_SET_COL_BANK,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0))
        self.ins_pos += 1

    def read_row_tia(self,reg2:str,reg1:str,reg0:str):
        """
            Args:
                reg2: tia[0,15]
                reg1: dout_ram_addr
                reg0: dout_ram块(0,1)
        """
        reg_2 = self.get_reg_variable(reg2,init=False)
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_READ_ROW_PULSE_TIA,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def read_col_tia(self,reg2:str,reg1:str,reg0:str):
        """
            Args:
                reg2: tia[0,15]
                reg1: dout_ram_addr
                reg0: dout_ram块(0,1)
        """
        reg_2 = self.get_reg_variable(reg2,init=False)
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_READ_COL_PULSE_TIA,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def return_dout(self,reg2:str,reg1:str,reg0:str):
        """
            Args:
                reg2: 数据长度
                reg1: dout_ram_addr
                reg0: dout_ram块(0,1)
        """
        reg_2 = self.get_reg_variable(reg2,init=False)
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_RETURN_DOUT,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2, reg1, reg0))
        self.ins_pos += 1

    def set_daci(self,imm1:Union[int|str],imm0:Union[int|str]):
        """
            Args:
                imm1: DAC的通道[0,11]
                imm0: 16bit的电压码值
        """
        imm1_c,isConst1 = self.const_str_to_int(imm1)
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_DAC_V,command_data=CmdData(imm1_c <<16 | imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm1, imm0))
        self.ins_pos += 1

        if isConst1:
            self.need_replace_const.append((self.ins_pos-1, imm1, 16, 8))
        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def set_row_banki(self,imm1:Union[int|str],imm0:Union[int|str]):
        """
            Args:
                imm1: 为row_bank_mask(8bit)
                imm0: 为din_ram的地址,din_ram[imm0]为row_index_mask
        """
        imm1_c,isConst1 = self.const_str_to_int(imm1)
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_ROW_BANK,command_data=CmdData(imm1_c <<16 | imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm1, imm0))
        self.ins_pos += 1

        if isConst1:
            self.need_replace_const.append((self.ins_pos-1, imm1, 16, 8))
        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def set_col_banki(self,imm1:Union[int|str],imm0:Union[int|str]):
        """
            Args:
                imm1: 为col_bank_mask(8bit)
                imm0: 为din_ram的地址,din_ram[imm0]为col_index_mask,din_ram每个数据单元大小32bit
        """
        imm1_c,isConst1 = self.const_str_to_int(imm1)
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_COL_BANK,command_data=CmdData(imm1_c <<16 | imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm1, imm0))
        self.ins_pos += 1

        if isConst1:
            self.need_replace_const.append((self.ins_pos-1, imm1, 16, 8))
        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def read_rowi(self,imm0:Union[int|str]):
        """
            Args:
                imm0: 为dout_ram的地址,读出的结果存在dout_ram[imm0](每个数据单元大小256bit)
            从行读
        """
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_READ_ROW_PULSE,command_data=CmdData(imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm0))
        self.ins_pos += 1

        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def read_coli(self,imm0:Union[int|str]):
        """
            Args:
                imm0: 为dout_ram的地址,读出的结果存在dout_ram[imm0](每个数据单元大小256bit)
            从列读
        """
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_READ_COL_PULSE,command_data=CmdData(imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm0))
        self.ins_pos += 1

        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def write_row(self):
        """
            从行写
        """
        ins = CMD(PL_WRITE_ROW_PULSE)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def write_col(self):
        """
            从列写
        """
        ins = CMD(PL_WRITE_COL_PULSE)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def cim_reset(self):
        """
            清零latch
        """
        ins = CMD(PL_CIM_RESET)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1