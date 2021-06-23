"""
Duplicates all selected reactions as well as their reactant and product nodes.

Version 0.01: Author: Claire Samuels (2021)

"""

import wx
from rkviewer.plugin.classes import PluginMetadata, CommandPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction
import math
import random as _random
import numpy as _np
import copy as _copy
from dataclasses import dataclass

class DuplicateReaction(CommandPlugin):
  metadata = PluginMetadata(
      name='DuplicateReaction',
      author='Claire Samuels',
      version='0.0.1',
      short_desc='Duplicate a reaction.',
      long_desc='Creates an exact copy of the selected reaction',
      category=PluginCategory.UTILITIES,
   )
  def __init__(self):
      """
      Initialize the DuplicateReaction.

      Args:
          self

      """
      super().__init__()

  def run(self):

    selected_reacts = api.selected_reaction_indices()

    net_index = 0

    # create a copy of passed node
    # accepts a node index
    # returns index of new node
    def copy_node(node_index, net_index):
      node = api.get_node_by_index(net_index,node_index)
      inx = api.add_node(net_index, 'copy_node_{}'.format(node_index),
                    position=Vec2(node.position[0]+200, node.position[1]+200), size=Vec2(100,30))
      return inx

    orig_node_set = set()
    reaction_info = {}

    selected_reacts = api.selected_reaction_indices()
    for r_index in selected_reacts:
      r = api.get_reaction_by_index(net_index, r_index)
      r_info = {
        "sources": r.sources,
        "targets": r.targets
      }
      reaction_info[r_index] = r_info
      orig_node_set = orig_node_set.union(set(r.sources))
      orig_node_set = orig_node_set.union(set(r.targets))

    node_indices = {}
    for n_index in orig_node_set:
      new_index = copy_node(n_index, net_index)
      node_indices[n_index] = new_index

    for reaction in reaction_info:
      new_sources = []
      for src in reaction_info[reaction]["sources"]:
        new_sources.append(node_indices[src])
      new_targets = []
      for trg in reaction_info[reaction]["targets"]:
        new_targets.append(node_indices[trg])
      api.add_reaction(net_index, 'copy_reac_{}'.format(reaction), reactants=new_sources,
                       products=new_targets)



