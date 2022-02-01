# ------------------------------------------------------------------------
# coding=utf-8
# ------------------------------------------------------------------------
#
#  Created by Martin J. Laubach on 2011-11-15
#
# ------------------------------------------------------------------------

import math
import turtle

import random
import time

from typing import (Dict, List, Tuple, Set)

UPDATE_EVERY = 0
DRAW_EVERY = 0
# maze_data = (   ( 3, 0, 0, 0, 0, 0, 0, 0, 0, 3 ),
#                 ( 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ),
#                 ( 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ),
#                 ( 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ),
#                 ( 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ),
#                 ( 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ),
#                 ( 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ),
#                 ( 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ),
#                 ( 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ),
#                 ( 3, 0, 0, 0, 0, 0, 0, 0, 0, 3 ))

class Maze(object):
    def __init__(self, maze_matrix, anc_list=None, block_width=5, turtle_init=True):
        self.block_witdh = block_width
        self.blocks = []
        for anc in anc_list:
            self.blocks.append((anc[1]-self.block_witdh/2, anc[2]-self.block_witdh/2))
        self.update_cnt = 0
        self.beacons = []
        self.maze = None
        self.anchor_x_list = [anc[1] for anc in anc_list]
        self.anchor_y_list = [anc[2] for anc in anc_list]
        self.anchor_z_list = [anc[3] for anc in anc_list]
        self.length = max(self.anchor_x_list) - min(self.anchor_x_list)
        self.width = max(self.anchor_y_list) - min(self.anchor_y_list)
        self.height = max(self.anchor_z_list) - min(self.anchor_z_list)
        self.beacons = anc_list
        
        if turtle_init:
            turtle.tracer(0, delay=0)
            turtle.register_shape("dot", ((-3,-3), (-3,3), (3,3), (3,-3)))
            turtle.register_shape("tri", ((-3, -2), (0, 3), (3, -2), (0, 0)))
            turtle.speed(10)
            turtle.setworldcoordinates(0, 0, 500, 500)
            turtle.title("Poor robbie is lost")
            turtle.setworldcoordinates(0, 0, self.length, self.width)
            self.one_px = float(turtle.window_width()) / float(self.length) / 0.002
            
    def draw(self, selected_beacons):
        # draw the blocks of the maze
        turtle.color("#000000")
        for x, y in self.blocks:
            turtle.up()
            turtle.setposition(x, y)
            turtle.down()
            turtle.setheading(90)
            turtle.begin_fill()
            for _ in range(0, 4):
                turtle.fd(self.block_witdh)
                turtle.right(90)
            turtle.end_fill()
            turtle.up()

        # draw the beacons/anchorsc
        for i in range(len(self.beacons)):
            x, y = self.beacons[i][1],self.beacons[i][2]
            turtle.setposition(x, y)
            if self.beacons[i][0] in selected_beacons:
                turtle.dot(8, 'white')
            else:
                turtle.dot(8, 'red')
        turtle.stamp()

    def weight_to_color(self, weight):
        return "#%02x00%02x" % (int(weight * 255), int((1 - weight) * 255))

    def is_in(self, x, y, z=None, **kwargs):
        if x < min(self.anchor_x_list) \
        or x > max(self.anchor_x_list) \
        or y < min(self.anchor_y_list) \
        or y > max(self.anchor_y_list):
            if kwargs.get('z_range', None) is None:
                pass
            else:
                if z > kwargs.get('z_range')[1] \
                or z < kwargs.get('z_range')[0]:
                    return False
        return True

    def is_free(self, x, y, z=None, **kwargs):
        if not z:
            z = min(self.anchor_z_list)
        if not self.is_in(x, y, z, **kwargs):
            return False
        
        yy = self.width - int(y) - 1
        xx = int(x)
        if self.maze:
            return self.maze[yy][xx] == 0
        return True

        # 0 - empty square
        # 1 - occupied square
        # 2 - occupied square with a beacon at each corner, detectable by the robot
        # 3 - occupied square with a beacon at the sensor, detectable by the robot

    def show_mean(self, x, y, z=None, confident=False):
        if confident:
            turtle.color("#00AA00")
        else:
            turtle.color("#cccccc")
        turtle.setposition(x, y)
        turtle.shape("circle")
        turtle.stamp()

    def show_particles(self, particles):
        self.update_cnt += 1
        if UPDATE_EVERY > 0 and self.update_cnt % UPDATE_EVERY != 1:
            return

        turtle.clearstamps()
        turtle.shape('tri')

        draw_cnt = 0
        px = {}
        for p in particles:
            draw_cnt += 1
            if DRAW_EVERY == 0 or draw_cnt % DRAW_EVERY == 1:
                # Keep track of which positions already have something
                # drawn to speed up display rendering
                scaled_x = int(p.x * self.one_px)
                scaled_y = int(p.y * self.one_px)
                scaled_xy = scaled_x * 10000 + scaled_y
                if not scaled_xy in px:
                    px[scaled_xy] = 1
                    turtle.setposition(*p.xy)
                    turtle.setheading(90 - p.xy_heading)
                    turtle.color(self.weight_to_color(p.w))
                    turtle.stamp()

    def show_robot(self, robot):
        turtle.color("green")
        turtle.shape('turtle')
        turtle.setposition(*robot.xy)
        turtle.setheading(90 - robot.xy_heading)
        turtle.stamp()
        turtle.update()

    def random_place(self, **kwargs):
        x = random.uniform(min(self.anchor_x_list), max(self.anchor_x_list))
        y = random.uniform(min(self.anchor_y_list), max(self.anchor_y_list))
        if kwargs.get('z_range', None) is None:
            z = 0
        else:
            z = random.uniform(min(kwargs.get('z_range')), max(kwargs.get('z_range')))
        return x, y, z

    def random_free_place(self, **kwargs):
        while True:
            x, y, z = self.random_place(**kwargs)
            if self.is_free(x, y, z, **kwargs):
                return x, y, z

    def euclidean_dist(self, x1, y1, z1, x2, y2, z2):
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)

    def euclidean_dist_xy(self, x1, y1, x2, y2):
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
        
    #  ---------------only for simulation, no Z-axis involved-------
    def distance_to_nearest_beacon(self, x, y, z=0) -> float:
        d = float('inf')
        for i in range(len(self.beacons)):
            c_x, c_y, c_z = self.beacons[i][1], self.beacons[i][2], self.beacons[i][3]
            distance = self.euclidean_dist(c_x, c_y, c_z, x, y, z)
            if distance < d:
                d = distance
                d_x, d_y, d_z = c_x, c_y, c_z
        return d
    
    def distances_to_all_beacons(self, x, y, z=0) -> Tuple:
        dist = []
        for i in range(len(self.beacons)):
            c_x, c_y, c_z = self.beacons[i][1], self.beacons[i][2], self.beacons[i][3]
            dist.append(self.euclidean_dist(c_x, c_y, c_z, x, y, z))
        return dist
