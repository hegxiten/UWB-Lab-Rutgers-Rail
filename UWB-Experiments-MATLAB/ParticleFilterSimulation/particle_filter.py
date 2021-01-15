# ------------------------------------------------------------------------
# coding=utf-8
# ------------------------------------------------------------------------
#
#  Created by Martin J. Laubach on 2011-11-15
#  Modified by Zezhou Wang for UWB applications on 2021
# ------------------------------------------------------------------------

from __future__ import absolute_import

from typing import (Dict, List, Tuple, Set)

import random
import math
import bisect
import numpy as np
from scipy.stats import multivariate_normal
from draw import Maze
from plot_3d import ProcessPlotter, NBPlot
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import multiprocessing as mp

import time

# AXIAL_NOISE=0.02
# SPEED_NOISE=0.02
# HEADING_NOISE, HEADING_RANGE = 3, [0, 360]
# PITCH_NOISE, PITCH_RANGE= 10, [-90,90]
# Z_RANGE = [-5,5]
AXIAL_NOISE, AXIAL_NOISE_LARGE=5,0.1
SPEED_NOISE=0.5
HEADING_NOISE, HEADING_RANGE = 10, [0, 360]
PITCH_NOISE, PITCH_RANGE = 10, [-90, 90]
Z_RANGE = [30,150]
WEIGHT_CUT_OFF = 0.3
# ------------------------------------------------------------------------
# Some utility functions

def add_noise(level, range_lim=None, *coords):
    if len(coords)==1:
        if isinstance(coords[0], List):
            raw = [x + random.uniform(-level, level) for x in coords[0]]    
        else:
            raw = coords[0] + random.uniform(-level, level)
    else:
        raw = [x + random.uniform(-level, level) for x in coords]
    if not range_lim:
        return raw
    elif isinstance(raw, List):
        for x in raw:
            if x < range_lim[0]:
                x = range_lim[0]
            if x > range_lim[1]:
                x = range_lim[1]
    else:
        if raw < range_lim[0]:
            raw = range_lim[0]
        if raw > range_lim[1]:
            raw = range_lim[1]
    return raw

# This is just a gaussian kernel I pulled out of my hat, to transform
# values near to robbie's measurement => 1, further away => 0
SIGMA = 0.9
def w_gauss(a, b, sigma):
    error = a - b
    sigma2 = sigma ** 2
    g = math.e ** -(error ** 2 / (2 * sigma2))
    return g

# This is the 0-mean multivariate gaussian pdf value serves as the weight
# values near to robbie's measurement => 1, further away => 0
# the pdf value is not normalized
def w_gauss_multi(a: List, b: List, sigma: float) -> float:
    a_valid = [i for i in range(len(a)) if a[i] != float('inf')]
    b_valid = [i for i in range(len(b)) if b[i] != float('inf')]
    intersection_idx = [i for i in a_valid if i in b_valid]
    a = np.asarray([a[i] for i in intersection_idx])
    b = np.asarray([b[i] for i in intersection_idx])
    sigma2 = sigma ** 2
    dim = len(a)
    if dim > 0:
        error = (a - b)
        center = (a - a)
        error = error.reshape(1,dim)
        mean = np.zeros(dim, float)
        cov = np.zeros((dim,dim), float)
        np.fill_diagonal(cov, sigma2)
        center_pdf = multivariate_normal.pdf(x=center, mean=mean, cov=cov)
        g = multivariate_normal.pdf(x=error, mean=mean, cov=cov) / center_pdf
        return g

# ------------------------------------------------------------------------
def compute_mean_point(world, particles, dist_threshold=2):
    """
    Compute the mean for all particles that have a reasonably good weight.
    This is not part of the particle filter algorithm but rather an
    addition to show the "best belief" for current position.
    """

    m_x, m_y, m_z, m_count = 0, 0, 0, 0
    for p in particles:
        m_count += p.w
        m_x += p.x * p.w
        m_y += p.y * p.w
        m_z += p.z * p.w

    if m_count == 0:
        return -1, -1, -1, False

    m_x /= m_count
    m_y /= m_count
    m_z /= m_count

    # Now compute how good that mean is -- check how many particles
    # actually are in the immediate vicinity
    m_count = 0
    for p in particles:
        if world.euclidean_dist(p.x, p.y, p.z, m_x, m_y, m_z) < dist_threshold:
            m_count += 1

    return m_x, m_y, m_z, m_count > PARTICLE_COUNT * 0.95

# ------------------------------------------------------------------------
class WeightedDistribution(object):
    def __init__(self, state):
        accum = 0.0
        self.state = [p for p in state if p.w > 0]
        self.distribution = []
        for x in self.state:
            accum += x.w
            self.distribution.append(accum)

    def pick(self):
        try:
            uni = random.uniform(0, 1)
            idx = bisect.bisect_left(self.distribution, uni)
            picked_p = self.state[idx]
            return picked_p
        except IndexError:
            # Happens when all particles are improbable w=0
            return None

