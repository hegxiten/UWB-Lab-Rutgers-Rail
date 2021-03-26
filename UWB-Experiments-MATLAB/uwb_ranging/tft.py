#!/usr/bin/env python3
import multiprocessing as mp
import time

from tkinter import *
from tkinter import ttk
from tkinter import font

from utils import timestamp_log, display_safety_ranging_results


BASE_WIDTH, BASE_HEIGHT = 1920, 1280
MIN_FONT_SIZE = 8


class RangingProcessPlotter(object):
    def __init__(self, **kwargs):
        self.root = Tk()
        self.root.attributes("-fullscreen", False)
        self.root.configure(background='black')
        self.root.bind("<Escape>", self.quit)
        self.root.bind("x", self.quit)
        self.scr_width, self.scr_height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry("%dx%d+0+0" % (self.scr_width, self.scr_height))
        percent_width, percent_height = self.scr_width / (BASE_WIDTH / 100), self.scr_height / (BASE_HEIGHT / 100)
        self.scale_factor = (percent_width + percent_height) / 2 /100
        font_size = max(int(55 * self.scale_factor), MIN_FONT_SIZE)
        self.fnt = font.Font(family='Helvetica', size=font_size, weight='bold')

        self.a_end_txt, self.b_end_txt = StringVar(), StringVar()
        self.a_end_lbl = ttk.Label(self.root, textvariable=self.a_end_txt, font=self.fnt, foreground="green", background="black")
        self.b_end_lbl = ttk.Label(self.root, textvariable=self.b_end_txt, font=self.fnt, foreground="green", background="black")
        self.a_end_lbl.place(relx=0.05, rely=0.35, anchor=W)
        self.b_end_lbl.place(relx=0.05, rely=0.65, anchor=W)
        
        self.a_end_ranging_res_ptr, self.b_end_ranging_res_ptr = [{},[]], [{},[]]


    def quit(self):
        self.root.destroy()

    def show_ranging_res(self):
        self.a_end_txt.set(display_safety_ranging_results(self.a_end_ranging_res_ptr[1], length_unit="METRIC"))
        self.b_end_txt.set(display_safety_ranging_results(self.b_end_ranging_res_ptr[1], length_unit="METRIC"))
        root.after(100, show_ranging_res)

    def ranging_process_display_call_back(self):
        """
        Define displaying actions within callback function. 
        Called regularly within self.__call__(conn)
        """
        while self.pipe_conn.poll():
            data_ptr = self.pipe_conn.recv()
            if data_ptr is None:
                self.terminate()
                return False
            else:
                [self.a_end_ranging_res_ptr, self.b_end_ranging_res_ptr] = data_ptr
        return True

    def __call__(self, pipe_conn):
        sys.stdout.write(timestamp_log() + "Tkinter display initialized.")
        self.pipe_conn = pipe_conn
        self.root.after(100, self.show_ranging_res)
        self.root.mainloop()


class NBRangingDisplayer(object):
    def __init__(self, **kwargs):
        self.displayer_pipe_parent_conn, displayer_child_conn = mp.Pipe()

        self.displayer_worker = RangingProcessPlotter(**kwargs)
        self.displayer_process = mp.Process(target=self.displayer_worker, args=(displayer_child_conn,), daemon=True)
        self.displayer_process.start()

    def display(self, data, finished=False):
        if finished:
            self.displayer_pipe_parent_conn.send(None)
        else:
            self.displayer_pipe_parent_conn.send(data)
