"""
This module stores environment variables for use in resource detection
"""

import os
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)


class EnvResources:
    """Stores environment variables to query for system resource information

    **Class Attributes:**

    :cvar string default_nodelist_env_slurm: Default SLRUM nodelist environment variable
    :cvar string default_nodelist_env_cobalt: Default Cobal nodelist environment variable
    :cvar string default_nodelist_env_lsf: Default LSF nodelist environment variable
    :cvar string default_nodelist_env_lsf_shortform: Default LSF short-form nodelist environment variable

    **Object Attributes:**

    These are set on initialization.

    :ivar dict nodelists: Environment variable names to query for nodelists by schedular
    :ivar dict ndlist_funcs: Functions to extract nodelists from environment by schedular
    """

    default_nodelist_env_slurm = 'SLURM_NODELIST'
    default_nodelist_env_cobalt = 'COBALT_PARTNAME'
    default_nodelist_env_lsf = 'LSB_HOSTS'
    default_nodelist_env_lsf_shortform = 'LSB_MCPU_HOSTS'

    def __init__(self,
                 nodelist_env_slurm=None,
                 nodelist_env_cobalt=None,
                 nodelist_env_lsf=None,
                 nodelist_env_lsf_shortform=None):

        """Initializes a new EnvResources instance

        Determines the environment variables to query for resource
        information. These are either provided or given defaults.

        Parameters
        ----------

        nodelist_env_slurm: String, optional
            The environment variable giving a node list in Slurm format (Default: uses SLURM_NODELIST).
            Note: This is queried only if a node_list file is not provided and auto_resources=True.

        nodelist_env_cobalt: String, optional
            The environment variable giving a node list in Cobalt format (Default: uses COBALT_PARTNAME).
            Note: This is queried only if a node_list file is not provided and auto_resources=True.

        nodelist_env_lsf: String, optional
            The environment variable giving a node list in LSF format (Default: uses LSB_HOSTS).
            Note: This is queried only if a node_list file is not provided and auto_resources=True.

        nodelist_env_lsf_shortform: String, optional
            The environment variable giving a node list in LSF short-form format (Default: uses LSB_MCPU_HOSTS).
            Note: This is queried only if a node_list file is not provided and auto_resources=True.
        """

        self.schedular = None
        self.nodelists = {}
        self.nodelists['Slurm'] = nodelist_env_slurm or EnvResources.default_nodelist_env_slurm
        self.nodelists['Cobalt'] = nodelist_env_cobalt or EnvResources.default_nodelist_env_cobalt
        self.nodelists['LSF'] = nodelist_env_lsf or EnvResources.default_nodelist_env_lsf
        self.nodelists['LSF_shortform'] = nodelist_env_lsf_shortform or EnvResources.default_nodelist_env_lsf_shortform

        self.ndlist_funcs = {}
        self.ndlist_funcs['Slurm'] = EnvResources.get_slurm_nodelist
        self.ndlist_funcs['Cobalt'] = EnvResources.get_cobalt_nodelist
        self.ndlist_funcs['LSF'] = EnvResources.get_lsf_nodelist
        self.ndlist_funcs['LSF_shortform'] = EnvResources.get_lsf_nodelist_frm_shortform

    def get_nodelist(self):
        """Returns nodelist from environment or an empty list"""
        for env, env_var in self.nodelists.items():
            if os.environ.get(env_var):
                self.schedular = env
                logger.debug("{0} env found - getting nodelist from {0}".format(env))
                get_list_func = self.ndlist_funcs[env]
                global_nodelist = get_list_func(env_var)
                return global_nodelist
        return []

    def abbrev_nodenames(self, node_list):
        """Returns nodelist with entries in abbreviated form"""
        if self.schedular == 'Slurm':
            return EnvResources.slurm_abbrev_nodenames(node_list)
        if self.schedular == 'Cobalt':
            return EnvResources.cobalt_abbrev_nodenames(node_list)
        return node_list

    @staticmethod
    def _range_split(s):
        """Splits ID range string"""
        ab = s.split("-", 1)
        nnum_len = len(ab[0])
        a = int(ab[0])
        b = int(ab[-1])
        if a > b:
            a, b = b, a
        b = b + 1
        return a, b, nnum_len

    @staticmethod
    def _noderange_append(prefix, nidstr):
        """Formats and appends nodes to overall nodelist"""
        nidlst = []
        for nidgroup in nidstr.split(','):
            a, b, nnum_len = EnvResources._range_split(nidgroup)
            for nid in range(a, b):
                nidlst.append(prefix + str(nid).zfill(nnum_len))
        return nidlst

    @staticmethod
    def get_slurm_nodelist(node_list_env):
        """Gets global libEnsemble nodelist from the Slurm environment"""
        fullstr = os.environ[node_list_env]
        if not fullstr:
            return []
        part_splitstr = fullstr.split('],')
        if len(part_splitstr) == 1:     # Single Partition
            splitstr = fullstr.split('[', 1)
            if len(splitstr) == 1:      # Single Node
                return splitstr
            prefix = splitstr[0]
            nidstr = splitstr[1].strip("]")
            nidlst = EnvResources._noderange_append(prefix, nidstr)
        else:                           # Multiple Partitions
            splitgroups = [str.split('[', 1) for str in part_splitstr]
            prefixgroups = [group[0] for group in splitgroups]
            nodegroups = [group[1].strip(']') for group in splitgroups]
            nidlst = []
            for i in range(len(prefixgroups)):
                prefix = prefixgroups[i]
                nidstr = nodegroups[i]
                nidlst.extend(EnvResources._noderange_append(prefix, nidstr))

        return sorted(nidlst)

    @staticmethod
    def get_cobalt_nodelist(node_list_env):
        """Gets global libEnsemble nodelist from the Cobalt environment"""
        nidlst = []
        nidstr = os.environ[node_list_env]
        if not nidstr:
            return []
        for nidgroup in nidstr.split(','):
            a, b, _ = EnvResources._range_split(nidgroup)
            for nid in range(a, b):
                nidlst.append(str(nid))
        return sorted(nidlst, key=int)

    @staticmethod
    def slurm_abbrev_nodenames(node_list, prefix=None):
        """Returns nodelist with only string upto first dot"""
        newlist = [s.split(".", 1)[0] for s in node_list]
        return newlist

    @staticmethod
    def cobalt_abbrev_nodenames(node_list, prefix='nid'):
        """Returns nodelist with prefix and leading zeros stripped"""
        newlist = [s.lstrip(prefix) for s in node_list]
        newlist = [s.lstrip('0') for s in newlist]
        return newlist

    @staticmethod
    def get_lsf_nodelist(node_list_env):
        """Gets global libEnsemble nodelist from the LSF environment"""
        full_list = os.environ[node_list_env]
        entries = full_list.split()
        # unique_entries = list(set(entries)) # This will not retain order
        unique_entries = list(OrderedDict.fromkeys(entries))
        nodes = [n for n in unique_entries if 'batch' not in n]
        return nodes

    @staticmethod
    def get_lsf_nodelist_frm_shortform(node_list_env):
        """Gets global libEnsemble nodelist from the LSF environment from short-form version"""
        full_list = os.environ[node_list_env]
        entries = full_list.split()
        iter_list = iter(entries)
        zipped_list = list(zip(iter_list, iter_list))
        nodes_with_count = [n for n in zipped_list if 'batch' not in n[0]]
        nodes = [n[0] for n in nodes_with_count]
        return nodes
