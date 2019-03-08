# """
# Runs libEnsemble with a simple uniform random sample on one instance of the GKLS
# problem. # Execute via the following command:

# mpiexec -np 4 python3 test_chwirut_uniform_sampling_one_residual_at_a_time.py

# """

from __future__ import division
from __future__ import absolute_import

from mpi4py import MPI # for libE communicator
import numpy as np
import copy

from libensemble.tests.regression_tests.support import save_libE_output

# Import libEnsemble main, sim_specs, gen_specs, alloc_specs, and persis_info
from libensemble.libE import libE
from libensemble.tests.regression_tests.support import chwirut_one_at_a_time_sim_specs as sim_specs
from libensemble.tests.regression_tests.support import uniform_random_sample_obj_components_gen_specs as gen_specs
from libensemble.tests.regression_tests.support import give_sim_work_first_pausing_alloc_specs as alloc_specs
from libensemble.tests.regression_tests.support import persis_info_3 as persis_info

persis_info_safe = copy.deepcopy(persis_info)

### Declare the run parameters/functions
m = 214
n = 3
max_sim_budget = 10*m

sim_specs['component_nan_frequency'] = 0.05

gen_specs['out'] += [('x',float,n),]
gen_specs['lb'] = -2*np.ones(n)
gen_specs['ub'] =  2*np.ones(n)
gen_specs['components'] = m

exit_criteria = {'sim_max': max_sim_budget, 'elapsed_wallclock_time': 300}

# Perform the run
H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria, persis_info, alloc_specs)
if MPI.COMM_WORLD.Get_rank() == 0:
    assert flag == 0

    save_libE_output(H,__file__)

# Perform the run with a much higher nan frequency
sim_specs['component_nan_frequency'] = 1
persis_info = copy.deepcopy(persis_info_safe) 
H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria, persis_info, alloc_specs)
if MPI.COMM_WORLD.Get_rank() == 0:
    assert flag == 0

# Perform the run but not stopping on NaNs
sim_specs['component_nan_frequency'] = 0.05
alloc_specs.pop('stop_on_NaNs')
persis_info = copy.deepcopy(persis_info_safe) 
H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria, persis_info, alloc_specs)
if MPI.COMM_WORLD.Get_rank() == 0:
    assert flag == 0

# Perform the run also not stopping on partial fvec evals
alloc_specs.pop('stop_partial_fvec_eval')
persis_info = copy.deepcopy(persis_info_safe) 
H, persis_info, flag = libE(sim_specs, gen_specs, exit_criteria, persis_info, alloc_specs)
if MPI.COMM_WORLD.Get_rank() == 0:
    assert flag == 0
