#!/bin/python3

# -*- coding: utf-8 -*-
#==============================
#    Author: Elun Dai
#    Last modified: 2018-06-11 18:33
#    Filename: memory.py
#    Description:
#    
#=============================#
# https://www.supermemo.com/articles/stability.htm
import math
from settings import STABILITY

def Ret(s, t):
    """retrievability R:
    R = e^{-k*t/s}
    where
        t - time
        R - probability of recall at time t
        S - stability expressed by the inter-repetition interval that results in retrievability of 90% (i.e. R=0.9)
            i.e. at time t=S, retrievability is R=0.9
        k - constant independent of stability, k=ln(10/9)
        >usually, k = -0.10536051565782635, s = -6.0552, -k/s = -0.0174
    """
    R = math.e**(-0.10536051565782635 / s * t)
#     R2 = math.e**(-0.10536051565782635 / (10*s) * t)
#     return (R+R2)/2
    return R

def SInc(p, r, a=1.0):
    """stability increment
    arguements:
        p: probability of recall in the rth re-encounter
        r: the rth re-encounter
        a: learning rate
    """
    if not (p >= 0 and p <= 1):
        raise Exception('p should between 0 and 1')

    if r > 1:
        # both add 0.001 to avoid 0/0 error
        return ((1-(1-p)**(a * r/(r-1))) + 0.001) / (p + 0.001)
    else:
        return 1

def S(last_s, t, r, a=1.0, is_pass=True, s1=None):
    """get new stability
    arguements:
        last_s: the stability of the last re-encounter
        t: time
        r: the rth re-encounter
        is_pass: True or False, wheather pass the test
        s1: if failed the test, set S to s1
    """
    if is_pass:
        R = Ret(last_s, t)
        return last_s*SInc(R, r, a)
    else:
        if s1 is None:
            # read from settings
            s1 = STABILITY
        return s1

def S_list(s1, intervel):
    s = [s1]
    for i in range(len(intervel)):
        print(s[i], intervel[i], i+1)
        s.append(S(s[i], intervel[i], i+1))
    return s

intervel = [5, 20, 720, 1440, 2880, 10080, 2160]

def best_intervel(s1, p, n):
    s = [s1]
    intervel = []
    for i in range(n):
#         k = -0.10536051565782635
#         t = s[i] * math.log(p, math.e) / k
        t = s[i] * math.log(p, 0.9)
#         print(s[i], t, i+1)
        s.append(S(s[i], t, i+1, a=1.2))
        intervel.append(t)
    print(s)
    return intervel
