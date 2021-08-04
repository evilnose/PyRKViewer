"""
Duplicates all selected reactions as well as their reactant and product nodes.
If no reactions are selected, duplicates all reactions

Version 0.01: Author: Claire Samuels (2021)

"""

import wx
from rkviewer.plugin.classes import PluginMetadata, CommandPlugin, PluginCategory
from rkviewer.plugin import api
from rkviewer.plugin.api import Node, Vec2, Reaction
from rkviewer.mvc import IDRepeatError
import math
import random as _random
import numpy as _np
import copy as _copy

class DuplicateReaction(CommandPlugin):
  metadata = PluginMetadata(
      name='DuplicateReaction',
      author='Claire Samuels',
      version='0.0.1',
      short_desc='Duplicate a reaction.',
      long_desc='Creates an exact copy of the selected reactions and all connected nodes.',
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

    net_index = 0

    selected_reacts = api.selected_reaction_indices()
    if len(selected_reacts) < 1:
      selected_reacts = api.get_reaction_indices(net_index)

    def copy_node(node_index, net_index):
      '''
      Creates a new node, translated 300 px down and to the right.
      Parameters: node index
      Returns: index of new node
      '''
      node = api.get_node_by_index(net_index,node_index)
      try:
        inx = api.add_node(net_index, id='copy_{}'.format(node.id),
                        shape_index=node.shape_index, size=Vec2(node.size[0]+60, node.size[1]),
                        position=Vec2(node.position[0]+300, node.position[1]+300))
      except IDRepeatError:
        # find a unique id
        all_ids = []
        ns = api.get_nodes(net_index)
        for n in ns:
          all_ids.append(n.id)
        c = 1
        new_id = 'copy_{}_{}'.format(node.id,c)
        while new_id in all_ids:
          c += 1
          new_id = 'copy_{}_{}'.format(node.id,c)
        inx = api.add_node(net_index, id=new_id,
                        shape_index=node.shape_index, size=Vec2(node.size[0]+60, node.size[1]),
                        position=Vec2(node.position[0]+300, node.position[1]+300))
      return inx

    orig_node_set = set()
    reaction_info = {}

    for r_index in selected_reacts:
      r = api.get_reaction_by_index(net_index, r_index)
      r_info = {
        "sources": r.sources,
        "targets": r.targets,
        "id": r.id
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
      reac_id = reaction_info[reaction]["id"]
      n_index = api.add_reaction(net_index, id="copy"+str(reaction), reactants=new_sources,
                       products=new_targets)
      api.update_reaction(net_index, n_index, id='{}_copy_{}'.format(reac_id,n_index))


