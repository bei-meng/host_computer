from cimCommand import CMD,CmdData,Packet
from cimCommand.singleCmdInfo import *
from pc import PS
from modules.adc import ADC
from modules.dac import DAC

class CHIP():
    """
        对chip进行的操作
    """
    deviceType = 0                  # 器件类型0: RERAM,1: ECRAM
    latch_cyc = 2                   # PCB上锁存器的latch cycle树
    reg_clk_cyc = 2                 # 高电平cycle数，1 cycle=10ns 0：翻转
    latch_clk_cyc = 2               # 高电平cycle数，1 cycle=10ns 0：翻转
    pulse_cyc = 256                 # row/col pulse的cycle数 0：翻转"


    pulse_cyc_length = 10*1e-9      # 每个cycle的宽度为10ns

    read_from_row = True            # 从行读的模式
    read_voltage = None             # 读电压

    write_voltage = None            # 写电压

    op_mode = None                  # 当前所处模式


    ps = None
    adc = None
    dac = None

    def __init__(self, adc:ADC, dac:DAC, ps:PS):
        self.ps = ps
        self.adc = adc
        self.dac = dac

        # DAC的初始化操作
        self.initOp()

    def get_setting_info(self):
        """
            输出相关信息
        """
        device = "ECRAM" if self.deviceType else "ReRAM"
        row_col = "行" if self.read_from_row else "列"
        if self.op_mode == "read":
            res = f"操作模式：{self.op_mode}\t器件：{device}\t读电压：{self.read_voltage}v\t从行\列给电压：{row_col}\tTIA增益：{self.adc.gain}"
        elif self.op_mode == "write":
            res = f"操作模式：{self.op_mode}\t器件：{device}\t写电压：{self.write_voltage}v\t脉宽：{self.pulse_cyc}"
        else:
            res = f"未配置操作模式。"
        return res

    #------------------------------------------------------------------------------------------
    # ********************************** 器件初始化及相关配置 ***********************************
    #------------------------------------------------------------------------------------------
    def initOp(self):
        """
            chip的初始化操作
        """
        # 配置器件的初始化
        self.set_device_cfg(deviceType=0,reg_clk_cyc=0xF,latch_clk_cyc=0xF)
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(FLT,command_data=CmdData(0x0FFF)),                  # 配置flt
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_flt_le1)),         # cfg_flt_le1
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_flt_le2)),         # cfg_flt_le2
            CMD(CIM_RESET,command_data=CmdData(1)),                 # reset指令
            CMD(CIM_SS,command_data=CmdData(1)),                    # reg写入数据打开
            CMD(SER_PARA_SEL,command_data=CmdData(1)),              # 切换到并行模式
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)

    def set_device_cfg(self,deviceType = None,latch_cyc = None, reg_clk_cyc= None, latch_clk_cyc = None):
        """
            设置device的cfg
        """
        self.deviceType = self.deviceType if deviceType is None else deviceType
        self.latch_cyc = self.latch_cyc if latch_cyc is None else latch_cyc
        self.reg_clk_cyc = self.reg_clk_cyc if reg_clk_cyc is None else reg_clk_cyc
        self.latch_clk_cyc = self.latch_clk_cyc if latch_clk_cyc is None else latch_clk_cyc

        data = self.deviceType | self.latch_cyc<<1 | self. reg_clk_cyc<<3 | self.latch_clk_cyc<<7
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(DEVICE_CFG,command_data=CmdData(data)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)

    def set_pulse_width(self,pulsewidth):
        """
            设置施加的脉宽的宽度
        """
        pulse_cyc=int(pulsewidth/self.pulse_cyc_length)
        assert pulse_cyc>=0 ,"set_pulse_width: 脉宽超过界限！"

        pkts=Packet()
        pkts.append_cmdlist([
            CMD(PULSE_CYC,command_data=CmdData(pulse_cyc)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)

        self.pulse_cyc = pulse_cyc
    
    #------------------------------------------------------------------------------------------
    # ********************************* 配置latch，行列的映射 **********************************
    #------------------------------------------------------------------------------------------
    def numToBank_Index(self,num:int):
        """
            注意：num从0索引开始
            将x,y译码为对应的bank和index
            bank和index均从0开始，方便后面的位操作
        """
        num += 1
        assert num > 0 and num < 257,"numToBank_Index: num超过范围!"
        # 先判断奇数偶数
        if num&1:
            index_base,index_offset = 64,1
            bank_base = 0
        else:
            index_base,index_offset = 64,2
            bank_base = 4

        bank_offset = int((num-index_offset)/index_base)
        bank = bank_base + bank_offset
        index = int((num - index_offset - bank_offset * index_base) / 2)

        return bank, index
    
    def get_data(self,num:list):
        bank,index = 0,0
        for i in num:
            bank_tmp,index_tmp = self.numToBank_Index(i)
            bank = bank | (1<<bank_tmp)
            index = index | (1<<index_tmp)
        return bank,index
    

    def get_bank_tia(self,num:list):
        """
            对应行号列号，映射为bank，index，tia
        """
        res = []
        for k,v in enumerate(num):
            bank,index = self.numToBank_Index(v)
            tia = self.adc.TIA_index_map(v,device=self.deviceType,col=self.read_from_row)

            res.append((k,v,bank,index,tia))
        return res
            
    def set_cim_reset(self):
        """
            发送reset的指令
        """
        pkts=Packet()
        # reset指令
        pkts.append_cmdlist([
            CMD(CIM_RESET,command_data=CmdData(0)),
            CMD(CIM_RESET,command_data=CmdData(1)),
        ],mode=1)
        self.ps.send_packets(pkts)

    def set_latch(self,num:list[list],row=True,value=None):
        """
            将对应的行或列配置成latch为1,
            num: 为嵌套列表,第一层表示有几个bank,第二层表示bank中需要修改的行号和列号,从0开始
        """
        row_col_sel = 1 if row else 0
        pkts=Packet()
        # 配置行
        for i in num:
            if len(i)>0:
                bank,index = self.get_data(i)
                # 如果是要将32bit的值改成对应的值
                if value is not None:
                    index = value
                pkts.append_cmdlist([
                    # 行reg配置
                    CMD(CIM_DATA_IN,command_data=CmdData(index)),                                       # 第index位置1
                    CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_cim_data_in)),       # cfg_cim_data_in
                    CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_reg_clk)),           # cfg_reg_clk

                    # 行bank配置
                    CMD(ROW_COL_SEL,command_data=CmdData(row_col_sel)),                                 # 设置为行/列模式
                    CMD(CIM_BANK_SEL,command_data=CmdData(bank)),                                       # 行bank选择
                    CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_bank_sel)),          # cfg_bank_sel
                    CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_latch_clk)),         # cfg_latch_clk
                ],mode=1)   
        self.ps.send_packets(pkts)

    def set_bank_latch(self,banknum:list,row=True,value=0):
        """
            将对应行/列的bank配置成对应的值
            banknum: 为要修改的bank的列表, 从0开始
            row: 表示是修改的row的,还是col的
            value: 为对应要修改32bit的值
        """
        assert len(banknum)>0,"set_bank_latch：空列表。"
        row_col_sel = 1 if row else 0
        pkts=Packet()
        # 配置行
        for i in banknum:
            pkts.append_cmdlist([
                # 行reg配置
                CMD(CIM_DATA_IN,command_data=CmdData(value)),                                       # 第xindex位置1
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_cim_data_in)),       # cfg_cim_data_in
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_reg_clk)),           # cfg_reg_clk

                # 行bank配置
                CMD(ROW_COL_SEL,command_data=CmdData(row_col_sel)),                                 # 设置为行/列模式
                CMD(CIM_BANK_SEL,command_data=CmdData(1<<i)),                                       # bank选择
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_bank_sel)),          # cfg_bank_sel
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_latch_clk)),         # cfg_latch_clk
            ],mode=1)   
        self.ps.send_packets(pkts)

    #------------------------------------------------------------------------------------------
    # ************************************** 读相关操作 ****************************************
    #------------------------------------------------------------------------------------------
    def set_read_mode(self,row=True,delay=None):
        """
            设置read的模式,从行读的配置,从列读的配置
        """
        self.op_mode = "read"
        self.read_from_row = row
        if self.read_from_row:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(ROW_CTRL,command_data=CmdData(1)),                                                  # 配置行到施加电压
                CMD(COL_CTRL,command_data=CmdData(0)),                                                  # 配置列到TIA
                CMD(ROW_COL_SW,command_data=CmdData(1)),                                                # PCB上的TIA接在列
            ],mode=1)
            self.ps.send_packets(pkts,delay=delay)
        else:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(ROW_CTRL,command_data=CmdData(0)),                                                  # 配置行到TIA
                CMD(COL_CTRL,command_data=CmdData(1)),                                                  # 配置列到电压
                CMD(ROW_COL_SW,command_data=CmdData(0)),                                                # PCB上的TIA接在行
            ],mode=1)
            self.ps.send_packets(pkts,delay=delay)

    def set_dac_read_V(self,v:int):
        """
            配置dac的读电压
        """
        self.read_voltage = v
        if self.deviceType==0:
            if self.read_from_row:
                self.dac.set_voltage(0,dac_num=0,dac_channel=0)           #
                self.dac.set_voltage(0,dac_num=0,dac_channel=1)           #
                self.dac.set_voltage(0,dac_num=0,dac_channel=2)           #
                self.dac.set_voltage(0,dac_num=0,dac_channel=3)           #

                self.dac.set_voltage(0,dac_num=0,dac_channel=4)           #
                self.dac.set_voltage(0,dac_num=0,dac_channel=5)           #
                self.dac.set_voltage(5,dac_num=0,dac_channel=6)           # TG
                self.dac.set_voltage(0,dac_num=0,dac_channel=7)           #

                self.dac.set_voltage(v,dac_num=1,dac_channel=0)           # ROW_Va
                self.dac.set_voltage(0,dac_num=1,dac_channel=1)           #  
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)           # COL_Va
                self.dac.set_voltage(0,dac_num=1,dac_channel=3)           #
            else:
                self.dac.set_voltage(0,dac_num=0,dac_channel=0)           #
                self.dac.set_voltage(0,dac_num=0,dac_channel=1)           #
                self.dac.set_voltage(0,dac_num=0,dac_channel=2)           #
                self.dac.set_voltage(0,dac_num=0,dac_channel=3)           #

                self.dac.set_voltage(0,dac_num=0,dac_channel=4)           #
                self.dac.set_voltage(0,dac_num=0,dac_channel=5)           #
                self.dac.set_voltage(5,dac_num=0,dac_channel=6)           # TG
                self.dac.set_voltage(0,dac_num=0,dac_channel=7)           #

                self.dac.set_voltage(v,dac_num=1,dac_channel=0)           # ROW_Va
                self.dac.set_voltage(0,dac_num=1,dac_channel=1)           #    
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)           # COL_Va
                self.dac.set_voltage(0,dac_num=1,dac_channel=3)           #
        elif self.deviceType==1:
            if self.read_from_row:
                self.dac.set_voltage(v,dac_num=0,dac_channel=0)           # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=1)           # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=2)           # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=3)           # ROW_Va电压

                self.dac.set_voltage(0,dac_num=0,dac_channel=4)           # COL_Va电压
                self.dac.set_voltage(0,dac_num=0,dac_channel=5)           # COL_Va电压
                self.dac.set_voltage(0,dac_num=0,dac_channel=6)           # COL_Va电压
                self.dac.set_voltage(0,dac_num=0,dac_channel=7)           # COL_Va电压

                self.dac.set_voltage(0,dac_num=1,dac_channel=0)           # ROW_Vc
                self.dac.set_voltage(0,dac_num=1,dac_channel=1)           # COL_Vc     
                self.dac.set_voltage(0,dac_num=1,dac_channel=2)           # GL
                self.dac.set_voltage(0,dac_num=1,dac_channel=3)           # GR
            else:
                self.dac.set_voltage(0,dac_num=0,dac_channel=0)           # ROW_Va电压
                self.dac.set_voltage(0,dac_num=0,dac_channel=1)           # ROW_Va电压
                self.dac.set_voltage(0,dac_num=0,dac_channel=2)           # ROW_Va电压
                self.dac.set_voltage(0,dac_num=0,dac_channel=3)           # ROW_Va电压

                self.dac.set_voltage(v,dac_num=0,dac_channel=4)           # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=5)           # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=6)           # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=7)           # COL_Va电压

                self.dac.set_voltage(0,dac_num=1,dac_channel=0)           # ROW_Vc
                self.dac.set_voltage(0,dac_num=1,dac_channel=1)           # COL_Vc     
                self.dac.set_voltage(0,dac_num=1,dac_channel=2)           # GL
                self.dac.set_voltage(0,dac_num=1,dac_channel=3)           # GR

    def generate_read_pulse(self):
        """
            产生读脉冲的指令
        """
        if self.read_from_row:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(PULSE_CYC,command_data=CmdData(0)),                                             # 翻转
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),         # cfg_col_pulse，配置列为常1
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_read)),          # 然后开始读,行给电压
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),         # cfg_col_pulse，读完后，把列电压翻转为0
            ],mode=1)
            self.ps.send_packets(pkts)
        else:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(PULSE_CYC,command_data=CmdData(0)),                                             # 翻转
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_pulse)),         # cfg_row_pulse，配置行为常1
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_read)),          # 然后开始读,列给电压
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_pulse)),         # cfg_row_pulse，读完后，把行电压翻转为0
            ],mode=1)
            self.ps.send_packets(pkts)

    def read_one(self,row_index:int,col_index:int):
        """
            读某一个器件，row_index为行索引，col_index为列索引
        """
        print(self.get_setting_info())
        assert self.op_mode == "read","未设置为读模式。"
        self.set_cim_reset()                                                                        # 先reset 
        self.set_latch([[row_index]],row=True,value=None)                                           # 配置行
        self.set_latch([[col_index]],row=False,value=None)                                          # 配置列
        self.generate_read_pulse()                                                                  # 产生读脉冲
        
        if self.read_from_row:
            tia_index = self.adc.TIA_index_map(col_index,self.deviceType,True)
        else:
            tia_index = self.adc.TIA_index_map(col_index,self.deviceType,True)
            
        return self.adc.get_out([tia_index],read_voltage=self.read_voltage)

    def read_row_or_col(self,row_index:list,col_index:list):
        """
            读某一行里面的器件，row_index为行索引，col_index为列索引
        """
        print(self.get_setting_info())
        assert self.op_mode == "read","未设置为读模式。"
        if self.read_from_row:
            assert len(row_index)==1,"从行读，行必须仅选择一行。"
        else:
            assert len(col_index)==1,"从列读，列必须仅选择一行。"
            row_index, col_index = col_index, row_index
        self.set_cim_reset()                                                                      # 先reset 
        self.set_latch([row_index],row=self.read_from_row,value=None)                             # 配置行

        index_data = self.get_bank_tia(col_index)                                                 # 映射得到i,num,bank，index，tia
        # ----------------------------------------------映射16路tia
        tia16 = [[] for _ in range(16)]
        for i in index_data:
            # print(i)
            tia16[i[4]].append(i)
        # print("tia16",tia16)
        # ----------------------------------------------每路TIA选一路
        flag = True
        read_num = []
        while flag:
            flag = False
            tmp = []
            for i in tia16:
                if len(i)>0:
                    tmp.append(i.pop())                 # 每路tia选一个值
                    flag = True
            if flag == True:
                read_num.append(tmp)
        # print("选择16路tia")
        # for i in read_num:
        #     print(i)
        # ----------------------------------------------循环去读
        read_res = []
        for i in read_num:
            # ------------------------------------------映射8个bank
            bank8 = [[] for _ in range(8)]
            for j in i:
                bank8[j[2]].append(j[1])
            print("映射bank",bank8)
            # ------------------------------------------开始配置列latch,如果从行读，row=False，从列读，row=True
            self.set_latch(bank8,row=not self.read_from_row,value=None)
            # ------------------------------------------给读脉冲
            self.generate_read_pulse() 
            # ------------------------------------------读出结果
            tia_out = self.adc.get_out([j[4] for j in i],read_voltage=self.read_voltage)
            read_res.append(tia_out)
        # ----------------------------------------------将结果映射回原来的顺序
        result = [0]*len(col_index)
        for i,v1 in enumerate(read_num):
            for j,v2 in enumerate(v1):
                result[v2[0]]=read_res[i][j]
        return result

    #------------------------------------------------------------------------------------------
    # ************************************** 写相关操作 ****************************************
    #------------------------------------------------------------------------------------------
    def write_one_dG(self,x, y, write_voltage=5, pulsewidth=255*10*1e-9, dG=1e-3, dGperPulse=1e-5, eRate=0.01, maxWrite=10):
        """
            写一个器件
            注意: x和y都是从0索引开始
        """
        # 设置为写模式
        self.change_operation_mode("write")

        # 配置行列的latch
        self.cfg_row_col_one(x,y)

        # 设置电压
        self.set_voltage(write_voltage)

        pkts=Packet()
        pkts.append_cmdlist([
            CMD(PULSE_CYC,command_data=CmdData(0)),                                                 # 翻转
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),             # cfg_col_pulse，常1
            CMD(PULSE_CYC,command_data=CmdData(int(pulsewidth/self.pulse_cyc_length))),             # 设置脉宽
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_pulse)),             # cfg_row_pulse, 给写脉冲
            CMD(PULSE_CYC,command_data=CmdData(0)),                                                 # 翻转回来
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),             # cfg_col_pulse，写完后，把列电压置0
        ],mode=1)
        self.ps.send_packets(pkts)
    