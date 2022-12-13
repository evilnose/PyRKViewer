"""
For development and testing only.
Version 1.0.0: Author: Claire Samuels (2021)

"""

from rkviewer import canvas
from rkviewer.canvas.geometry import Rect
import wx
from rkviewer.plugin.classes import PluginMetadata, CommandPlugin, PluginCategory
from rkviewer.plugin import api
#from rkviewer.plugin.api import CustomShape, CustomShapeGroup, Node, Vec2, Reaction, get_node_indices, reaction_count
from rkviewer.mvc import IDRepeatError
import math
import random
import numpy as _np
import copy as _copy

class PluginEvents1(CommandPlugin):
  metadata = PluginMetadata(
      name='parameters',
      author='Claire Samuels',
      version='1.0.0',
      short_desc='For development and testing only.',
      long_desc='For development and testing only. adds and removes model parameters.',
      category=PluginCategory.UTILITIES,
   )
  def __init__(self):
      """
      Initialize.

      Args:
          self

      """
      super().__init__()

  def run(self):
      net_index = 0

      # printing a call to api.get_paramters shows that there are currently no model parameters
      v0 = api.get_parameters(net_index)
      print(v0)

      # add three parameters with values
      param_ids = ["p1", "p2", "p3"]
      param_vals = [0, 0.3, 100.45]
      for i in range(3):
          api.set_parameter_value(net_index, param_ids[i], param_vals[i])
      v = api.get_parameters(net_index)
      print(v)

      # remove all parameters individually
      for param in v:
          api.remove_parameter(net_index, param) 
      v2 = api.get_parameters(net_index)
      print(v2)
      
      # add a parameter, then change value of said parameter
      api.set_parameter_value(net_index, "p2000", 200)
      api.set_parameter_value(net_index, "p2000", 200000)
      v3 = api.get_parameters(net_index)
      print(v3)

      # remove all parameters
      api.clear_parameters(net_index)
      v4 = api.get_parameters(net_index)
      print(v4)


      
