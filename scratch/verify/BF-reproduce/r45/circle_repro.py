import sys, zendriver
from zendriver.core import util
print("zendriver from", zendriver.__file__)
f = lambda pts: [(round(a, 1), round(b, 1)) for a, b in pts]
print("circle(100, 0)  :", f(util.circle(100, 0, radius=10, num=4)))
print("circle(100, 1)  :", f(util.circle(100, 1, radius=10, num=4)))
print("circle(100, 50) :", f(util.circle(100, 50, radius=10, num=4)))
print("circle(100)     :", f(util.circle(100, radius=10, num=4)))
