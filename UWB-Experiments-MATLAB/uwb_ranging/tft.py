#!/usr/bin/python3

import queue
import time, os, sys

from tkinter import *
from tkinter import ttk
from tkinter import font

from utils import *
try:
    from cam_record import *
except ModuleNotFoundError:
    pass

BASE_WIDTH, BASE_HEIGHT = 1920, 1280
MIN_FONT_SIZE = 8
BASE_WIDGET_WIDTH, BASE_WIDGET_HEIGHT = 100, 50
GRID_COLUMNS, GRID_ROWS = 5, 20
LIMIT_ALARM, LIMIT_WARNING = 3000, 10000


class ThreadWithRetValue(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, *, daemon=None):
        super().__init__(group=group, target=target, name=name,
                 args=args, kwargs=kwargs, daemon=daemon)
        self.ret_val = None
        
    def run(self):
        # Overriding the run method to acquire the return value
        try:
            if self._target is not None:
                self.ret_val = self._target(*self._args, **self._kwargs)
        finally:
            del self._target, self._args, self._kwargs

class RangingGUI(Frame):
    def __init__(self, q, root, parent=None, ranging_thread=None):
        super().__init__(parent, background="black")
        self.root = root
        self.parent = parent
        self.parent.configure(background='black')

        # Bind short cut keys
        self.root.bind("<Escape>", self.quit)
        self.root.bind("x", self.quit)
        
        # Calculate size and font
        self.root.attributes("-fullscreen", True)
        self.scr_width, self.scr_height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        _percent_width, _percent_height = self.scr_width / (BASE_WIDTH / 100), self.scr_height / (BASE_HEIGHT / 100)
        self.scale_factor = (_percent_width + _percent_height) / 2 /100
        self.ranging_fnt_size = max(int(75 * self.scale_factor), MIN_FONT_SIZE)
        self.ranging_fnt =  font.Font(family='Helvetica', size=int(self.ranging_fnt_size*1.0), weight='bold')
        self.time_fnt =     font.Font(family='Helvetica', size=int(self.ranging_fnt_size*0.4), weight='bold')
        self.button_fnt =   font.Font(family='Helvetica', size=int(self.ranging_fnt_size*0.5), weight='bold')

        # Grid config
        self.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        # TTK style config
        s = ttk.Style()
        s.configure('control.TButton',          font=self.button_fnt)
        s.configure('time.TLabel',              font=self.time_fnt,     foreground="green", background="black")
        s.configure('ranging_default.TLabel',   font=self.ranging_fnt,  foreground="gray",  background="black")
        s.configure('ranging_safe.TLabel',      font=self.ranging_fnt,  foreground="green", background="black")        
        s.configure('ranging_error.TLabel',     font=self.ranging_fnt,  foreground="blue",  background="black")
        s.configure('ranging_warn.TLabel',      font=self.ranging_fnt,  foreground="yellow",background="black")
        s.configure('ranging_alarm.TLabel',     font=self.ranging_fnt,  foreground="red",   background="black")
        s.configure('ranging_no_detection.TLabel',font=self.ranging_fnt,  foreground="orange", background="black")
        

        # Button init
        self.start_button = ttk.Button(self, text="Start", command=self.start_ranging, state="normal", style='control.TButton')
        self.start_button.grid(row=0, column=0, sticky=W)
        self.stop_button =  ttk.Button(self, text="Stop", command=self.stop_ranging, state="disabled", style='control.TButton')
        self.stop_button.grid(row=0, column=1, sticky=W)

        # Time Stamp Text init
        self.time_world_txt, self.time_start_txt = StringVar(), StringVar()
        self.time_world_lbl = ttk.Label(self, textvariable=self.time_world_txt, style='time.TLabel').grid(row=1, column=0, sticky=W)
        self.time_start_lbl = ttk.Label(self, textvariable=self.time_start_txt, style='time.TLabel').grid(row=2, column=0, sticky=W)
        
        # Status Report Text init
        self.info_txt = StringVar()
        self.info_txt_lbl = ttk.Label(self, textvariable=self.info_txt, style='time.TLabel').grid(row=3, column=0, sticky=W)

        # Reporting Text init
        self.a_end_txt, self.b_end_txt = StringVar(), StringVar()
        self.a_end_lbl = ttk.Label(parent, textvariable=self.a_end_txt, style='ranging_default.TLabel')
        self.a_end_lbl.place(relx=0.05, rely=0.45, anchor=W)
        self.b_end_lbl = ttk.Label(parent, textvariable=self.b_end_txt, style='ranging_default.TLabel')
        self.b_end_lbl.place(relx=0.05, rely=0.75, anchor=W)
        
        # Operation status init
        self.started = False
        self.start_button.state(["!disabled"])
        self.stop_button.state(["disabled"])
        self.start_time = None

        # Start the clock
        self.clock_thread = threading.Thread(target=self.show_time_stamp_thread_job, name="Clock Thread", daemon=True)
        self.clock_thread.start()

        # UWB parameters
        self.q = q
        self.ranging_thread = ranging_thread
        self.video_thread = None
        self.serial_ports = {}

        # Camera parameters
        self.video_recorder, self.audio_recorder = None, None

    
    def is_serial_port_ready(self):
        if len(self.serial_ports) == 4:
            return True
        return False


    def show_time_stamp_thread_job(self):
        while True:
            self.time_world_txt.set("Time: " + timestamp_log(brackets=False))
            if self.start_time is None:
                self.time_start_txt.set("Time elapsed from start: N/A")
            else:
                self.time_start_txt.set("Time elapsed from start: " + str(round(time.time() - self.start_time, 6)))
            time.sleep(0.1)

    def quit(self, *args):
        sys.stdout.write(timestamp_log() + "Process killed manually by exiting the GUI.\n")
        self.stop_ranging()
        time.sleep(0.5)
        self.destroy()
        sys.exit()

    def start_ranging(self):
        self.experiment_name = timestamp_log(shorten=True)
        if self.started == True:
            self.start_button.state(["disabled"])
            return
        
        self.started = True
        self.start_time = time.time()
        self.start_button.state(["disabled"])
        self.stop_button.state(["!disabled"])
        
        if len(self.serial_ports) < 4:
            for (dev, dev_dict) in self.serial_ports.items():
                try: 
                    dev_dict.get("port").close()
                except: 
                    continue
            self.uwb_init_thread = ThreadWithRetValue(  target=pairing_uwb_ports, 
                                                        kwargs={"oem_firmware": False, 
                                                                "init_reporting": True, 
                                                                "serial_ports_dict": self.serial_ports,
                                                                "stop_flag_callback": lambda: not self.started,
                                                                "ui_txt": self.info_txt},
                                                        name="UWB Serial Port Init Thread",
                                                        daemon=True)
            self.uwb_init_thread.start()

        if not self.ranging_thread:
            self.ranging_thread = threading.Thread( target=end_ranging_job, 
                                                    kwargs={"serial_ports": self.serial_ports, 
                                                            "data_ptrs_queue": self.q,
                                                            "stop_flag_callback": lambda: not self.started,
                                                            "oem_firmware": False,
                                                            "exp_name": self.experiment_name},
                                                    name="End Reporting Thread")
            self.ranging_thread.start()
        elif not self.ranging_thread.is_alive():
            self.ranging_thread = threading.Thread( target=end_ranging_job, 
                                                    kwargs={"serial_ports": self.serial_ports, 
                                                            "data_ptrs_queue": self.q,
                                                            "stop_flag_callback": lambda: not self.started,
                                                            "oem_firmware": False,
                                                            "exp_name": self.experiment_name},
                                                    name="End Reporting Thread")
            self.ranging_thread.start()
        
        try:
            self.vid_f_name = "vid-" + self.experiment_name
            self.video_recorder, self.audio_recorder = VideoRecorder(fname=self.vid_f_name), AudioRecorder(fname=self.vid_f_name)
        except BaseException as e:
            raise e
            self.video_recorder, self.audio_recorder = None, None

        if self.video_recorder is not None and self.audio_recorder is not None:
            start_AVrecording(self.video_recorder, self.audio_recorder, self.vid_f_name)
            
        self.after(100, self.show_ranging_res, self.q)
        

    def stop_ranging(self):
        if self.started == False:
            self.stop_button.state(["disabled"])
            return
        self.started = False
        self.start_time = None
        self.stop_button.state(["disabled"])
        if self.video_recorder is not None and self.audio_recorder is not None:
            stop_AVrecording(self.video_recorder, self.audio_recorder, self.vid_f_name, muxing=True)
            self.video_recorder, self.audio_recorder = None, None
        if self.uwb_init_thread:
            self.uwb_init_thread.join()
        if self.ranging_thread:
            self.ranging_thread.join()
        if self.video_thread:
            self.video_thread.join()
        self.start_button.state(["!disabled"])


    def show_ranging_res(self, q):
        try:
            [a_end_ranging_res_ptr, b_end_ranging_res_ptr] = q.get(block=False)
            a_txt_to_show, a_flag = display_safety_ranging_results(a_end_ranging_res_ptr[1], length_unit="METRIC")
            b_txt_to_show, b_flag = display_safety_ranging_results(b_end_ranging_res_ptr[1], length_unit="METRIC")
            self.a_end_txt.set(a_txt_to_show)
            self.configure_ui_by_ranging_res(self.a_end_lbl, a_flag)
            self.b_end_txt.set(b_txt_to_show)
            self.configure_ui_by_ranging_res(self.b_end_lbl, b_flag)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.show_ranging_res, q)
    

    def configure_ui_by_ranging_res(self, label_ui, range_flag):
        if range_flag < 0:
            if range_flag == -1:
                label_ui.configure(style='ranging_default.TLabel')
            if range_flag == -2:
                label_ui.configure(style='ranging_no_detection.TLabel')
            if range_flag == -3:
                label_ui.configure(style='ranging_no_error.TLabel')
        elif 0 < range_flag < LIMIT_ALARM:
            label_ui.configure(style='ranging_alarm.TLabel')
        elif LIMIT_ALARM < range_flag < LIMIT_WARNING:
            label_ui.configure(style='ranging_warn.TLabel')
        elif range_flag > LIMIT_WARNING:
            label_ui.configure(style='ranging_safe.TLabel')



if __name__ == "__main__":
    # Unit Testing
    gui_root = Tk()

    import threading
    def data_gen_job(q):
        cnt = 0
        while True:
            a_ptrs, b_ptrs = [{},[]],[{},[]]
            q.put([a_ptrs, b_ptrs])
            time.sleep(0.0005)
    q = queue.Queue()
    
    end_ranging_thread_test = threading.Thread(
        target=data_gen_job, 
        args=(q,),
        name="A End Ranging",
        daemon=True)
    gui = RangingGUI(q=q, root=gui_root, parent=gui_root)

    gui.mainloop()

    end_ranging_thread_test.join()