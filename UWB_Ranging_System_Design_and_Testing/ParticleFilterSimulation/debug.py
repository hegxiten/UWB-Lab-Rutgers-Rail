
# ------------------------------------------------------------------------
# coding=utf-8
# ------------------------------------------------------------------------
#
#  Created by Martin J. Laubach on 2011-11-15
#  Modified by Zezhou Wang for UWB applications on 2021
# ------------------------------------------------------------------------

from typing import (Dict, List, Tuple, Set)

import paho.mqtt.client as mqtt
import json
from draw import *
from plot_3d import WorldProcessPlotter, NBWorldPlot
import random
import math
import numpy as np
from scipy.stats import multivariate_normal
import bisect

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import multiprocessing as mp
import time


AXIAL_NOISE, AXIAL_NOISE_LARGE=5,0.1
SPEED_NOISE=0.5
HEADING_NOISE, HEADING_RANGE = 10, [0, 360]
PITCH_NOISE, PITCH_RANGE = 10, [-90, 90]
Z_RANGE = [30,150]


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

if __name__ == "__main__":
    print(w_gauss_multi([162, 178, 336, 345],[162, 178, 336, 344], 15))