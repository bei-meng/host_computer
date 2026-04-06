# 读[row_start_num,row_end_num][col_start_num,col_start_num]这块区域的值
# 默认会定义一个寄存器变量zero,值为0
    const_uint8 per_points_bit, 5                                                                        # 每行能存多少数据2^4表示能存16个，对应v1
    const_uint8 per_points_sub1, 31
    #---------------------------------------------------------------------------------------------------每个dout_ram能存的最大数据
    const_uint8 count_max_pos, 144
    const_uint8 pq_c, 0                                                          # 有两块dout_ram，控制选择哪一块dout_ram写数据

    #---------------------------------------------------------------------------------------------------要读的行bank号在din_ram存放的位置,以及右边界
    const_uint8 row_bank_din_ram_s_c, 0
    const_uint8 row_bank_din_ram_e_c, 0

    #---------------------------------------------------------------------------------------------------要读的行bank号在din_ram存放的位置,以及右边界
    const_uint8 col_bank_din_ram_s_c, 8
    const_uint8 col_bank_din_ram_e_c, 8

    #---------------------------------------------------------------------------------------------------每个行bank的起始index号和结束index号在din_ram存放的位置
    const_uint8 row_index_din_ram_s_c, 16
    const_uint8 row_index_din_ram_e_c, 24

    #---------------------------------------------------------------------------------------------------每个列bank的起始index号和结束index号在din_ram存放的位置
    const_uint8 col_index_din_ram_s_c, 32
    const_uint8 col_index_din_ram_e_c, 40

    const_uint8 row_col_type0, 48                                                                          # 正常32bit
    const_uint8 row_col_type1, 80                                                                          # 存储表示index中01反转的32bit
    const_uint8 row_col_type2, 112                                                                          # 只有选中的TIA不反转，其他TIA对应latch都反转

    const_uint8 row_index_pos, 48
    const_uint8 col_index_pos, 48

    const_uint8 row_index_init,145
    const_uint8 col_index_init,145
start:
    # 一定要记得reset！！！！！！！！！！！！！！！！！！！！！！！！！！！！！
    set_row_bank_and_data_i 0xFF,row_index_init
    set_col_bank_and_data_i 0xFF,col_index_init

    add_i row_index_init_reg,zero,row_index_init
    add_i col_index_init_reg,zero,col_index_init
    load_din_ram_to_reg row_index_init_reg,row_index_init_reg
    load_din_ram_to_reg col_index_init_reg,col_index_init_reg

    #---------------------------------------------------------------------------------------------------用于移位操作的寄存器数
    add_i one, zero, 1                                                       # 寄存器里面存的1
    add_i two, zero, 2
    add_i three, zero,3
    add_i four, zero, 4                                                      # 寄存器里面存的2

    #---------------------------------------------------------------------------------------------------用于下面的dout_ram满了之后将数据上传
    add_i count, zero, 0                                                     # 初始化计数器
    add_i count_max, zero, count_max_pos  
    load_din_ram_to_reg    count_max,count_max                               # 加载最大读的点数
    #---------------------------------------------------------------------------------------------------存储当前是使用的哪一块dout_ram
    add_i pq, zero,pq_c

    #---------------------------------------------------------------------------------------------------初始化取行bank地址的起始和结束边界
    # []左闭右闭, row_bank_addr 为起始边界, row_bank_end_addr 为结束边界
    add_i row_bank_addr, zero, row_bank_din_ram_s_c                          # 初始化寄存器，存放din_ram中的第一个要读的行bank的bank号的addr
    add_i row_bank_end_addr, zero, row_bank_din_ram_e_c                      # 初始化寄存器，存放din_ram中的第一个截止读的行bank的bank号的addr

    #---------------------------------------------------------------------------------------------------初始化取行index号地址的起始和结束边界
    add_i row_index_start_addr, zero, row_index_din_ram_s_c                  # 初始化寄存器，存放din_ram中的第一个行bank起始读的行index的addr
    add_i row_index_end_addr, zero, row_index_din_ram_e_c                    # 初始化寄存器，存放din_ram中的第一个行bank截止读的行index的addr

    add_i per_ponts_num,zero,per_points_bit                                 # 每行能存多少个点
