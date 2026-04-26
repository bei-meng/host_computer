### 上位机开发程序

- 2025.5.30 - ArrTest2.0_Firmware1.0_Code1.0.4
- 2025.6.6 - ArrTest2.0_Firmware1.0_Code1.0.5
- 2025.6.9 - ArrTest2.0_Firmware1.0_Code1.0.6
- 2025.6.10 - ArrTest2.0_Firmware1.0_Code1.0.7

  - 汇编器里面新增10多条pl指令
  - ddr寻址规则改为32B为单位，但是数据依旧以4B为单位
- 2025.6.13 - ArrTest2.0_Firmware1.0_Code1.0.8

  - 加入ReRAM-ECRAM读写示例文件
  - 修复ps传指令的问题
- 2025.6.14 - ArrTest2.0_Firmware1.0_Code1.0.9

  - v201,v202,v203,v101adc测试
  - 线阻补偿测试
- 2025.6.17 - ArrTest2.0_Firmware1.0_Code1.1.0

  - adc噪声测试
  - 32路补偿测试
- 2025.6.18 - ArrTest2.0_Firmware1.0_Code1.1.0

  - 汇编代码编译成字节码功能的完善
  - ps往上位机传数据处理数据功能的完善
    - adc噪声测试
    - 32路补偿测试
- 2025.6.23 - AT2_F_Code1.1.1

  - adc测试
  - 佩鸿师兄部署网络测试
  - 编译器的bug修复
- 2025.7.9 - AT2_F_Code1.1.2

  - 返回数据量的优化
  - ret汇编指令改成寄存器63
- 2025.7.17 - AT2_F_Code1.1.3

  - 修改多版reset信号的逻辑
- 2025.09.24 - AT2_F_Code1.1.4

  - 没有修改，新增一个版本

    def set_cim_reset(self,flag1=False,flag2=0b0000_0000,flag3="",reset_ans=0):

    """

    发送reset的指令,

    如果flag1为真,将reset信号设置为flag2

    否则:

    如果为ECRAM或不为v1.4版本,将reset信号状态设置为reset_ans

    否则使用REG_OUT设置为reset_ans

    """
- 2025.12.01 - AT2_F_Code1.1.5

  - 新增神经元相关指令AT2_F_Code1.1.4
- 2025.12.29 - AT2_F_Code1.1.6

  - 修改ECRAM的inversion_type==2兼容
- 2026.01.18 - AT2_F_Code1.1.7

  - 整理删除文件，用硬件读写接口替换软件实现的推理和权重更新过程
- 2026.02.06 - AT2_F_Code1.1.8

  - 新增解码在FPGA中完成的接口，新增reset控制信号和脉冲参数配置的指令
- 2026.04.06 - AT2_F_Code1.1.9

  - 新增ECRAM逐点读汇编代码
- 2026.04.26 - AT2_F_Code1.2.0

  - ECRAM供电关闭指令
