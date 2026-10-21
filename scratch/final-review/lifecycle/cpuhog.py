import multiprocessing, sys, time, os
def spin(d):
    end = time.time() + d
    while time.time() < end:
        pass
if __name__ == "__main__":
    n, d = int(sys.argv[1]), float(sys.argv[2])
    open(sys.argv[3], "w").write(str(os.getpid()))
    ps = [multiprocessing.Process(target=spin, args=(d,)) for _ in range(n)]
    for p in ps: p.start()
    for p in ps: p.join()
