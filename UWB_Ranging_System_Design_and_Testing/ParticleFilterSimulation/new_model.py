import math
import numpy as np
from scipy.stats import multivariate_normal
import bisect


SIGMA = 5.5
MU = 10
def w_gauss(a, b, sigma):
    error = a - b
    sigma2 = sigma ** 2
    g = math.e ** -(error ** 2 / (2 * sigma2))
    return g

def w_combined_gauss(a, b, sigma, mu):
    error = a - b
    sigma2 = sigma ** 2
    f = 1 / (sigma * math.sqrt(2 * math.pi)) * math.e ** (-(error - mu)) + \
        l * math.e ** (- l* error) * ()
    

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