from __future__ import division
from __future__ import absolute_import
import numpy as np
import sys, os

#sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))
from libensemble.message_numbers import EVAL_SIM_TAG 
from libensemble.message_numbers import EVAL_GEN_TAG 

#sys.path.append(os.path.join(os.path.dirname(__file__), '../../examples/gen_funcs'))
from libensemble.gen_funcs.aposmm import initialize_APOSMM, decide_where_to_start_localopt, update_history_dist

def start_persistent_local_opt_gens(W, H, sim_specs, gen_specs, persis_info):
    """ 
    This allocation function will:
    
    - Start up a persistent generator that is a local opt run at the first point
      identified by APOSMM's decide_where_to_start_localopt.
    - It will only do this if at least one worker will be left to perform
      simulation evaluations.
    - If multiple starting points are available, the one with smallest function
      value is chosen. 
    - If no candidate starting points exist, points from existing runs will be
      evaluated (oldest first)
    - If no points are left, call the gen_f

        /libensemble/tests/regression_tests/test_6-hump_camel_uniform_sampling_with_persistent_localopt_gens.py
    
    """

    Work = {}
    gen_count = 0
    already_in_Work = np.zeros(len(H),dtype=bool) # To mark points as they are included in Work, but not yet marked as 'given' in H.

    # If a persistent localopt run has just finished, use run_order to update H
    # and then remove other information from persis_info
    for i in persis_info.keys():
        if 'done' in persis_info[i]:
            H['num_active_runs'][persis_info[i]['run_order']] -= 1
        if 'x_opt' in persis_info[i]:
            opt_ind = np.all(H['x']==persis_info[i]['x_opt'],axis=1)
            assert sum(opt_ind) == 1, "There must be just one optimum"
            H['local_min'][opt_ind] = True
            persis_info[i] = {'rand_stream': persis_info[i]['rand_stream']}

    # If i is idle, but in persistent mode, and its calculated values have
    # returned, give them back to i. Otherwise, give nothing to i
    for i in W['worker_id'][np.logical_and(W['active']==0,W['persis_state']!=0)]:
        gen_inds = H['gen_worker']==i 
        if np.all(H['returned'][gen_inds]):
            last_ind = np.nonzero(gen_inds)[0][np.argmax(H['given_time'][gen_inds])]
            Work[i] = {'persis_info':persis_info[i],
                       'H_fields': sim_specs['in'] + [name[0] for name in sim_specs['out']],
                       'tag':EVAL_GEN_TAG, 
                       'libE_info': {'H_rows': np.atleast_1d(last_ind),
                                     'persistent': True
                                }
                       }
            persis_info[i]['run_order'].append(last_ind)

    for i in W['worker_id'][np.logical_and(W['active']==0,W['persis_state']==0)]:
        # Find candidate points for starting local opt runs if a sample point has been evaluated
        if np.any(np.logical_and(~H['local_pt'],H['returned'])):
            n, n_s, c_flag, _, rk_const, lhs_divisions, mu, nu = initialize_APOSMM(H, gen_specs)
            update_history_dist(H, gen_specs, c_flag=False)
            starting_inds = decide_where_to_start_localopt(H, n_s, rk_const, lhs_divisions, mu, nu)        
        else:
            starting_inds = []

        # Start up a persistent generator that is a local opt run but don't do it if all workers will be persistent generators.
        if len(starting_inds) and gen_count + sum(W['persis_state']==EVAL_GEN_TAG) + 1 < len(W) :
            # Start at the best possible starting point 
            ind = starting_inds[np.argmin(H['f'][starting_inds])]

            Work[i] = {'persis_info':persis_info[i],
                       'H_fields': sim_specs['in'] + [name[0] for name in sim_specs['out']],
                       'tag':EVAL_GEN_TAG, 
                       'libE_info': {'H_rows': np.atleast_1d(ind),
                                     'persistent': True
                                }
                       }

            H['started_run'][ind] = 1
            H['num_active_runs'][ind] += 1

            persis_info[i]['run_order'] = [ind]
            gen_count += 1

        else: 
            # Else, perform sim evaluations from existing runs (if they exist).
            q_inds_logical = np.logical_and.reduce((~H['given'],~H['paused'],~already_in_Work))

            if np.any(q_inds_logical):
                b = np.logical_and(q_inds_logical,  H['local_pt'])
                if np.any(b):
                    q_inds_logical = b
                else:
                    q_inds_logical = np.logical_and(q_inds_logical, ~H['local_pt'])

            if np.any(q_inds_logical):
                sim_ids_to_send = np.nonzero(q_inds_logical)[0][0] # oldest point

                Work[i] = {'H_fields': sim_specs['in'],
                           'persis_info': {}, # Our sims don't need information about how points were generatored
                           'tag':EVAL_SIM_TAG, 
                           'libE_info': {'H_rows': np.atleast_1d(sim_ids_to_send),
                                    },
                          }

                already_in_Work[sim_ids_to_send] = True

            else:
                # Finally, generate points since there is nothing else to do. 
                if gen_count + sum(np.logical_and(W['active']==EVAL_GEN_TAG,W['persis_state']==0)) + sum(W['persis_state']==EVAL_GEN_TAG) > 0: 
                    continue
                gen_count += 1
                # There are no points available, so we call our gen_func
                Work[i] = {'persis_info':persis_info[i],
                           'H_fields': gen_specs['in'],
                           'tag':EVAL_GEN_TAG, 
                           'libE_info': {'H_rows': [],
                                    }
                           }

    return Work, persis_info

