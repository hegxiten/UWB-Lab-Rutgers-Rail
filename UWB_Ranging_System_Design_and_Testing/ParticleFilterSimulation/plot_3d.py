import multiprocessing as mp
import time

import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
import numpy as np

# Fixing random state for reproducibility
np.random.seed(19680801)
DRAW_EVERY = 10

class WorldProcessPlotter(object):
    def __init__(self, **kwargs):
        self.world = kwargs.get('world', None)
    
    def terminate(self):
        plt.close('all')

    def weight_to_color(self, weight):
        return "#%02x00%02x" % (int(weight * 255), int((1 - weight) * 255))

    def world_plot_call_back(self):
        """
        Define plotting details and actions within callback function. 
        Called regularly within self.__call__(conn)
        """
        xlm=self.ax.get_xlim3d() #we use them in the next
        ylm=self.ax.get_ylim3d() #we use them in the next
        zlm=self.ax.get_zlim3d() #graph to reproduce the magnification from mousing
        while self.pipe_conn.poll():
            command = self.pipe_conn.recv()
            if command is None:
                self.terminate()
                return False
            else:
                self.ax.clear()
                [selected_anc, robbie, particles, (m_x, m_y, m_z, confidence_indicator)] = command
                self.ax.set_xlabel('X axis')
                self.ax.set_ylabel('Y axis')
                self.ax.set_zlabel('Z axis')
                if xlm != (0, 1.0): # (0,1.0) by default, avoid the default because we want the lim to be calculated automatically
                    self.ax.set_xlim3d(xlm[0], xlm[1])
                    self.ax.set_ylim3d(ylm[0], ylm[1])
                    self.ax.set_zlim3d(zlm[0], zlm[1])
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
                    if DRAW_EVERY == 0 or draw_cnt % DRAW_EVERY == 1:
                        self.ax.plot(p.x, p.y, p.z, 'o', color=self.weight_to_color(p.w))
                self.ax.plot(robbie.x, robbie.y, robbie.z, 'g*', markersize=20)
                self.fig.canvas.draw()
                xlm=self.ax.get_xlim3d() #These are two tupples
                ylm=self.ax.get_ylim3d() #we use them in the next
                zlm=self.ax.get_zlim3d() #graph to reproduce the magnification from mousing
                azm=self.ax.azim
                ele=self.ax.elev
        return True

    def __call__(self, pipe_conn):
        print('starting world plotter...')
        self.pipe_conn = pipe_conn
        self.fig = plt.figure(figsize=plt.figaspect(0.5))
        self.ax = p3.Axes3D(self.fig)
        timer = self.fig.canvas.new_timer(interval=1)
        timer.add_callback(self.world_plot_call_back)
        timer.start()

        print('world plotter started...')
        plt.show()


class StatsProcessPlotter(object):
    def __init__(self, **kwargs):
        pass
    
    def terminate(self):
        plt.close('all')

    def particle_stats_plot_call_back(self):
        """
        Define plotting details and actions within callback function. 
        Called regularly within self.__call__(conn)
        """
        while self.pipe_conn.poll():
            command = self.pipe_conn.recv()
            if command is None:
                self.terminate()
                return False
            else:
                self.ax.clear()
                [particles] = command
                weights = np.asarray([p.w for p in particles])
                n, bins, patches = self.ax.hist(weights, 50, facecolor='g', alpha=0.75)
                self.ax.set_xlabel('Weights')
                self.ax.set_ylabel('Amount of Particles')
                self.ax.set_title('Particle Distribution in Weights')
                self.ax.grid(True)
                self.fig.canvas.draw()

        return True
    
    def __call__(self, pipe_conn):
        print('starting stats plotter...')
        self.pipe_conn = pipe_conn
        self.fig, self.ax = plt.subplots(1, 1)
        timer = self.fig.canvas.new_timer(interval=1000)
        timer.add_callback(self.particle_stats_plot_call_back)
        timer.start()
        
        print('stats plotter started...')
        plt.show()


class NBWorldPlot(object):
    def __init__(self, **kwargs):
        self.world_plot_pipe_parent_conn, world_plotter_pipe_child_conn = mp.Pipe()
        
        self.world_plotter = WorldProcessPlotter(**kwargs)
        self.world_plot_process = mp.Process(
            target=self.world_plotter, args=(world_plotter_pipe_child_conn,), daemon=True)
        self.world_plot_process.start()

    def plot(self, data, finished=False):
        if finished:
            self.world_plot_pipe_parent_conn.send(None)
        else:
            self.world_plot_pipe_parent_conn.send(data)

class NBStatsPlot(object):
    def __init__(self, **kwargs):
        self.stats_plot_pipe_parent_conn, stats_plotter_pipe_child_conn = mp.Pipe()
        
        self.stats_plotter = StatsProcessPlotter(**kwargs)
        self.stats_plot_process = mp.Process(
            target=self.stats_plotter, args=(stats_plotter_pipe_child_conn,), daemon=True)
        self.stats_plot_process.start()

    def plot(self, data, finished=False):
        if finished:
            self.stats_plot_pipe_parent_conn.send(None)
        else:
            self.stats_plot_pipe_parent_conn.send(data)


def main():
    pl = NBWorldPlot()
    while True:
        pl.plot()
        # time.sleep(0.05)


if __name__ == '__main__':
    if plt.get_backend() == "MacOSX":
        mp.set_start_method("forkserver")
    main()