loop1:
    #---------------------------------------------------------------------------------------------------取行bank号, 生成行bank掩码, 
    #row_bank_addr 为计数器,会++, 直到结束边界
    load_din_ram_to_reg    row_bank_num,row_bank_addr                              # 加载bank号
    sll     row_bank_mask, one, row_bank_num                                # row_bank_mask = one << row_bank_num

    #---------------------------------------------------------------------------------------------------初始化index号遍历的起始和结束边界
    # row_index_start_addr 和 row_index_end_addr 会++, row_index_num 为起始边界, row_end_index 为结束边界
    load_din_ram_to_reg    row_index_num, row_index_start_addr                     # 将当前行bank的起始index号加载进来
    load_din_ram_to_reg    row_end_index, row_index_end_addr                       # 将当前行bank的截止index号加载进来

loop2:
    #---------------------------------------------------------------------------------------------------取行index号, 生成行index掩码, 
    #row_index_num为计数器,会++
    add_i current_row_index_pos, row_index_num,row_index_pos 
    load_din_ram_to_reg row_index_mask, current_row_index_pos                                  # 从对应位置加载行的mask
    set_row_bank_and_data_r row_bank_mask, row_index_mask                              # 配置行bank

    #---------------------------------------------------------------------------------------------------初始化取列bank地址的起始和结束边界
    # []左闭右闭, col_bank_addr 为起始边界, col_bank_end_addr 为结束边界
    add_i col_bank_addr, zero, col_bank_din_ram_s_c                          # 初始化寄存器，存放din_ram中的第一个要读的列bank的bank号的addr
    add_i col_bank_end_addr, zero, col_bank_din_ram_e_c                      # 初始化寄存器，存放din_ram中的第一个截止读的列bank的bank号的addr

    #---------------------------------------------------------------------------------------------------初始化取列index号地址的起始和结束边界
    add_i col_index_start_addr, zero, col_index_din_ram_s_c                  # 初始化寄存器，存放din_ram中的第一个列bank起始读的列index的addr
    add_i col_index_end_addr, zero, col_index_din_ram_e_c                    # 初始化寄存器，存放din_ram中的第一个列bank截止读的列index的addr

loop3:
    #---------------------------------------------------------------------------------------------------取列bank号, 生成列bank掩码, 
    #col_bank_addr为计数器,会++
    load_din_ram_to_reg    col_bank_num,col_bank_addr                              # 加载bank号
    sll     col_bank_mask, one, col_bank_num                                # col_bank_mask = one << col_bank_num

    #---------------------------------------------------------------------------------------------------初始化index号遍历的起始和结束边界
    # col_index_start_addr 和 col_index_end_addr 会++
    load_din_ram_to_reg    col_index_num, col_index_start_addr                     # 将当前行bank的起始row index加载进来
    load_din_ram_to_reg    col_end_index, col_index_end_addr                       # 将当前行bank的截止row index加载进来

    #---------------------------------------------------------------------------------------------------计算tia的base
    bge_r col_bank_num, four, tia_big4                                        # 如果col_bank_num >= 4，跳转到tia_big4,表示是偶数行/列

tia_nobig4:# 奇数行/列，ECRAM对应0+col_bank_num*4
    sll     tia_base, col_bank_num, two                                         # tia_base = col_bank_num * 4
    jmp loop4

tia_big4: #偶数行/列,ECRAM对应17+(col_bank_num-4)*4 = 1+col_bank_num*4
    sll       tia_base, col_bank_num, two                                         # tia_base = col_bank_num * 4
    add_i     tia_base,tia_base,1

