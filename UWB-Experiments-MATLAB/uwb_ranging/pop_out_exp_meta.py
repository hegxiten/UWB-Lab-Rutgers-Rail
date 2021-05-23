import sys, os

import tkinter as tk
from tkinter import *
from tkinter import messagebox
from functools import partial
from utils import timestamp_log


class ExpMetaInfoCollectApp(tk.Toplevel):
    def __init__(self, root, log_fpath, exp_name):
        super().__init__(root)
        self.title('Experiment Meta Data')
        self.root = root
        self.log_fpath = log_fpath
        self.exp_name = exp_name
        self.geometry('500x500')
        self.bind("x", self.quit)
        self.protocol('WM_DELETE_WINDOW', self.quit)
        self.setupUI()

    def setupUI(self):
        l1 = Label(self, text="Experiment Title: ")
        l1.pack() # side can be assigned as LEFT  RTGHT TOP  BOTTOM
        l1_text = StringVar()
        l1_entry = Entry(self, textvariable = l1_text, width=100)
        l1_text.set("")
        l1_entry.pack()

        l2 = Label(self, text="Vehicle Number: ")
        l2.pack()  # side can be assigned as LEFT  RTGHT TOP  BOTTOM
        l2_text = StringVar()
        l2_entry = Entry(self, textvariable = l2_text, width=100)
        l2_text.set("")
        l2_entry.pack()

        l3 = Label(self, text="Movement Direction: ")
        l3.pack()  # side can be assigned as LEFT  RTGHT TOP  BOTTOM
        l3_text = StringVar()
        l3_entry = Entry(self, textvariable = l3_text, width=100)
        l3_text.set("")
        l3_entry.pack()

        l4 = Label(self, text="Additional Comments: ")
        l4.pack()  # side can be assigned as LEFT  RTGHT TOP  BOTTOM
        l4_text = StringVar()
        l4_entry = Entry(self, textvariable = l4_text, width=100)
        l4_text.set("")
        l4_entry.pack()
        
        b = Button(self, text="Save", command = partial(self.on_click, [(l1, l1_text), (l2, l2_text), (l3, l3_text), (l4, l4_text)])).pack()

    def on_click(self, label_entries):
        self.set_to_top()
        if sum([1 if e.get() else 0 for (_, e) in label_entries]) < 4:
            messagebox.showinfo(title='Warning', message = "Must complete all entries! Otherwise click 'X'")
            return
        meta_fname = self.exp_name + "-experiment_setup_meta.log"
        with open(os.path.join(self.log_fpath, meta_fname), "a", encoding="utf-8") as meta_log:
            meta_log.write(timestamp_log(incl_UTC=True) + " === UTC TIME REFERENCE === \n")
            for (l, l_txt) in label_entries:
                meta_log.write(l.cget("text"))
                meta_log.write(l_txt.get())
                meta_log.write("\n")
        sys.stdout.write(timestamp_log() + "Experiment {} Meta Data Saved to {}".format(self.exp_name, meta_fname))
        messagebox.showinfo(title='Confirmation', message = "Experiment {} Meta Data Saved to {}".format(self.exp_name, meta_fname))
        self.quit()

    def set_to_top(self):
        self.attributes('-topmost', True)
        self.update()

    def quit(self, *args):
        self.destroy()

if __name__ == '__main__':
    rt = Tk()
    app = ExpMetaInfoCollectApp(rt, "C:\\Users\\wangz\\uwb_ranging", "pop_up_window_test")
    app.set_to_top()
    rt.mainloop()