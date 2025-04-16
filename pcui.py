import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import random
import serial
import threading
import time

from modules import CHIP
from pc import PS

import tkinter as tk
from tkinter import ttk

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("神经形态芯片里程碑测试")
        self.root.geometry("1100x900")

        # 存储生成的随机地址和转换结果
        self.generated_addresses = []
        self.chip = None
        self.connected = False

        self.create_layout()

    def create_layout(self):

        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)

        self.root.rowconfigure(0, weight=1)

        # 左侧主框架
        left_frame = ttk.Frame(self.root, width=300)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_frame.grid_propagate(False)
        left_frame.rowconfigure(0, weight=1)  # 硬件连接板块
        left_frame.rowconfigure(1, weight=3)  # 地址生成板块
        left_frame.rowconfigure(2, weight=6)  # 读取结果板块
        left_frame.columnconfigure(0, weight=1)

        # 右侧主框架
        right_frame = ttk.Frame(self.root)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.rowconfigure(0, weight=1)  # 任务1
        right_frame.rowconfigure(1, weight=1)  # 任务2
        right_frame.columnconfigure(0, weight=1)

        # 1. 硬件连接板块
        self.create_connection_panel(left_frame)

        # 2. 地址生成板块
        self.create_address_panel(left_frame)

        # 3. 读取结果板块
        self.create_result_panel(left_frame)

        # 右边：任务1 & 任务2（占位）
        # 创建右边列（任务1，任务2）
        self.create_task_panels(right_frame)

    def create_connection_panel(self, parent):
        conn_frame = ttk.LabelFrame(parent, text="硬件连接")
        conn_frame.grid(row=0, column=0, sticky="nsew", pady=5)
        conn_frame.columnconfigure(1, weight=1)

        # IP 地址
        ttk.Label(conn_frame, text="IP 地址:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.ip_entry = ttk.Entry(conn_frame)
        self.ip_entry.insert(0, "192.168.1.10")
        self.ip_entry.grid(row=0, column=1, columnspan=2, sticky="we", padx=5, pady=2)

        # 端口号 + 按钮
        ttk.Label(conn_frame, text="端口号:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.port_entry = ttk.Entry(conn_frame)
        self.port_entry.insert(0, "7")
        self.port_entry.grid(row=1, column=1, sticky="we", padx=5, pady=2)

        connect_button = ttk.Button(conn_frame, text="连接", command=self.connect_device)
        connect_button.grid(row=1, column=2, padx=5)

    def create_address_panel(self, parent):
        addr_frame = ttk.LabelFrame(parent, text="地址生成")
        addr_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        for i in range(3):
            addr_frame.columnconfigure(i, weight=1)

        # 生成数量
        ttk.Label(addr_frame, text="生成数量:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.num_entry = ttk.Entry(addr_frame, width=10)
        self.num_entry.insert(0, "3")
        self.num_entry.grid(row=0, column=1, padx=5, pady=2)

        # chip 范围
        ttk.Label(addr_frame, text="chip 范围:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.chip_min_entry = ttk.Entry(addr_frame, width=10)
        self.chip_min_entry.insert(0, "1")
        self.chip_min_entry.grid(row=1, column=1, padx=5, pady=2)
        self.chip_max_entry = ttk.Entry(addr_frame, width=10)
        self.chip_max_entry.insert(0, "18")
        self.chip_max_entry.grid(row=1, column=2, padx=5, pady=2)

        # row 范围
        ttk.Label(addr_frame, text="row 范围:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.row_min_entry = ttk.Entry(addr_frame, width=10)
        self.row_min_entry.insert(0, "1")
        self.row_min_entry.grid(row=2, column=1, padx=5, pady=2)
        self.row_max_entry = ttk.Entry(addr_frame, width=10)
        self.row_max_entry.insert(0, "256")
        self.row_max_entry.grid(row=2, column=2, padx=5, pady=2)

        # col 范围
        ttk.Label(addr_frame, text="col 范围:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.col_min_entry = ttk.Entry(addr_frame, width=10)
        self.col_min_entry.insert(0, "1")
        self.col_min_entry.grid(row=3, column=1, padx=5, pady=2)
        self.col_max_entry = ttk.Entry(addr_frame, width=10)
        self.col_max_entry.insert(0, "256")
        self.col_max_entry.grid(row=3, column=2, padx=5, pady=2)

        # 按钮
        gen_btn = ttk.Button(addr_frame, text="生成随机地址", command=self.generate_random_addresses)
        gen_btn.grid(row=4, column=0, columnspan=3, sticky="we", padx=5, pady=5)

        read_random_btn = ttk.Button(addr_frame, text="读取随机地址对应的点", command=self.read_random_points)
        read_random_btn.grid(row=5, column=0, columnspan=3, sticky="we", padx=5, pady=5)

    def create_result_panel(self, parent):
        result_frame = ttk.LabelFrame(parent, text="读取结果")
        result_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(result_frame, wrap="word")
        self.output_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def create_task_panels(self, parent):
        # 任务1
        task1_frame = ttk.LabelFrame(parent, text="任务1", padding="10")
        task1_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        task1_label = ttk.Label(task1_frame, text="任务1", anchor="center")
        task1_label.grid(row=0, column=0, pady=10, sticky="we", padx=5)

        # 任务2
        task2_frame = ttk.LabelFrame(parent, text="任务2", padding="10")
        task2_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        task2_label = ttk.Label(task2_frame, text="任务2", anchor="center")
        task2_label.grid(row=0, column=0, pady=10, sticky="we", padx=5)

    def connect_device(self):
        self.chip = CHIP(PS(host=self.ip_entry.get(), port=int(self.port_entry.get()), delay=0.3, debug=0), init=True)
        if (self.chip.ps.connected):
            self.log(f"网口连接成功:{self.chip.ps.host}:{self.chip.ps.port}，正在初始化")
            self.connected = True

            self.chip.IsRERAM512 = True
            self.chip.setting.IsRERAM512 = True
            self.chip.set_device_cfg(deviceType=0)

            self.chip.set_op_mode(read=True, from_row=True)  # 设置为读模式, 并且是从行读
            self.chip.set_dac_read_V(0.11, tg=5)  # 设置读电压, 会根据device的自动配置对应的DAC通道
            self.chip.adc.set_gain_resistor(big_resistance=33e3, small_resistance=200)  # 设置TIA增益使用的电阻大小
            self.chip.set_tia_gain(1)  # 设置TIA的增益
            print(self.chip.get_setting_info())
            self.chip.set_chip_sel(9)
            self.chip.set_pulse_width(10e-3)
            self.chip.adc.set_gap(adc_cs_gap=600, adc_first_gap=100, adc_last_gap=10)
            self.chip.clk_manager.set_cyc(100, 100)

            self.chip.set_cim_reset()
            self.log("初始化完成")
        else:
            self.log(f"连接失败:{self.chip.ps.host}:{self.chip.ps.port}")

    def generate_random_addresses(self):
        # 获取输入值
        try:
            num = int(self.num_entry.get())
            chip_min = int(self.chip_min_entry.get())
            chip_max = int(self.chip_max_entry.get())
            row_min = int(self.row_min_entry.get())
            row_max = int(self.row_max_entry.get())
            col_min = int(self.col_min_entry.get())
            col_max = int(self.col_max_entry.get())
        except ValueError:
            self.log("请检查输入是否为有效数字。")
            return

        # 地址列表
        self.generated_addresses.clear()

        # 生成随机地址并显示结果
        for i in range(num):
            chip = random.randint(chip_min, chip_max)
            row = random.randint(row_min, row_max)
            col = random.randint(col_min, col_max)
            self.generated_addresses.append((chip, row, col))
            result = f"随机地址 {i + 1}: chip={chip}, row={row}, col={col}"
            self.log(result)

    def read_random_points(self):
        if not self.connected:
            self.log("网口未连接，读取失败")
            return
        if not self.generated_addresses:
            self.log("先生成随机地址再读取")
            return

        cnt_addresses = len(self.generated_addresses)
        self.log((f'读{cnt_addresses}个点：'))
        for i in range(cnt_addresses):
            chip_sel = self.generated_addresses[i][0]
            row_num = self.generated_addresses[i][1]
            col_num = self.generated_addresses[i][2]

            # 调用读的过程
            v, c, r = self.read_point(0.1, chip_sel, row_num, col_num)

            self.log(
                f'第{i + 1:>2}个点，chip={chip_sel:>2}, row={row_num:>3}, col={col_num:>3} 测试结果：{r:.3f} kΩ   {c:.3f} uS')

    def read_point(self, v_read, chip_sel, row, col):

        chip_sel -= 1  # 减1是因为上位机程序中的编号都是从零开始的
        row -= 1
        col -= 1

        self.chip.set_dac_read_V(v_read)
        self.chip.set_chip_sel(chip_sel)
        self.chip.set_cim_reset()

        self.chip.set_latch([row], row=True, value=None)
        self.chip.set_latch([col], row=False, value=None)

        # print(self.chip.setting.TIA_index_map(col,col=True))

        self.chip.generate_read_pulse()
        tia_num = self.chip.setting.TIA_index_map(col)

        # voltage = chip.get_tia_out([k for k in range(16)])
        # max_voltage = np.max(voltage)

        voltage = self.chip.get_tia_out([tia_num])
        cond = self.chip.voltage_to_cond(voltage=voltage[0])
        resistance = self.chip.voltage_to_resistance(voltage=voltage[0])
        if voltage < 0:
            voltage, cond, resistance = self.read_point_retry(tia_num)

        return voltage, cond, resistance

    def read_point_retry(self, tia_num):

        self.chip.set_tia_gain(2)
        self.chip.generate_read_pulse()
        voltage = self.chip.get_tia_out([tia_num])
        cond = self.chip.voltage_to_cond(voltage=voltage[0])
        resistance = self.chip.voltage_to_resistance(voltage=voltage[0])
        self.chip.set_tia_gain(1)
        return abs(voltage), abs(cond), abs(resistance)

    def log(self, message):
        self.output_text.insert(tk.END, message + "\n" + "-" * 20 + "\n")
        self.output_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
