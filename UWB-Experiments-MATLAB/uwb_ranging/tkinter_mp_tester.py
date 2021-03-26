
# Test Code for Tkinter with threads
import tkinter as Tk
import multiprocessing
import time

class GuiApp(object):
   def __init__(self,q):
      self.root = Tk.Tk()
      self.root.geometry('300x100')
      self.text_wid = Tk.Text(self.root,height=100,width=100)
      self.text_wid.pack(expand=1,fill=Tk.BOTH)
      self.root.after(100,self.CheckQueuePoll,q)

   def CheckQueuePoll(self,c_queue):
      try:
         str = c_queue.get(0)
         self.text_wid.insert('end',str)
      except:
         pass
      finally:
         self.root.after(100, self.CheckQueuePoll, c_queue)

# Data Generator which will generate Data
def GenerateData(q):
   for i in range(10):
      print("Generating Some Data, Iteration %s" %(i))
      time.sleep(2)
      q.put("Some Data from iteration %s \n" %(i))


if __name__ == '__main__':
# Queue which will be used for storing Data

   q = multiprocessing.Queue()
   q.cancel_join_thread() # or else thread that puts data will not term
   gui = GuiApp(q)
   t1 = multiprocessing.Process(target=GenerateData,args=(q,))
   t1.start()
   gui.root.mainloop()

   t1.join()