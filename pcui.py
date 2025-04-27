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
import tkinter.font as tkfont
import numpy as np
from PIL import Image, ImageTk

from network.hnn import hnn
from network.svm import svm
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Tkinter 界面示例")
        self.root.geometry("1000x800")

        # 存储生成的随机地址和转换结果
        self.generated_addresses = []
        self.chip = None
        self.connected = False
        self.default_font = tkfont.nametofont("TkDefaultFont").copy()
        self.default_font.configure(size=16)  # 修改默认字体大小、加粗
        
        self.create_layout()


        self.chip = CHIP(PS(host="192.168.1.10", port = 7, debug=0),init=True)
        self.connected = True
        self.chip.IsRERAM512 = True
        self.chip.setting.IsRERAM512 = True
        self.chip.set_device_cfg(deviceType=0)

        self.chip.set_op_mode(read=True, from_row=True)  # 设置为读模式, 并且是从行读
        self.chip.set_dac_read_V(0.11, tg=5)  # 设置读电压, 会根据device的自动配置对应的DAC通道
        self.chip.adc.set_gain_resistor(big_resistance=33e3, small_resistance=200)  # 设置TIA增益使用的电阻大小
        self.chip.set_tia_gain(1)  # 设置TIA的增益
        # print(self.chip.get_setting_info())
        self.chip.set_chip_sel(9)
        # self.chip.set_pulse_width(10e-3)
        self.chip.adc.set_gap(adc_cs_gap=200, adc_first_gap=100, adc_last_gap=10)
        self.chip.clk_manager.set_cyc(100, 100)

        self.chip.set_cim_reset()

        chip=CHIP(PS(host="192.168.1.11", port = 7, debug=0),init=True)
        chip.set_device_cfg(deviceType=0)
        chip.adc.set_gap(adc_cs_gap=100,adc_first_gap=20,adc_last_gap=10)
        chip.add_compiler("./code/")
        self.chip_task2=chip


    def create_layout(self):

        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)

        self.root.rowconfigure(0, weight=1)

        # 左侧主框架
        left_frame = ttk.Frame(self.root, width=250)
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

        self.create_svm_panel(right_frame)

        self.create_hnn_panel(right_frame)

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
        self.num_entry = ttk.Entry(addr_frame)
        self.num_entry.insert(0, "3")
        self.num_entry.grid(row=0, column=1, columnspan=2, sticky="we", padx=5, pady=2)

        # chip 范围
        ttk.Label(addr_frame, text="chip 范围:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.chip_min_entry = ttk.Entry(addr_frame, width=5)
        self.chip_min_entry.insert(0, "1")
        self.chip_min_entry.grid(row=1, column=1, padx=5, pady=2)
        self.chip_max_entry = ttk.Entry(addr_frame, width=5)
        self.chip_max_entry.insert(0, "18")
        self.chip_max_entry.grid(row=1, column=2, padx=5, pady=2)

        # row 范围
        ttk.Label(addr_frame, text="row 范围:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.row_min_entry = ttk.Entry(addr_frame, width=5)
        self.row_min_entry.insert(0, "1")
        self.row_min_entry.grid(row=2, column=1, padx=5, pady=2)
        self.row_max_entry = ttk.Entry(addr_frame, width=5)
        self.row_max_entry.insert(0, "256")
        self.row_max_entry.grid(row=2, column=2, padx=5, pady=2)

        # col 范围
        ttk.Label(addr_frame, text="col 范围:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.col_min_entry = ttk.Entry(addr_frame, width=5)
        self.col_min_entry.insert(0, "1")
        self.col_min_entry.grid(row=3, column=1, padx=5, pady=2)
        self.col_max_entry = ttk.Entry(addr_frame, width=5)
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

    # def create_task_panels(self, parent):
    #     # 任务1
    #     task1_frame = ttk.LabelFrame(parent, text="任务1", padding="10")
    #     task1_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    #
    #     task1_label = ttk.Label(task1_frame, text="任务1", anchor="center")
    #     task1_label.grid(row=0, column=0, pady=10, sticky="we", padx=5)
    #
    #     # 任务2
    #     task2_frame = ttk.LabelFrame(parent, text="任务2", padding="10")
    #     task2_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    #
    #     task2_label = ttk.Label(task2_frame, text="任务2", anchor="center")
    #     task2_label.grid(row=0, column=0, pady=10, sticky="we", padx=5)

    def get_img10x10(self):
        """生成一个随机的10x10黑白图像，值为0或1"""
        return np.random.randint(0, 2, size=(10, 10), dtype=np.uint8)

    def get_blank_image10x10(self):
        return np.ones((10, 10), dtype=np.uint8)  # 白色图像（全1）

    def array_to_photoimage(self, arr):
        """将10x10 numpy数组转换为可显示的PhotoImage"""
        # print("转换前：")
        # print(arr)
        arr1 = np.where(arr == -1, 0, 255)
        # print("转换后：")
        # print(arr1)
        # print(arr)
        img = Image.fromarray(arr1.astype('uint8'), mode='L')  # 'L' 表示灰度图，注意类型转换
        img = img.resize((70, 70), Image.NEAREST)  # 放大显示
        return ImageTk.PhotoImage(img)

    def set_hnn_origin_img(self):
        self.hnn = hnn()
        self.original_imgs = self.hnn.get_origin()
        # for index in range(5):
        #     original_img = self.get_img10x10()
        #     self.original_imgs.append(original_img)

    def start_noising(self):
        self.noisy_imgs = self.hnn.get_damaged()
        for index in range(len(self.original_imgs)):

            img = self.array_to_photoimage(self.noisy_imgs[index])

            # 更新 UI 需要回到主线程（Tkinter 线程不安全）
            def update_ui(i=index, im=img):
                label = self.noisy_labels[i]
                label.config(image=im, text="")
                label.image = im

            self.root.after(0, update_ui)  # 马上调 UI 更新
            
            def update_ui(i=index, im=img):
                label = self.restored_labels[i]
                label.config(image=im, text="")
                label.image = im
            
            self.root.after(0, update_ui)  # 马上调 UI 更新

    def start_restoration(self):
        for index,state in enumerate(self.noisy_imgs):
            state_flat = state.flatten()
            for _ in range(10):
                new_state = np.where(self.hnn.forward_from_row(self.chip_task2,state_flat) >= 0, 1, -1)
                if np.array_equal(new_state, state_flat):
                    break
                state_flat = new_state
                restored_img = state_flat.reshape((state.shape))

                self.restored_imgs.append(restored_img)

                img = self.array_to_photoimage(restored_img)

                # 更新 UI 需要回到主线程（Tkinter 线程不安全）
                def update_ui(i=index, im=img):
                    label = self.restored_labels[i]
                    label.config(image=im, text="")
                    label.image = im

                self.root.after(0, update_ui)  # 马上调 UI 更新

    def create_hnn_panel(self, parent):
        hnn_frame = ttk.LabelFrame(parent, text="任务1")
        hnn_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        title = ttk.Label(hnn_frame, text="HNN任务：图像恢复", font=self.default_font)
        title.pack(pady=5)

        self.original_imgs = []       # 原始图
        self.noisy_imgs = []        # 加噪图
        self.restored_imgs = []     # 恢复图
        self.noisy_labels = []      # 加噪图的Label引用
        self.restored_labels = []   # 恢复图的Label引用
        self.set_hnn_origin_img()   # 设置原始图像

        # 使用一个Frame容纳图片矩阵
        image_matrix = ttk.Frame(hnn_frame)
        image_matrix.pack()

        # 添加列标题（图1 ~ 图5）
        # for col in range(5):
        #     label = tk.Label(image_matrix, text=f"图{col + 1}", font=(self.default_font, 12), width=10)
        #     label.grid(row=0, column=col + 1, padx=2, pady=2)  # 放置在第一行

        # 添加行标题（原始图、加噪图、恢复图）
        row_titles = ["原始图", "加噪图", "恢复图"]
        for row in range(3):
            label = tk.Label(image_matrix, text=row_titles[row], font=(self.default_font, 12), width=10)
            label.grid(row=row, column=0, padx=2, pady=2)  # 放置在每一行的第一列


        blank_img = self.array_to_photoimage(self.get_blank_image10x10())
        # 显示原始图和加噪图
        for col in range(5):
            # print(self.original_imgs[col])
            origin_img = self.array_to_photoimage(self.original_imgs[col])

            label1 = tk.Label(image_matrix, image=origin_img, borderwidth=1, relief="solid")
            label1.image = origin_img
            label1.grid(row=0, column=col + 1, padx=15, pady=10)

            label2 = tk.Label(image_matrix, image=blank_img, borderwidth=1, relief="solid")
            label2.image = blank_img
            label2.grid(row=1, column=col + 1, padx=15, pady=10)
            self.noisy_labels.append(label2)

            label3 = tk.Label(image_matrix, image=blank_img, borderwidth=1, relief="solid")
            label3.image = blank_img
            label3.grid(row=2, column=col + 1, padx=15, pady=10)
            self.restored_labels.append(label3)

        # 按钮区域
        button_frame = ttk.Frame(hnn_frame)
        button_frame.pack(pady=10)

        # 新增：生成加噪图按钮
        noise_button = ttk.Button(button_frame, text="生成加噪图", command=self.start_noising_thread)
        noise_button.pack(side="left", padx=10)

        # 原有：执行恢复按钮
        restore_button = ttk.Button(button_frame, text="执行恢复", command=self.start_restoration_thread)
        restore_button.pack(side="left", padx=10)

    def start_noising_thread(self):
        t = threading.Thread(target=self.start_noising)
        t.start()

    def start_restoration_thread(self):
        t = threading.Thread(target=self.start_restoration)
        t.start()

    def create_svm_panel(self, parent):
        svm_frame = ttk.LabelFrame(parent, text="任务2")
        svm_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.set_svm_label()

        # 添加启动任务的按钮，放在accuracy_label的左边
        self.start_button = ttk.Button(svm_frame, text="开始任务", command=self.start_svm_thread)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 示例：添加准确率显示
        self.accuracy_label = ttk.Label(svm_frame, text="准确率：--%", font=self.default_font)
        self.accuracy_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 示例：分类结果表格
        self.result_tree = ttk.Treeview(svm_frame, columns=("id", "pred", "true", "correct"), show="headings")
        self.result_tree.heading("id", text="样本ID")
        self.result_tree.heading("pred", text="预测类别")
        self.result_tree.heading("true", text="真实类别")
        self.result_tree.heading("correct", text="是否正确")
        self.result_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        # 设置固定列宽
        self.result_tree.column("id", width=50, anchor="center")  # 设置 id 列宽为 50
        self.result_tree.column("pred", width=50, anchor="center")  # 设置 pred 列宽为 150
        self.result_tree.column("true", width=50, anchor="center")  # 设置 true 列宽为 150
        self.result_tree.column("correct", width=100, anchor="center")  # 设置 correct 列宽为 100

        # 调整 grid 配置，确保自适应父容器的大小
        svm_frame.grid_rowconfigure(1, weight=1)  # 使表格占满剩余的空间
        svm_frame.grid_columnconfigure(0, weight=1)  # 使第一列能够扩展
        svm_frame.grid_columnconfigure(1, weight=1)  # 使第二列能够扩展

    def start_svm_thread(self):
        # 启动线程调用下位机API
        threading.Thread(target=self.start_svm).start()

    def set_svm_label(self):
        self.svm = svm()
        # 100个标签
        self.svm_label = self.svm.get_correct_labels().reshape(100,1)

    def start_svm(self):
        # chip=CHIP(PS(host="192.168.1.11", port = 7, debug=0),init=True)
        # chip.set_device_cfg(deviceType=0)
        # chip.adc.set_gap(adc_cs_gap=100,adc_first_gap=20,adc_last_gap=10)
        # chip.add_compiler("./code/")
        # self.chip_task2=chip
        self.svm_predicted = self.svm.forward(self.chip_task2).reshape(100,1)

        def update_result_tree():
            correct_count = 0
            for i in range(len(self.svm_predicted)):
                # 获取每一行的实际标签和预测值
                true_label = self.svm_label[i][0]
                pred_label = self.svm_predicted[i][0]
                correct = "√" if true_label == pred_label else "×"
                # 插入表格
                self.result_tree.insert("", "end", values=(i + 1, pred_label, true_label, correct))
                if correct == "√":
                    correct_count += 1

            # 更新准确率
            accuracy = (correct_count / 100) * 100
            self.accuracy_label.config(text=f"准确率：{accuracy:.2f}%")

        # 在主线程更新表格
        self.root.after(0, update_result_tree)

    def connect_device(self):
        if (self.chip.ps.connected):
            self.log(f"网口连接成功:{self.chip.ps.host}:{self.chip.ps.port}，正在初始化")

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
            # v=self.chip.read_point3(row_num,row_num+1,col_num,col_num+1,read_voltage=0.1,tg=5,gain=1,from_row=True,out_type=0)
            # c=self.chip.voltage_to_cond(v)
            # r=self.chip.voltage_to_resistance
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
