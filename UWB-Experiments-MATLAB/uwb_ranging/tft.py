#!/usr/bin/env python3
import multiprocessing as mp
import time

from tkinter import *
from tkinter import ttk
from tkinter import font

from utils import timestamp_log, display_safety_ranging_results


BASE_WIDTH, BASE_HEIGHT = 1920, 1280
MIN_FONT_SIZE = 8


class RangingProcessPlotterGUI(object):
    def __init__(self, queue):
        self.queue = queue

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
        
        self.root.after(100, self.show_ranging_res, self.queue)


    def quit(self, *args):
        self.root.destroy()

    def show_ranging_res(self, queue):
        try:
            [a_end_ranging_res_ptr, b_end_ranging_res_ptr] = queue.get(0)
            self.a_end_txt.set(display_safety_ranging_results(a_end_ranging_res_ptr, length_unit="METRIC", debug=True))
            self.b_end_txt.set(display_safety_ranging_results(b_end_ranging_res_ptr, length_unit="METRIC", debug=True))
        except BaseException as e:
            raise e
        finally:
            queue.empty()
            self.root.after(100, self.show_ranging_res, queue)


def data_gen_process_job(queue):
    while True:
        a_ptrs, b_ptrs = [{},[]],[{},[]]
        queue.put([a_ptrs, b_ptrs])
        time.sleep(0.0005)


if __name__ == "__main__":
    import multiprocessing

    q = multiprocessing.Queue()
    q.cancel_join_thread()
    gui = RangingProcessPlotterGUI(queue=q)

    end_ranging_process = multiprocessing.Process(target=data_gen_process_job, args=(q,),name="A End Ranging",daemon=True)
    end_ranging_process.start()

    gui.root.mainloop()

    end_ranging_process.join()