# ------------------------------------------------------------------------
class Particle(object):
    def __init__(self, x, y, z=0, xy_heading=None, pitch=None, w=1, noisy=False):
        if xy_heading is None:
            xy_heading = random.uniform(HEADING_RANGE[0], HEADING_RANGE[1])
        if pitch is None:
            pitch = 0
        if noisy:
            x, y, z = add_noise(AXIAL_NOISE, [], x, y, z)
            xy_heading = add_noise(HEADING_NOISE, HEADING_RANGE, xy_heading)
            pitch = 0

        self.x = x
        self.y = y
        self.z = z
        self.xy_heading = xy_heading
        self.pitch = pitch
        self.w = w

    def __repr__(self):
        return "(%f, %f, %f, w=%f)" % (self.x, self.y, self.z, self.w)

    @property
    def xy(self):
        return self.x, self.y

    @property
    def xyz(self):
        return self.x, self.y, self.z

    @classmethod
    def create_random_particles(cls, particle_count, maze):
        return [cls(*maze.random_free_place(z_range=Z_RANGE)) for _ in range(0, particle_count)]

    def read_nearest_sensor(self, maze):
        """
        Find distance to nearest beacon.
        """
        return maze.distance_to_nearest_beacon(*self.xy)
    
    def read_sensors(self, maze):
        """
        Find all distances to all available beacons.
        """
        return maze.distances_to_all_beacons(*self.xy)

    def advance_by(self, speed, delta_t=1, checker=None, noisy=False):
        if noisy:
            speed = add_noise(SPEED_NOISE, [], speed)
            xy_heading = add_noise(HEADING_NOISE, HEADING_RANGE, self.xy_heading)
            # self.pitch = add_noise(PITCH_NOISE, PITCH_RANGE, self.pitch)
        else:
            speed, xy_heading = speed, self.xy_heading
        xy_heading_r, pitch_r = math.radians(xy_heading), math.radians(self.pitch)
        speed_xy = math.cos(pitch_r) * speed
        dx = math.sin(xy_heading_r) * speed_xy * delta_t
        dy = math.cos(xy_heading_r) * speed_xy * delta_t
        dz = math.sin(pitch_r) * speed * delta_t
        if checker is None or checker(self, dx, dy, dz):
            self.move_by(dx, dy, dz)
            return True
        return False

    def move_by(self, x, y, z):
        self.x += x
        self.y += y
        self.z += z

# ------------------------------------------------------------------------
class Robot(Particle):
    speed = 0

    def __init__(self, maze):
        super(Robot, self).__init__(*maze.random_free_place(), xy_heading=90)
        self.chose_random_direction()
        self.step_count = 0

    def chose_random_direction(self):
        self.xy_heading = random.uniform(HEADING_RANGE[0], HEADING_RANGE[1])

    def read_nearest_sensor(self, maze, noise_level=AXIAL_NOISE):
        """
        Poor robot, it's sensors are noisy and pretty strange,
        it only can measure the distance to the nearest beacon(!)
        and is not very accurate at that too!
        """
        return add_noise(noise_level, super(Robot, self).read_nearest_sensor(maze))
    
    def read_sensors(self, maze, range_lim=[], noise_level=AXIAL_NOISE):
        """
        Returns the distances to all the sensors (beacons) in the same order as
        the way sensors are stored (maze.beacons). 
        -------------
        random_loss: True/False
            Simulate the randomized reading loss for some of the sensors (beacons)
        """
        return add_noise(noise_level, range_lim, super(Robot, self).read_sensors(maze))

    def move(self, maze, speed, delta_t):
        """
        Move the robot. Note that the movement is stochastic too.
        """
        self.step_count += 1
        while True:
            if self.advance_by(speed, delta_t=1, noisy=True,
                        checker=lambda r, dx, dy, dz: maze.is_free(r.x+dx, r.y+dy, r.z+dz)):
                break
            # Bumped into something or too long in same direction,
            # chose random new direction
            self.chose_random_direction()

