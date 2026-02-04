_data_:
; set_row_ctrl_pulse_para
0               # 模式
1000            # delay
1000            # pulse width
; set_col_ctrl_pulse_para
0               # 模式
1000            # delay
1000            # pulse width
; set_tg_pulse_width
0               # 模式
1000            # delay
1000            # pulse width
; set_vin_row_pulse_para
0               # 模式
1000            # delay
1000            # pulse width
; set_vin_col_pulse_para
0               # 模式
1000            # delay
1000            # pulse width
; set_write_row_pulse_para
0               # 模式
1000            # delay
1000            # pulse width
; set_write_col_pulse_para
0               # 模式
1000            # delay
1000            # pulse width
; set_read_row_pulse_delay
1000            # pulse width
; set_read_col_pulse_delay
1000            # pulse width
; set_write

_main_:
# 配置对应的GPIO，
set_IO 0b00_0000_0001

# 使用前初始化寄存器
mov_i reg1,0
mov_i reg2,0
mov_i reg3,0
mov_i reg4,0
mov_i reg5,0

mov_i reg1,0
call load_data
set_row_ctrl_pulse_para reg5,reg4,reg3

mov_i reg1,3
call load_data
set_col_ctrl_pulse_para reg5,reg4,reg3

mov_i reg1,6
call load_data
set_tg_pulse_width_para reg5,reg4,reg3

mov_i reg1,9
call load_data
set_vin_row_pulse_para reg5,reg4,reg3

mov_i reg1,12
call load_data
set_vin_col_pulse_para reg5,reg4,reg3

mov_i reg1,15
call load_data
set_write_row_pulse_para reg5,reg4,reg3

mov_i reg1,18
call load_data
set_write_col_pulse_para reg5,reg4,reg3

mov_i reg1,21
load_din_ram_to_reg reg3,reg1
set_read_row_pulse_delay reg3

mov_i reg1,22
load_din_ram_to_reg reg3,reg1
set_read_col_pulse_delay reg3

set_write

exit


load_data:
    # 取数据
    load_din_ram_to_reg reg3,reg1           ; reg3 = din_ram[reg1]
    add_i reg1,reg1,1                        ; reg1++
    load_din_ram_to_reg reg4,reg1           ; reg4 = din_ram[reg1]
    add_i reg1,reg1,1                        ; reg1++
    load_din_ram_to_reg reg5,reg1           ; reg5 = din_ram[reg1]



