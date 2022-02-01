import multiprocessing as mp
import time

import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
import numpy as np

# Fixing random state for reproducibility
np.random.seed(19680801)
class ProcessPlotter(object):
    def __init__(self, **kwargs):
        self.world = kwargs.get('world', None)
    
    def terminate(self):
        plt.close('all')

    def call_back(self):
        xlm=self.ax.get_xlim3d() 
        ylm=self.ax.get_ylim3d() 
        zlm=self.ax.get_zlim3d() 
        while self.pipe.poll():
            command = self.pipe.recv()
            if command is None:
                self.terminate()
                return False
            else:
                self.ax.clear()
                self.ax.set_xlabel('X axis')
                self.ax.set_ylabel('Y axis')
                self.ax.set_zlabel('Z axis')
                if xlm != (0, 1.0): # (0,1.0) by default, avoid the default because we want the lim to be calculated automatically
                    self.ax.set_xlim3d(xlm[0], xlm[1])
                    self.ax.set_ylim3d(ylm[0], ylm[1])
                    self.ax.set_zlim3d(zlm[0], zlm[1])
                [selected_anc, robbie, particles, (m_x, m_y, m_z, confidence_indicator)] = command
                # draw the beacons/anchors
                x, y, z, attr = [], [] ,[], []
                for i in range(len(self.world.beacons)):
                    x, y, z = self.world.beacons[i][1],self.world.beacons[i][2],self.world.beacons[i][3]
                    if self.world.beacons[i][0] in selected_anc:
                        self.ax.plot(x, y, z, 'go')
                    else:
                        self.ax.plot(x, y, z, 'ro')
                draw_cnt = 0
                for p in particles:
                    draw_cnt += 1
                    self.ax.plot(p.x, p.y, p.z, 'o', color=self.weight_to_color(p.w))
                self.ax.plot(robbie.x, robbie.y, robbie.z, 'g*', markersize=20)
                self.fig.canvas.draw()
                xlm=self.ax.get_xlim3d() #These are two tupples
                ylm=self.ax.get_ylim3d() #we use them in the next
                zlm=self.ax.get_zlim3d() #graph to reproduce the magnification from mousing
                azm=self.ax.azim
                ele=self.ax.elev
                
        return True

    def __call__(self, pipe):
        print('starting stats plotter...')

        self.pipe = pipe
        self.fig = plt.figure(figsize=plt.figaspect(0.5))
        self.ax = p3.Axes3D(self.fig)

        timer = self.fig.canvas.new_timer(interval=1000)
        timer.add_callback(self.call_back)
        timer.start()

        print('...done')
        plt.show()

class NBPlot(object):
    def __init__(self, **kwargs):
        self.plot_pipe, plotter_pipe = mp.Pipe()
        self.plotter = ProcessPlotter(**kwargs)
        self.plot_process = mp.Process(
            target=self.plotter, args=(plotter_pipe,), daemon=True)
        self.plot_process.start()

    def plot(self, data, finished=False):
        send = self.plot_pipe.send
        if finished:
            send(None)
        else:
            send(data)


def main():
    pl = NBPlot()
    while True:
        pl.plot()
        # time.sleep(0.05)


if __name__ == '__main__':
    if plt.get_backend() == "MacOSX":
        mp.set_start_method("forkserver")
    main()