# ------------------------------------------------------------------------
if __name__ == "__main__":
    PARTICLE_COUNT = 2000    # Total number of particles

    # create the particle filter maze world
    # anchor_list = [('00',0,0,0), ('01',9,0,0), ('02',9,9,0), ('03',0,9,0)] # no units
    anchor_list = [('C584',30,16,78), ('DA36',21,335,129), ('9234',295,278,81), ('8287',269,37,72)] # unit in cm
    maze_data = None

    ROBOT_HAS_COMPASS = False # Does the robot know where north is? If so, it
    # makes orientation a lot easier since it knows which direction it is facing.
    # If not -- and that is really fascinating -- the particle filter can work
    # out its xy_heading too, it just takes more particles and more time. Try this
    # with 3000+ particles, it obviously needs lots more hypotheses as a particle
    # now has to correctly match not only the position but also the xy_heading.
    RANDOM_LOSS = False
    PLOT_3D = True
    if PLOT_3D:
        world = Maze(maze_data, anc_list=anchor_list, turtle_init=False)
        pl = NBPlot(world)
    else:
        world = Maze(maze_data, anc_list=anchor_list, turtle_init=True, block_width=0.5)
    # initial distribution assigns each particle an equal probability
    particles = Particle.create_random_particles(PARTICLE_COUNT, world)
    robbie = Robot(world)
    while True:
        # To expand the dimensions, use multiple anchors, then we have multiple readings
        # for particles and adjust particle weights accordingly. 
        # Update particle weight according to how good every particle matches
        # robbie's sensor reading
        if not RANDOM_LOSS:
            r_ds = robbie.read_sensors(world)
            for p in particles:
                if world.is_free(*p.xyz, z_range=Z_RANGE):
                    p_ds = p.read_sensors(world)
                    new_weight = w_gauss_multi(r_ds, p_ds, SIGMA)
                    if new_weight is not None:
                        p.w = new_weight
                else:
                    p.w = 0
            chosen_idx = list(range(len(r_ds)))
            selected_anc = [anchor_list[i][0] for i in chosen_idx]
        else:
            r_ds = robbie.read_sensors(world)
            chosen_idx = random.sample(range(len(r_ds)), random.randint(0, len(r_ds)))
            selected_anc = [anchor_list[i][0] for i in chosen_idx]
            for i in chosen_idx:
                r_ds[i] = float('inf')
            for p in particles:
                if world.is_free(*p.xyz, z_range=Z_RANGE):
                    p_ds = p.read_sensors(world)
                    for i in chosen_idx:
                        p_ds[i] = float('inf')
                    new_weight = w_gauss_multi(r_ds, p_ds, SIGMA)
                    if new_weight is not None:
                        p.w = new_weight
                else:
                    p.w = 0
        # ---------- Try to find current best estimate for display ----------
        m_x, m_y, m_z, confidence_indicator = compute_mean_point(world, particles)
        # ---------- Show current state ----------
        if not PLOT_3D:
            world.draw(chosen_idx)
            world.show_particles(particles)
            world.show_mean(m_x, m_y, confidence_indicator)
            world.show_robot(robbie)
        else:
            if plt.get_backend() == "MacOSX":   # MacOS might require a different start method
                mp.set_start_method("forkserver")
            pl.plot(data=[selected_anc, robbie, particles, (m_x, m_y, m_z, confidence_indicator)])
        # ---------- Shuffle particles ----------
        new_particles = []

        # Normalise weights
        nu = sum(p.w for p in particles)
        if nu:
            for p in particles:
                p.w = p.w / nu
        print("min weight: {}, max weight: {}".format(min([p.w for p in particles]), max([p.w for p in particles])))
        picked, generated = [], []
        # create a weighted distribution, for fast picking
        dist = WeightedDistribution(particles)
        for _ in particles:
            p = dist.pick()
            if p is None:  # No pick b/c all totally improbable
                new_particle = Particle.create_random_particles(1, world)[0]
                generated.append(new_particle)
            else:
                new_particle = Particle(p.x, p.y, p.z,
                        xy_heading=robbie.xy_heading if ROBOT_HAS_COMPASS else p.xy_heading, 
                        noisy=True)
                picked.append(new_particle)
            new_particles.append(new_particle)

        particles = new_particles
        # print(r_ds, p_ds)
        print("Robot speed: {}, picked particle: {}, generated particle: {}"
                .format(robbie.speed, len(picked), len(generated)))
        # print(r_ds, p_ds)
        # print("Robot speed: {}, picked particle: {}, generated particle: {}"
        #         .format(robbie.speed, len(picked), len(generated)))
        print("particle x range: [{}-{}] y range: [{}-{}] z range: [{}-{}]"
                .format(round(min([p.x for p in particles]),2), round(max([p.x for p in particles]),2), 
                        round(min([p.y for p in particles]),2), round(max([p.y for p in particles]),2),
                        round(min([p.z for p in particles]),2), round(max([p.z for p in particles]),2)))
        print("particle x: {} y: {} z: {}"
                .format(round(m_x,2), round(m_y,2), round(m_z, 2)))
        print("robbie x: {}, y: {}, z: {}, pitch: {}".format(round(robbie.x,2), round(robbie.y, 2), round(robbie.z,2),round(robbie.pitch,2)))
        # ---------- Move things ----------
        old_xy_heading = robbie.xy_heading
        robbie.move(world, speed=robbie.speed, delta_t=1)
        d_h = robbie.xy_heading - old_xy_heading
        # Move particles according to my belief of movement (this may
        # be different than the real movement, but it's all I got)
        for p in particles:
            p.xy_heading += d_h # in case robot changed xy_heading, swirl particle xy_heading too
            p.advance_by(robbie.speed)
