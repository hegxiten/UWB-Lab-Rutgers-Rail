#!/usr/bin/env python3

import multiprocessing as mp
import queue
import time, os

from tkinter import *
from tkinter import ttk
from tkinter import font

from utils import timestamp_log, display_safety_ranging_results


BASE_WIDTH, BASE_HEIGHT = 1920, 1280
MIN_FONT_SIZE = 8


class RangingProcessPlotterGUI(object):
    def __init__(self, q):
        self.q = q

        if os.environ.get('DISPLAY','') == '':
            os.environ.__setitem__('DISPLAY', ':0.0')

        self.root = Tk()
        self.root.attributes("-fullscreen", True)
        self.root.configure(background='black')
        self.root.bind("<Escape>", self.quit)
        self.root.bind("x", self.quit)
        self.scr_width, self.scr_height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry("%dx%d+0+0" % (self.scr_width, self.scr_height))
        percent_width, percent_height = self.scr_width / (BASE_WIDTH / 100), self.scr_height / (BASE_HEIGHT / 100)
        self.scale_factor = (percent_width + percent_height) / 2 /100
        font_size = max(int(75 * self.scale_factor), MIN_FONT_SIZE)
        self.fnt = font.Font(family='Helvetica', size=font_size, weight='bold')

        self.a_end_txt, self.b_end_txt = StringVar(), StringVar()
        self.a_end_lbl = ttk.Label(self.root, textvariable=self.a_end_txt, font=self.fnt, foreground="green", background="black")
        self.b_end_lbl = ttk.Label(self.root, textvariable=self.b_end_txt, font=self.fnt, foreground="green", background="black")
        self.a_end_lbl.place(relx=0.05, rely=0.35, anchor=W)
        self.b_end_lbl.place(relx=0.05, rely=0.65, anchor=W)
        
        self.root.after(100, self.show_ranging_res, self.q)


    def quit(self, *args):
        self.root.destroy()

    def show_ranging_res(self, q):
        try:
            [a_end_ranging_res_ptr, b_end_ranging_res_ptr] = q.get(0)
            self.a_end_txt.set(display_safety_ranging_results(a_end_ranging_res_ptr[1], length_unit="METRIC"))
            self.b_end_txt.set(display_safety_ranging_results(b_end_ranging_res_ptr[1], length_unit="METRIC"))
        except queue.Empty:
            pass
        finally:
            q.empty()
            self.root.after(100, self.show_ranging_res, q)


def data_gen_process_job(q):
    cnt = 0
    while True:
        cnt+=1
        a_ptrs, b_ptrs = [{},[cnt]],[{},[cnt]]
        q.put([a_ptrs, b_ptrs])
        time.sleep(0.0005)


if __name__ == "__main__":
    import multiprocessing

    q = multiprocessing.Queue()
    q.cancel_join_thread()
    gui = RangingProcessPlotterGUI(q=q)

    end_ranging_process = multiprocessing.Process(target=data_gen_process_job, args=(q,),name="A End Ranging",daemon=True)
    end_ranging_process.start()

    gui.root.mainloop()

    end_ranging_process.join()