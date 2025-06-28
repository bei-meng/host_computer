; 常量初始化
MOV_i reg0, 26              ; reg0 = reg_cnn1_W_num
MOV_i reg1, 10               ; reg1 = reg_cnn1_H_num
MOV_i reg2, 25               ; reg2 = reg_cnn1_kernel_W_num
MOV_i reg3, 0                ; reg3 = reg_actv_din_start_addrb
MOV_i reg4, 400              ; reg4 = reg_actv_cnn1_start_addrb
MOV_i reg5, 6                ; reg5 = reg_cnn1_result_shifter1
MOV_i reg6, 1                ; reg6 = 常量1 (用于地址计算)
MOV_i reg7, 16               ; reg7 = 常量16 (地址步长)
MOV_i reg8, 3                ; reg8 = 常量3 (位平面循环次数)
MOV_i reg9, 5                ; reg9 = 常量5 (移位位数)
MOV_i reg10, 1               ; reg10 = 常量1 (循环增量)

; 主程序开始
set_adc_discard_nbits 0      ; 配置ADC
MOV_i reg11, 0               ; reg11 = reg_calc_layer_flg = 0
set_elewise_reg_2_shifter1 reg5 ; 设置移位器1

; 计算初始地址: reg_actv_ram_byte_addrb_cnn1 = reg4 << 6
MOV_i reg12, 6               ; 加载移位位数6
sll reg13, reg4, reg12       ; reg13 = reg4 << 6 (初始地址)

; 外层循环: cnn1_W_cnt (reg14)
MOV_i reg14, 0               ; reg14 = cnn1_W_cnt = 0
outer_loop_W:
    ; 计算循环边界: reg15 = reg0 - reg2 + 1
    sub reg15, reg0, reg2    ; reg15 = reg_cnn1_W_num - reg_cnn1_kernel_W_num
    add reg15, reg15, reg10  ; reg15 += 1
    CMP_r reg14, reg15       ; 比较 cnn1_W_cnt 和边界
    JGE exit_outer_loop_W    ; 若 >= 则跳出循环

    ; 内层循环: cnn1_H_cnt (reg16)
    MOV_i reg16, 0           ; reg16 = cnn1_H_cnt = 0
    inner_loop_H:
        CMP_r reg16, reg1    ; 比较 cnn1_H_cnt 和 reg_cnn1_H_num
        JGE exit_inner_loop_H ; 若 >= 则跳出循环

        reshape_buffer_clear ; 清空reshape buffer

        ; 输入数据循环: cnn1_kernel_W_cnt (reg17)
        MOV_i reg17, 0       ; reg17 = cnn1_kernel_W_cnt = 0
        kernel_loop:
            CMP_r reg17, reg2 ; 比较 kernel_cnt 和 reg_cnn1_kernel_W_num
            JGE exit_kernel_loop

            ; 计算地址: (cnn1_W_cnt + kernel_cnt)*32 + H_cnt + start_addr
            add reg18, reg14, reg17 ; reg18 = cnn1_W_cnt + kernel_cnt
            sll reg19, reg18, reg9  ; reg19 = (cnn1_W_cnt + kernel_cnt) << 5
            add reg20, reg19, reg16 ; reg20 += cnn1_H_cnt
            add reg21, reg20, reg3  ; reg21 += reg_actv_din_start_addrb

            set_actv_ram_addr reg21 ; 设置激活RAM地址
            load_actv_ram         ; 读取1字节数据到临时reg
            set_reshape_buffer_addr reg17 ; 设置reshape buffer地址
            store_reshape_buffer  ; 存储数据

            ; 循环递增: kernel_cnt++
            add reg17, reg17, reg10
            JMP kernel_loop
        exit_kernel_loop:

        ; 调用cal_block子函数 (参数在reg55)
        MOV_i reg55, 1       ; reg55 = reg_reshape_t_nbank = 1
        CALL cal_block

        ; 存储结果并更新地址
        set_actv_ram_addr reg13 ; 设置结果地址
        store_actv_ram_shifter1 ; 存储带移位的激活RAM
        set_elewise_adder_clear ; 清空加法器
        add reg13, reg13, reg7  ; 结果地址 += 16

        ; 内层循环递增: H_cnt++
        add reg16, reg16, reg10
        JMP inner_loop_H
    exit_inner_loop_H:

    ; 外层循环递增: W_cnt++
    add reg14, reg14, reg10
    JMP outer_loop_W
exit_outer_loop_W:

EXIT ; 程序结束

; =============== cal_block 子函数 (使用 reg55-reg63) ===============
cal_block:
    ; sign循环 (reg56)
    MOV_i reg56, 0           ; reg56 = sign = 0
    sign_loop:
        CMP_i reg56, 2       ; 比较 sign < 2
        JGE exit_sign_loop

        ; 设置乘法系数 (+1/-1)
        CMP_i reg56, 0
        JNE negative
        MOV_i reg62, 1       ; reg62 = +1
        JMP set_mul
    negative:
        MOV_i reg62, -1      ; reg62 = -1
    set_mul:
        set_elewise_reg_2_mul_B reg62 ; 设置乘法器

        ; 位平面循环 (reg57)
        MOV_i reg57, 0       ; reg57 = bit_plane_cnt = 0
        bit_loop:
            CMP_r reg57, reg8 ; 比较 bit_plane_cnt < 3
            JGE exit_bit_loop

            ; 设置移位器0
            set_elewise_reg_2_shifter0 reg57

            cim_reset        ; 重置CIM
            ; Word bank循环 (reg58)
            MOV_i reg58, 0   ; reg58 = bank_cnt = 0
            bank_loop:
                CMP_r reg58, reg55 ; 比较 bank_cnt < nbank
                JGE exit_bank_loop

                ; 计算地址: (bit_plane << 3) + bank_cnt
                MOV_i reg59, 3
                sll reg60, reg57, reg59 ; reg60 = bit_plane << 3
                add reg61, reg60, reg58 ; reg61 = 最终地址

                ; 加载reshape buffer数据
                load_reshape_buffer_t reg56, reg62, reg61 ; sign, data, addr
                ; 计算bank掩码: 1 << bank_cnt
                MOV_i reg63, 1
                sll reg59, reg63, reg58 ; reg59 = bank掩码

                ; 设置bank和数据
                set_row_bank_and_data_r reg59, reg62

                ; 检查是否为最后一次迭代
                sub reg60, reg55, reg63 ; nbank - 1
                CMP_r reg58, reg60
                JNE skip_read
                row_read_rram_32ch_to_diff ; 读取RRAM
                set_elewise_fast          ; 执行移位加法
            skip_read:

                ; bank循环递增
                add reg58, reg58, reg63
                JMP bank_loop
            exit_bank_loop:

            ; 位平面循环递增
            add reg57, reg57, reg63
            JMP bit_loop
        exit_bit_loop:

        ; sign循环递增
        add reg56, reg56, reg63
        JMP sign_loop
    exit_sign_loop:

    RET ; 子函数返回