loop4:
    #---------------------------------------------------------------------------------------------------取列index号, 生成列index掩码, 
    #col_index_num为计数器,会++,范围[0:31]
    add_i current_col_index_pos,col_index_num, col_index_pos 
    load_din_ram_to_reg col_index_mask, current_col_index_pos                                  # 从对应位置加载列的mask
    set_col_bank_and_data_r col_bank_mask, col_index_mask                              # 配置列bank

    #---------------------------------------------------------------------------------------------------计算tia,并设置tia_mask
    srl tia_offset, col_index_num, four
    sll tia_offset, tia_offset, one
    add_r tia_num, tia_base, tia_offset                                       # tia_num = tia_base + tia_offset
    sll tia_mask,one,tia_num                                                # tia_mask = one << tia_num

    row_read_rram_1ch_to_dout tia_mask,count,pq
    #---------------------------------------------------------------------------------------------------控制返回的计数器, 计数已经操作了多少个点了
    add_i    count, count, 1                                                 # count, count + 1
    bge_r     count, count_max, return_0                                      # 如果count >= count_max, 跳转到return_0
    jmp   jmp_return

return_0:
    add_i count,count,per_points_sub1
    srl return_len,count, per_ponts_num                               # return_len=return_len/32行
    return_dout return_len,zero ,pq
    xor_i    pq, pq, 1                                                       # pq, pq xor 1 
    add_i    count, zero, 0                                                  # count, 0

jmp_return:
    #---------------------------------------------------------------------------------------------------当前列bank里面的所有列都遍历完了,就跳出循环,否则下一列
    bge_r col_index_num, col_end_index, end4                                  # 如果col_index_num >= col_end_index，跳转到end4
    add_i col_index_num, col_index_num, 1                                    # col_index_num = col_index_num + 1
    jmp loop4

end4:
    #---------------------------------------------------------------------------------------------------把当前bank的所有latch清零
    set_col_bank_and_data_r col_bank_mask, col_index_init_reg
    #---------------------------------------------------------------------------------------------------当前所有列bank都遍历完了,就跳出循环,否则下一个bank
    bge_r col_bank_addr, col_bank_end_addr, end3                              # 如果col_bank_addr >= col_bank_end_addr，跳转到end3

    add_i col_bank_addr, col_bank_addr, 1                                    # col_bank_addr = col_bank_addr + 1
    add_i col_index_start_addr, col_index_start_addr, 1                      # 下一个列bank的起始读的列index的地址
    add_i col_index_end_addr, col_index_end_addr, 1                          # 下一个列bank的截止读的列index的地址
    jmp loop3

end3:
    #---------------------------------------------------------------------------------------------------当前行bank里面的所有行都遍历完了,就跳出循环,否则下一行
    bge_r row_index_num, row_end_index, end2                                  # 如果row_index_num >= row_end_index，跳转到end2
    add_i row_index_num, row_index_num, 1                                    # row_index_num, row_index_num + 1
    jmp loop2

end2:
    #---------------------------------------------------------------------------------------------------把当前bank的所有latch设置为初始状态
    set_row_bank_and_data_r row_bank_mask, row_index_init_reg
    #---------------------------------------------------------------------------------------------------当前所有行bank都遍历完了,就跳出循环,否则下一个行bank
    bge_r row_bank_addr, row_bank_end_addr, end1                              # 如果row_bank_addr >= row_bank_end_addr，跳转到end1

    add_i row_bank_addr, row_bank_addr, 1                                    # row_bank_addr = row_bank_addr + 1
    add_i row_index_start_addr, row_index_start_addr, 1                      # 下一个行bank的起始读的行index的地址
    add_i row_index_end_addr, row_index_end_addr, 1                          # 下一个行bank的截止读的行index的地址
    jmp loop1

end1:
    #---------------------------------------------------------------------------------------------------有数据才返回
    bge_r count,one,return_1
    jmp exit

return_1:
    add_i count,count,per_points_sub1
    srl return_len,count, per_ponts_num                               # return_len=return_len/32行
    return_dout return_len,zero ,pq
exit:
    add_i pq,zero,0
    row_read_rram_1ch_to_dout tia_mask,count,pq
    return_dout zero,zero ,pq
    exit              # 结束执行