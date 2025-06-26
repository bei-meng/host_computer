from command.singleCmd import CMD
from command.singleCmdData import CmdData

from command.singleCmdInfo import *
from typing import List, Union
from compiler.chipSetting import CHIPSETTING

class COMPILER:
    ins_data = None                                                 # 存放CMD
    ass_ins = None                                                  # 汇编指令(name,参数2, 参数1, 参数0)
    reg_flag = None                                                 # 寄存器使用标志, 使用为1,未使用为0
    need_replace_label = None                                       # 需要进行label提供的指令(ins_pos,label_name,start,length)
    need_replace_const = None                                       # 需要替换的常量符号(ins_pos,label_name,start,length)
    labels = None                                                   # 标签
    variable = None                                                 # 变量对应的reg号
    const_variable = None                                           # 常量,用于立即数
    ins_pos = None                                                  # 最后一条指令的位置
    offset = 0                                                      # 当前指令的偏移


    check_reg = False

    def __init__(self):
        self.ins_data = []                                          # 存放CMD
        self.ass_ins = []                                           # 汇编指令(name,参数2, 参数1, 参数0)
        self.reg_flag = [0]*CHIPSETTING.REG_NUM                     # 寄存器使用标志, 使用为1,未使用为0
        self.need_replace_label = []                                # 需要进行label提供的指令(ins_pos,label_name,start,length)
        self.need_replace_const = []
        self.need_replace_return = []                               # 替换返回的地址
        self.labels = {}                                            # 标签
        self.variable = {}                                          # 变量对应的reg号
        self.const_variable = {}
        self.return_label = {}                                      # 返回位置的标签
        self.ins_pos = 0                                            # 最后一条指令的位置
        # self.get_reg_variable("zero")                               # 寄存器默认初始化就为0,不要改0寄存器的值
        self.offset = 0                                             # 指令整体偏移量

        # 闭包变量 i 的延迟绑定

        apu_calc = ["apu_calc_relu","apu_calc_sigmoid","apu_calc_tanh"]
        for i,name in enumerate(apu_calc):
            setattr(self, name.lower(), lambda i=str(i): self.apu_calc(i))

        element_wise = [
            "set_elewise_APU_2_mul_A",                              # 0
            "set_elewise_actv_2_mul_A",                             # 1
            "set_elewise_acc_2_mul_A",                              # 2
            "set_elewise_APU_2__mul_B",                             # 3
            "set_elewise_actv_2_mul_B",                             # 4
            "set_elewise_reg_2_mul_B",                              # 5
            "set_elewise_reg_2_shifter0",                           # 6
            "set_elewise_mul_shifter0_calc",                        # 7
            "set_elewise_mul_2_adder_A",                            # 8
            "set_elewise_acc_2_adder_A",                            # 9
            "set_elewise_mul_2_adder_B",                            # A
            "set_elewise_actv_2_adder_B",                           # B
            "set_elewise_adder_shifter1_calc",                      # C
            "set_elewise_adder_clear",                              # D
            "set_elewise_fast",                                     # E
            "set_elewise_reg_2_shifter1",                           # F
            ]
        for i,name in enumerate(element_wise):
            if i==5 or i==6 or i==15:
                setattr(self, name.lower(), lambda reg2,i=str(i): self.element_wise(reg2,"0",i))
            else:
                setattr(self, name.lower(), lambda i=str(i): self.element_wise(None,"0",i))

        store_actv_ram = [
            "store_actv_ram_shifter0",
            "store_actv_ram_shifter1",
            "store_actv_ram_apu"
        ]
        for i,name in enumerate(store_actv_ram):
            setattr(self, name.lower(), lambda i=str(i): self.store_actv_ram(i))

        setattr(self, "add", lambda reg2,reg1,reg0: self.add_r(reg2,reg1,reg0))
        setattr(self, "sub", lambda reg2,reg1,reg0: self.sub_r(reg2,reg1,reg0))

    def __str__ (self):
        res = ""
        for k,v in self.const_variable.items():
            res += f"const: {k:<{30}}: 常量值: 0x{v:02x}\n"
        
        res += "\n"
        
        for k,v in self.variable.items():
            res += f"变量名: {k:<{30}}: 寄存器编号: 0x{v:02x}\n"
        
        res += "\n"
        for k,v in self.labels.items():
            res += f"标签: {k:<{30}}: 指令地址: 0x{v:02x}\n"

        res += "\n"
        # res += "start:\t0\n"
        num = 0
        # ins[0]==1表示label, ins[0]==0表示指令, ins[0]==2表示常量
        for ins in self.ass_ins:
            if ins[0] == 1:
                if num!=0:
                    res += "\n"
                res += "0x"+format(num, 'x')+ "\t" + ins[1]+":"
            elif ins[0]==0:
                res += "0x"+format(num, 'x')
                num += 1
                if ins[1]=="pl_call":
                    num+=1
                res += "\t\t" + ins[1][3:] +"\t"
                if len(ins)>2:
                    for i in range(2,len(ins)):
                        if i!=2: res += ", "
                        # print(ins[i],ins)
                        res += ins[i]
            elif ins[0]==2:
                res += "0x"+format(num, 'x')
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

        for label_name,ins_pos in self.return_label.items():
            self.return_label[label_name] = ins_pos + need_offset
        self.offset = offset

    
    def get_assembler_ins(self):
        """
            返回对应的汇编指令
        """
        res = ""
        num = 0
        # ins[0]==1表示label, ins[0]==0表示指令, ins[0]==2表示常量
        for ins in self.ass_ins:
            if ins[0] == 1:
                if num!=0:
                    res += "\n"
                res += ins[1]+":" + "\t"
            elif ins[0] == 0 or ins[0]==2:
                if ins[1]=="pl_call":
                    num+=1
                num += 1
                res += "\t" + ins[1][3:] +"\t"
                if len(ins)>2:
                    for i in range(2,len(ins)):
                        if i!=2: res += ", "
                        # print(ins[1],ins)
                        res += ins[i]
            # elif ins[0]==2:
            #     res += "\t" + ins[1][3:] +"\t"
            #     if len(ins)>2:
            #         for i in range(2,len(ins)):
            #             if i!=2: res += ", "
            #             # print(ins[1],ins)
            #             res += ins[i]
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
        

        for ins_pos,label,start,length in self.need_replace_return:
            new_data = self.return_label.get(label,None)
            if new_data is not None:
                self.ins_data[ins_pos].command_data.replace_bit(start,length,new_data)
            else:
                raise Exception(f"返回地址{label}未定义!")
        return self.ins_data.copy()
    
    def load_assembler_ins(self,filename:str,encoding:str = 'utf-8'):
        """
            从filename中加载汇编代码
        """
        print("正在编译文件: ",filename)
        with open(filename, 'r', encoding=encoding) as file:
            for line in file:
                # 删除注释,同时删除首尾空格和\t符号
                line = line.replace(';', '#').split('#')[0].strip().lower()
                
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
                    try:
                        getattr(self, cmd_name)(*cmd_data)
                    except Exception as e:
                        print(f"编译指令 {line} 时出错: {e}")
                        # 其他错误处理逻辑（如日志记录、返回默认值等）

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
    
    def to_int8(self,value):
        value = int(value)  # 将字符串转换为整数
        if value < -128 or value > 127:
            raise ValueError("Value out of range for int8")
        return value
    
    def const_str_to_int(self,imm:Union[int|str],mask = 0xFF):
        isConst = False
        if type(imm)==str:
            imm_c = self.get_const_variable(imm)
            if imm_c is None:
                try:
                    imm_c = int(imm,0)
                except Exception as e:
                    raise Exception(f"立即数{imm}未定义!")
            else:
                isConst = True
        elif type(imm)==int:
            imm_c = imm
        else:
            raise Exception(f"立即数{imm}类型错误!")
        
        if imm_c>mask or imm_c < -mask:
            raise Exception(f"立即数{imm_c}超过256/-127限制!")
        return imm_c&mask,isConst
    
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
                if self.check_reg:
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
                    reg_num = int(variable_name[3:])
                    if reg_num>CHIPSETTING.REG_NUM:
                        raise Exception("寄存器不够!")
                    else:
                        self.variable[variable_name] = reg_num
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

    def const_i(self,variable_name:str,value:Union[int|str]):
        """
            Args:
                variable_name: 变量名
                value: 变量值
            新增非寄存器的变量, 用于编译转字节码
        """
        if type(value)==str:
            value = int(value,0)
        if value>256:
            raise Exception(f"立即数{value}超过256限制!")
        self.add_const_variable(variable_name,value)
        self.ass_ins.append((2, "pl_consti", variable_name, str(value)))

    def free_reg(self,variable_name):
        self.del_reg_variable(variable_name=variable_name)


    def call(self,label:str):
        # 翻译成一条move_i 0xff,ins_pos+2
        reg127 = self.get_reg_variable("reg127",init=True)
        ins = CMD(PL_MOVE_I,command_data=CmdData(reg127<<16))
        self.ins_data.append(ins)
        self.ins_pos += 1

        return_label = "return"+str(self.ins_pos+1)
        self.return_label[return_label] = self.ins_pos+1
        # print("0x"+format(self.ins_pos+1, 'x'))

        self.need_replace_return.append((self.ins_pos-1, return_label, 0, 16))


        # 加上一条jump的指令
        ins = CMD(PL_JUMP,command_data=CmdData(0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, "pl_call", label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, CHIPSETTING.INS_RAM_ADDR_LENGTH))

    def jmp(self,label:str):
        """
            pc跳转至label指令处
        """
        ins = CMD(PL_JUMP,command_data=CmdData(0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, CHIPSETTING.INS_RAM_ADDR_LENGTH))

    def set_row_bank_and_data_i(self,imm1,imm0):
        raise Exception(f"set_row_bank_and_data_i未实现!")
    
    def set_col_bank_and_data_i(self,imm1,imm0):
        raise Exception(f"set_col_bank_and_data_i未实现!")

    def set_daci(self,imm1:Union[int|str],imm0:Union[int|str]):
        """
            Args:
                imm1: DAC的通道[0,11]
                imm0: 16bit的电压码值
        """
        imm1_c,isConst1 = self.const_str_to_int(imm1)
        imm0_c,isConst0 = self.const_str_to_int(imm0,mask=0xFFFF)
        ins = CMD(PL_DAC_V,command_data=CmdData(imm1_c <<16 | imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm1, imm0))
        self.ins_pos += 1

        if isConst1:
            self.need_replace_const.append((self.ins_pos-1, imm1, 16, 8))
        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 16))

    def row_read_rram_32ch_to_dout_i(self,imm0:Union[int|str]):
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

    def col_read_rram_32ch_to_dout_i(self,imm0:Union[int|str]):
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

    def row_write_pulse(self):
        """
            从行写
        """
        ins = CMD(PL_WRITE_ROW_PULSE)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def col_write_pulse(self):
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

    def bge_r(self,reg1:str,reg0:str,label:str):
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

        self.need_replace_label.append((self.ins_pos-1, label, CHIPSETTING.BGE_INS_ADDR_START_POS, CHIPSETTING.INS_RAM_ADDR_LENGTH))

    def add_i(self,reg1:str,reg0:str,imm:Union[int|str]):
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

    def exit(self):
        """
            exit
        """
        ins = CMD(PL_EXIT)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def load_din_ram_to_reg(self,reg1:str,reg0:str):
        """
            reg1 = din_ram[reg0]
        """
        reg_0 = self.get_reg_variable(reg0,init=False)
        reg_1 = self.get_reg_variable(reg1)
        ins = CMD(PL_LOAD_DIN_RAM,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0))
        self.ins_pos += 1

    def add_r(self,reg2:str,reg1:str,reg0:str):
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

    def sub_r(self,reg2:str,reg1:str,reg0:str):
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

    def xor_i(self,reg1:str,reg0:str,imm:Union[int|str]):
        """
            reg1 = reg0 ^ imm
        """
        imm_c,isConst = self.const_str_to_int(imm)
        reg_1 = self.get_reg_variable(reg1)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_XORI,command_data=CmdData(imm_c<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg1, reg0, str(imm)))
        self.ins_pos += 1

        if isConst:
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

    def set_row_bank_and_data_r(self,reg1:str,reg0:str):
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

    def set_col_bank_and_data_r(self,reg1:str,reg0:str):
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

    def row_read_rram_1ch_to_dout(self,reg2:str,reg1:str,reg0:str):
        """
            Args:
                reg2: tia的mask
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

    def col_read_rram_1ch_to_dout(self,reg2:str,reg1:str,reg0:str):
        """
            Args:
                reg2: tia的mask
                reg1: dout_ram_addr
                reg0: dout_ram块(0,1)
            --废弃
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

    def row_read_rram_1ch_to_reg(self,reg1:str,reg0:str):
        """
            Args:
                reg1: tia的mask
                reg0: 读出来的结果存在reg0
        """
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_READ_ROW_PULSE_REG,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name,reg1, reg0))
        self.ins_pos += 1

    def col_read_rram_1ch_to_reg(self,reg1:str,reg0:str):
        """
            Args:
                reg1: tia的mask
                reg0: 读出来的结果存在reg0
            -- 废弃
        """
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_READ_COL_PULSE_REG,command_data=CmdData(reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name,reg1, reg0))
        self.ins_pos += 1

    def row_ctrl_i(self,imm0:Union[int|str]):
        """
            Args:
                imm0: 0|1
        """
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_ROW_CTRLI,command_data=CmdData(imm0_c<<16))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm0))
        self.ins_pos += 1

        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 16, 8))

    def col_ctrl_i(self,imm0:Union[int|str]):
        """
            Args:
                imm0: 0|1
        """
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_COL_CTRLI,command_data=CmdData(imm0_c<<16))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm0))
        self.ins_pos += 1
        
        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 16, 8))

    def row_col_sw_i(self,imm0:Union[int|str]):
        """
            Args:
                imm0: 0|1
        """
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_ROW_COL_SWI,command_data=CmdData(imm0_c<<16))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm0))
        self.ins_pos += 1
        
        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 16, 8))

    def row_read_rram_32ch_to_diff(self):
        """
            产生row读pulse,求平均,32路并行diff写入16个专用寄存器。舍弃adc最低的n bits
        """
        ins = CMD(PL_READ_ROW_PULSE_DIFF)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def col_read_rram_32ch_to_diff(self):
        """
            产生col读pulse,求平均,32路并行diff写入16个专用寄存器。舍弃adc最低的n bits
        """
        ins = CMD(PL_READ_COL_PULSE_DIFF)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def cal_ch_mask(self,imm1:Union[int|str],imm0:Union[int|str]):
        """
            Args:
                imm1:mask[15:8]
                imm0:mask[7:0]
        """
        imm1_c,isConst1 = self.const_str_to_int(imm1)
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_CAL_CH_MASK,command_data=CmdData(imm1_c <<8 | imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm1, imm0))
        self.ins_pos += 1

        if isConst1:
            self.need_replace_const.append((self.ins_pos-1, imm1, 8, 8))
        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def apu_calc(self,imm0:Union[int|str]):
        """
            Args:
                imm0: mode
        """
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_APU_MODE,command_data=CmdData(imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm0))
        self.ins_pos += 1

        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def element_wise(self,reg0:Union[str|None],imm1:Union[int|str],imm0:Union[int|str]):
        """
            Args:
                reg0:
                imm1:
                imm0:mode

        """
        if reg0 is None:
            reg0 = ""
            reg_0 = 0
        else:
            reg_0 = self.get_reg_variable(reg0,init=False)
        imm1_c,isConst1 = self.const_str_to_int(imm1)
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_ELEMENT_WISE,command_data=CmdData(reg_0 <<16 | imm1_c <<8 | imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg0, imm1, imm0))
        self.ins_pos += 1

        if isConst1:
            self.need_replace_const.append((self.ins_pos-1, imm1, 8, 8))
        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def set_actv_ram_addr(self,reg0:str):
        """

        """
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_ACTV_RAM_ADDR,command_data=CmdData(reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg0))
        self.ins_pos += 1

    def load_actv_ram(self):
        """
            actv_read
        """
        ins = CMD(PL_ACTV_RAM_READ)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def store_actv_ram(self,imm0:Union[int|str]):
        """
            Args:
                imm0: mode
        """
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_ACTV_RAM_WRITE,command_data=CmdData(imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm0))
        self.ins_pos += 1

        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def reshape_buffer_clear(self):
        """
            actv_read
        """
        ins = CMD(PL_RESHAPE_BUFFER_CLEAR)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def set_reshape_buffer_addr(self,reg0:str):
        """

        """
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_RESHAPE_BUFFER_ADDR,command_data=CmdData(reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg0))
        self.ins_pos += 1

    def store_reshape_buffer(self):
        """
            actv_read
        """
        ins = CMD(PL_RESHAPE_BUFFER_WRITE)
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name))
        self.ins_pos += 1

    def load_reshape_buffer_t(self,reg2:str,reg1:str,reg0:str):
        """
        """
        reg_2 = self.get_reg_variable(reg2,init=False)
        reg_1 = self.get_reg_variable(reg1,init=True)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_RESHAPE_BUFFER_READ,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2,reg1, reg0))
        self.ins_pos += 1

    def set_adc_discard_nbits(self,imm0:Union[int|str]):
        """
        """
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        ins = CMD(PL_SET_ADC_DISCARD_NBITS,command_data=CmdData(imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, imm0))
        self.ins_pos += 1

        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 8))

    def mov_i(self,reg0:str,imm0:Union[int|str]):
        """
            reg0 = imm0
        """
        reg_0 = self.get_reg_variable(reg0,init=True)
        imm0_c,isConst0 = self.const_str_to_int(imm0,mask=0xFFFF)
        ins = CMD(PL_MOVE_I,command_data=CmdData(reg_0 <<16 | imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg0, imm0))
        self.ins_pos += 1

        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 16))

    def mov_r(self,reg1:str,reg0:str):
        """
            reg1 = reg0
        """
        reg_1 = self.get_reg_variable(reg1,init=True)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_MOVE_R,command_data=CmdData(reg_1<<16|reg_0<<8))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name,reg1, reg0))
        self.ins_pos += 1

    def cmp_i(self,reg0:str,imm0:Union[int|str]):
        """
            reg0 比较 imm0
        """
        reg_0 = self.get_reg_variable(reg0,init=False)
        imm0_c,isConst0 = self.const_str_to_int(imm0,mask=0xFFFF)
        ins = CMD(PL_CMP_I,command_data=CmdData(reg_0 <<16 | imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg0, imm0))
        self.ins_pos += 1

        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 16))

    def cmp_r(self,reg1:str,reg0:str):
        """
            reg1 比较 reg0
        """
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_CMP_R,command_data=CmdData(reg_1<<16|reg_0<<8))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name,reg1, reg0))
        self.ins_pos += 1

    def jeq(self,label:str):
        """
            pc跳转至label指令处
        """
        ins = CMD(PL_JEQ,command_data=CmdData(0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, 16))


    def jne(self,label:str):
        """
            pc跳转至label指令处
        """
        ins = CMD(PL_JNE,command_data=CmdData(0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, 16))

    def jlt(self,label:str):
        """
            pc跳转至label指令处
        """
        ins = CMD(PL_JLT,command_data=CmdData(0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, 16))

    def jgt(self,label:str):
        """
            pc跳转至label指令处
        """
        ins = CMD(PL_JGT,command_data=CmdData(0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, 16))

    def jle(self,label:str):
        """
            pc跳转至label指令处
        """
        ins = CMD(PL_JLE,command_data=CmdData(0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, 16))

    def jge(self,label:str):
        """
            pc跳转至label指令处
        """
        ins = CMD(PL_JGE,command_data=CmdData(0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, label))
        self.ins_pos += 1

        self.need_replace_label.append((self.ins_pos-1, label, 0, 16))

    def jump_r(self,reg0:str):
        """
            jump to [reg0]
        """
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_JUMP_R,command_data=CmdData(reg_0<<16))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg0))
        self.ins_pos += 1

    def mul(self,reg2:str,reg1:str,reg0:str):
        """
        """
        reg_2 = self.get_reg_variable(reg2,init=False)
        reg_1 = self.get_reg_variable(reg1,init=False)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_MUL_R,command_data=CmdData(reg_2<<16|reg_1<<8|reg_0))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg2,reg1, reg0))
        self.ins_pos += 1

    def set_dac_i(self,imm0:Union[int|str],reg0:Union[int|str]):
        """
            !!!!未实现
            Args:
                imm1: DAC的通道[0,11]
                imm0: 16bit的电压码值
        """
        raise Exception(f"sset_dac_i未实现!")
        print("指令set_dac未实现")
        imm0_c,isConst0 = self.const_str_to_int(imm0)
        reg_0 = self.get_reg_variable(reg0,init=False)
        ins = CMD(PL_DAC_V,command_data=CmdData(reg_0 <<16 | imm0_c))
        self.ins_data.append(ins)
        self.ass_ins.append((0, ins.command_name, reg0, imm0))
        self.ins_pos += 1

        if isConst0:
            self.need_replace_const.append((self.ins_pos-1, imm0, 0, 16))


