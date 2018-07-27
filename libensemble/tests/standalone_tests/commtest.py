"""Standalone comms test

Testing for message errors and correctness of data
"""

from __future__ import division
from __future__ import absolute_import

from mpi4py import MPI
import sys, os        
import numpy as np
import time

comm = MPI.COMM_WORLD
num_workers = MPI.COMM_WORLD.Get_size() - 1
rank = comm.Get_rank()
worker_ranks = set(range(1,MPI.COMM_WORLD.Get_size()))
rounds = 20
total_num_mess = rounds*num_workers

array_size = int(1e6)   # Size of large array in sim_specs

sim_specs = {'out': [
                     ('arr_vals',float,array_size),
                     ('scal_val',float), #Test if get error without this
                    ],
             }

start_time = time.time()

if rank == 0:
    print("Running comms test on {} processors with {} workers".format(MPI.COMM_WORLD.Get_size(),num_workers))
    #print("Hello from manager")
    status = MPI.Status()
    alldone = False
    mess_count = 0
    while not alldone:
        for w in worker_ranks:
            if comm.Iprobe(source=w, tag=MPI.ANY_TAG, status=status):
                D_recv = comm.recv(source=w, tag=MPI.ANY_TAG, status=status)
                mess_count += 1
                #To test values
                x = w * 1000.0
                assert np.all(D_recv['arr_vals'] == x), "Array values do not all match"
                assert D_recv['scal_val'] == x + x/1e7, "Scalar values do not all match"
        if mess_count >= total_num_mess:
            alldone = True

    print('Manager received and checked {} messages'.format(mess_count))        
    print('Manager finished in time', time.time() - start_time)
        
else:
    #print("Hello from worker", rank)
    output = np.zeros(1,dtype=sim_specs['out'])
    for x in range(rounds):
        x = rank * 1000.0
        output.fill(x)
        output['scal_val'] = x + x/1e7
        comm.send(obj=output, dest=0)
