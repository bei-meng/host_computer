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

    #---------------------------------------------------------------------------------------------------要读的列bank号在din_ram存放的位置,以及右边界
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
    add_i per_ponts_num,zero,per_points_bit                                  # 每行能存多少个点
    #---------------------------------------------------------------------------------------------------存储当前是使用的哪一块dout_ram
    add_i pq, zero,pq_c

    # 逻辑：遍历 Column -> 遍历 Row
    
    #---------------------------------------------------------------------------------------------------初始化取列bank地址的起始和结束边界
    add_i col_bank_addr, zero, col_bank_din_ram_s_c                         
    add_i col_bank_end_addr, zero, col_bank_din_ram_e_c                     

    #---------------------------------------------------------------------------------------------------初始化取列index号地址的起始和结束边界
    add_i col_index_start_addr, zero, col_index_din_ram_s_c                  
    add_i col_index_end_addr, zero, col_index_din_ram_e_c                    

loop1: # 外层循环：遍历 列Bank (Col Bank)
    #---------------------------------------------------------------------------------------------------取列bank号, 生成列bank掩码
    load_din_ram_to_reg    col_bank_num, col_bank_addr                              
    sll     col_bank_mask, one, col_bank_num                                

    #---------------------------------------------------------------------------------------------------初始化列index号遍历的起始和结束边界
    load_din_ram_to_reg    col_index_num, col_index_start_addr                     
    load_din_ram_to_reg    col_end_index, col_index_end_addr                       

loop2: # 中层循环：遍历 列Index (Col Index) -> [TIA计算在这里完成]
    #---------------------------------------------------------------------------------------------------计算tia的base
    bge_r col_bank_num, four, tia_big4                                        

tia_nobig4:
    sll     tia_base, col_bank_num, two                                         
    jmp calc_tia_mask

tia_big4: 
    sll       tia_base, col_bank_num, two                                         
    add_i     tia_base,tia_base,1

calc_tia_mask:
    #---------------------------------------------------------------------------------------------------取列index号, 生成列index掩码
    add_i current_col_index_pos, col_index_num, col_index_pos 
    load_din_ram_to_reg col_index_mask, current_col_index_pos                                  
    set_col_bank_and_data_r col_bank_mask, col_index_mask                              

    #---------------------------------------------------------------------------------------------------计算tia,并设置tia_mask
    srl tia_offset, col_index_num, four
    sll tia_offset, tia_offset, one
    add_r tia_num, tia_base, tia_offset                                       
    sll tia_mask, one, tia_num                                                 

    #---------------------------------------------------------------------------------------------------[内层循环开始] 初始化行相关的寄存器
    # 初始化取行bank地址的起始和结束边界
    add_i row_bank_addr, zero, row_bank_din_ram_s_c                         
    add_i row_bank_end_addr, zero, row_bank_din_ram_e_c                     

    # 初始化取行index号地址的起始和结束边界
    add_i row_index_start_addr, zero, row_index_din_ram_s_c                  
    add_i row_index_end_addr, zero, row_index_din_ram_e_c                    

loop3: # 内层循环：遍历 行Bank (Row Bank)
    #---------------------------------------------------------------------------------------------------取行bank号, 生成行bank掩码
    load_din_ram_to_reg    row_bank_num, row_bank_addr                              
    sll     row_bank_mask, one, row_bank_num                                

    #---------------------------------------------------------------------------------------------------初始化行index号遍历的起始和结束边界
    load_din_ram_to_reg    row_index_num, row_index_start_addr                     
    load_din_ram_to_reg    row_end_index, row_index_end_addr                       

loop4: # 最内层循环：遍历 行Index (Row Index) -> [只做读取动作]
    #---------------------------------------------------------------------------------------------------取行index号, 生成行index掩码
    add_i current_row_index_pos, row_index_num, row_index_pos 
    load_din_ram_to_reg row_index_mask, current_row_index_pos                                  
    set_row_bank_and_data_r row_bank_mask, row_index_mask                              

    #---------------------------------------------------------------------------------------------------读取数据
    row_read_rram_1ch_to_dout tia_mask, count, pq
    
    #---------------------------------------------------------------------------------------------------控制返回的计数器
    add_i    count, count, 1                                                 
    bge_r     count, count_max, return_0                                      
    jmp   jmp_return_inner

return_0:
    add_i count,count,per_points_sub1
    srl return_len,count, per_ponts_num                               
    return_dout return_len,zero ,pq
    xor_i    pq, pq, 1                                                       
    add_i    count, zero, 0                                                  

jmp_return_inner:
    #---------------------------------------------------------------------------------------------------当前行bank里面的所有行都遍历完了
    bge_r row_index_num, row_end_index, end4                                  
    add_i row_index_num, row_index_num, 1                                    
    jmp loop4

end4:
    #---------------------------------------------------------------------------------------------------把当前行bank的所有latch清零
    set_row_bank_and_data_r row_bank_mask, row_index_init_reg
    #---------------------------------------------------------------------------------------------------下一个行bank
    bge_r row_bank_addr, row_bank_end_addr, end3                              

    add_i row_bank_addr, row_bank_addr, 1                                    
    add_i row_index_start_addr, row_index_start_addr, 1                      
    add_i row_index_end_addr, row_index_end_addr, 1                          
    jmp loop3

end3:
    #---------------------------------------------------------------------------------------------------[内层循环结束] 回到列循环
    # 当前列bank里面的所有列都遍历完了
    bge_r col_index_num, col_end_index, end2                                  
    add_i col_index_num, col_index_num, 1                                    
    jmp loop2

end2:
    #---------------------------------------------------------------------------------------------------把当前列bank的所有latch清零
    set_col_bank_and_data_r col_bank_mask, col_index_init_reg
    #---------------------------------------------------------------------------------------------------下一个列bank
    bge_r col_bank_addr, col_bank_end_addr, end1                              

    add_i col_bank_addr, col_bank_addr, 1                                    
    add_i col_index_start_addr, col_index_start_addr, 1                      
    add_i col_index_end_addr, col_index_end_addr, 1                          
    jmp loop1

end1:
    #---------------------------------------------------------------------------------------------------有数据才返回
    bge_r count,one,return_1
    jmp exit

return_1:
    add_i count,count,per_points_sub1
    srl return_len,count, per_ponts_num                               
    return_dout return_len,zero ,pq
exit:
    add_i pq,zero,0
    row_read_rram_1ch_to_dout tia_mask,count,pq 
    return_dout zero,zero ,pq
    exit              