#!/usr/bin/env python3

from tkinter import *
from tkinter import ttk
from tkinter import font
import time

def quit(*args):
	root.destroy()

def show_time():
	txt.set(time.strftime("%H:%M:%S"))
	root.after(1000, show_time)

root = Tk()
root.attributes("-fullscreen", True)
root.configure(background='black')
root.bind("<Escape>", quit)
root.bind("x", quit)
root.after(1000, show_time)
BASE_WIDTH, BASE_HEIGHT = 1920, 1280
scr_width, scr_height = root.winfo_screenwidth(), root.winfo_screenheight()
percent_width, percent_height = scr_width / (BASE_WIDTH / 100), scr_height / (BASE_HEIGHT / 100)
scale_factor = (percent_width + percent_height) / 2 /100
min_font_size = 8
font_size = max(int(55 * scale_factor), min_font_size)
fnt = font.Font(family='Helvetica', size=font_size, weight='bold')
txt = StringVar()
txt.set(time.strftime("%H:%M:%S"))
lbl = ttk.Label(root, textvariable=txt, font=fnt, foreground="green", background="black")
lbl.place(relx=0.5, rely=0.5, anchor=CENTER)

root.mainloop()