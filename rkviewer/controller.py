"""Implementation of a controller.
"""
# pylint: disable=maybe-no-member
from contextlib import contextmanager
from numpy.core.fromnumeric import shape
import wx
import traceback
from typing import Any, Collection, List, Optional, Set
import rkviewer.iodine as iod
import logging

from rkviewer.iodine import Color, getReactionModifiers
from .utils import gchain, rgba_to_wx_colour
from .events import DidAddCompartmentEvent, DidAddNodeEvent, DidAddReactionEvent, DidChangeCompartmentOfNodesEvent, DidCommitDragEvent, DidRedoEvent, DidUndoEvent, DidNewNetworkEvent, post_event
from .canvas.data import Compartment, Node, Reaction, CompositeShape
from .canvas.geometry import Vec2
from .canvas.utils import get_nodes_by_ident, get_nodes_by_idx
from .mvc import IController, IView, ModelError, ModifierTipStyle


def iod_setter(controller_iod_setter):
    """Decorator for controller iod_setter methods that catches Errors and auto updates views."""
    # If programmatic is True, then do not trigger a C-Event

    def ret(self, *args):
        retval = controller_iod_setter(self, *args)

        if self.group_depth == 0:
            self._update_view()

        return retval

    return ret


class Controller(IController):
    """A controller class.

    This is not strictly adhering to the MVC architecture, since there is not a separate Model
    interface. Rather, this controller directly interacts with iodine. The model class should
    be implemented if necessary.
    """
    view: IView

    def __init__(self, view: IView):
        self.view = view
        iod.reset()
        iod.newNetwork('the one')
        self.stacklen = 0  # TODO temporary hack to not undo the first newNetwork() operation.
        self.group_depth = 0
        self.initial_position = wx.Point (0,0)

    @contextmanager
    def group_action(self):
        try:
            self._start_group()
            yield
        finally:
            self._end_group()

    def _start_group(self) -> bool:
        self.group_depth += 1

        # already in a group before; don't start startGroup()
        if self.group_depth > 1:
            return False
        iod.startGroup()
        return True

    def _end_group(self) -> bool:
        assert self.group_depth > 0
        self.group_depth -= 1

        # still in a group; don't call endGroup()
        if self.group_depth > 0:
            return False

        iod.endGroup()
        self._update_view()
        return True

    def in_group(self) -> bool:
        return self.group_depth > 0

    def undo(self) -> bool:
        if self.stacklen == 0:
            return False
        try:
            assert self.group_depth == 0
            iod.undo()
            post_event(DidUndoEvent())
        except iod.StackEmptyError:
            logging.getLogger('controller').info('Undo stack is empty')
            return False

        self.stacklen -= 2  # -2 to correct the +1 in update_view
        self._update_view()
        return True

    def redo(self) -> bool:
        try:
            assert self.group_depth == 0
            iod.redo()
            post_event(DidRedoEvent())
        except iod.StackEmptyError:
            logging.getLogger('controller').info('Redo stack is empty')
            return False

        self._update_view()
        return True

    @iod_setter
    def clear_network(self, neti):
        iod.clearNetwork(neti)

    def add_node_g(self, neti: int, node: Node) -> int:
        '''
        Add node represented by the given Node variable.

        The 'g' suffix indicates that this operation creates its own group
        '''
        with self.group_action():
            iod.addNode(neti, node.id, node.position.x, node.position.y, node.size.x, node.size.y, True) # True = floating species
            nodei = iod.getNodeIndex(neti, node.id)
            # iod.setNodeFillColorAlpha(neti, nodei, node.fill_color.Alpha() / 255)
            # iod.setNodeFillColorRGB(neti, nodei, node.fill_color.Red(),
            #                         node.fill_color.Green(), node.fill_color.Blue())
            # iod.setNodeBorderColorAlpha(neti, nodei, node.border_color.Alpha() / 255)
            # iod.setNodeBorderColorRGB(neti, nodei, node.border_color.Red(),
            #                            node.border_color.Green(), node.border_color.Blue())
            # iod.setNodeBorderWidth(neti, nodei, int(node.border_width))
            iod.setCompartmentOfNode(neti, nodei, node.comp_idx)
            iod.setNodeFloatingStatus(neti, nodei, node.floatingNode)
            iod.setNodeShapeIndex(neti, nodei, node.shape_index)

            post_event(DidAddNodeEvent(nodei))
        return nodei

    def set_application_position(self, pos: wx.Point):
        self.initial_position = pos

    def get_application_position(self) -> wx.Point:
        return self.initial_position

    def get_composite_shape_list(self, neti: int) -> List[CompositeShape]:
        return iod.getListOfCompositeShapes(neti)

    def get_composite_shape_at(self, neti: int, shapei: int) -> CompositeShape:
        return iod.getCompositeShapeAt(neti, shapei)

    def get_node_shape(self, neti: int, nodei: int) -> CompositeShape:
        return iod.getNodeShape(neti, nodei)

    def get_node_shape_index(self, neti: int, nodei: int) -> int:
        return iod.getNodeShapeIndex(neti, nodei)

    @iod_setter
    def set_node_shape_index(self, neti: int, nodei: int, shapei: int):
        iod.setNodeShapeIndex(neti, nodei, shapei)
    
    @iod_setter
    def set_node_primitive_property(self, neti: int, nodei: int, primitive_index: int, prop_name: str, prop_value):
        iod.setNodePrimitiveProperty(neti, nodei, primitive_index, prop_name, prop_value)

    def wx_to_tcolor(self, color: wx.Colour) -> Color:
        return Color(color.Red(), color.Green(), color.Blue(), color.Alpha())

    def tcolor_to_wx(self, color: Color) -> wx.Colour:
        return wx.Colour(color.r, color.g, color.b, color.a)

    def add_compartment_g(self, neti: int, compartment: Compartment) -> int:
        if len(compartment.nodes) != 0:
            raise ValueError('The "nodes" list for a newly added compartment should be empty. '
                             'This is to avoid implicit moving of nodes between compartments.')
        with self.group_action():
            compi = iod.addCompartment(neti, compartment.id, *compartment.position, *compartment.size)
            iod.setCompartmentFillColor(neti, compi, self.wx_to_tcolor(compartment.fill))
            iod.setCompartmentOutlineColor(neti, compi, self.wx_to_tcolor(compartment.border))
            iod.setCompartmentOutlineThickness(neti, compi, compartment.border_width)
            iod.setCompartmentVolume(neti, compi, compartment.volume)
            post_event(DidAddCompartmentEvent(compi))
        return compi
    
    @iod_setter
    def add_alias_node(self, neti: int, original_idx: int, pos: Vec2, size: Vec2) -> int:
        return iod.addAliasNode(neti, original_idx, *pos, *size)
    
    @iod_setter
    def alias_for_reaction(self, neti: int, reai: int, nodei: int, pos: Vec2, size: Vec2):
        iod.aliasForReaction(neti, reai, nodei, *pos, *size)

    @iod_setter
    def move_node(self, neti: int, nodei: int, pos: Vec2, allowNegativeCoordinates: bool=False):
        #assert pos.x >= 0 and pos.y >= 0
        iod.setNodeCoordinate(neti, nodei, pos.x, pos.y, allowNegativeCoordinates)

    @iod_setter
    def set_node_size(self, neti: int, nodei: int, size: Vec2):
        iod.setNodeSize(neti, nodei, size.x, size.y)

    @iod_setter
    def rename_node(self, neti: int, nodei: int, new_id: str):
        iod.setNodeID(neti, nodei, new_id)

    @iod_setter
    def set_node_concentration(self, neti: int, nodei: int, new_conc: float):
        iod.setNodeConcentration(neti, nodei, new_conc)

    @iod_setter
    def set_node_floating_status(self, neti: int, nodei: int, floatingStatus: bool):
        iod.setNodeFloatingStatus (neti, nodei, floatingStatus)

    @iod_setter
    def set_node_locked_status(self, neti: int, nodei: int, lockedNode: bool):
        iod.setNodeLockedStatus (neti, nodei, lockedNode)

    @iod_setter
    def set_node_fill_rgb(self, neti: int, nodei: int, color: wx.Colour):
        iod.setNodeFillColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())

    @iod_setter
    def set_node_fill_alpha(self, neti: int, nodei: int, alpha: int):
        iod.setNodeFillColorAlpha(neti, nodei, alpha / 255)

    @iod_setter
    def set_node_border_rgb(self, neti: int, nodei: int, color: wx.Colour):
        iod.setNodeBorderColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())

    @iod_setter
    def set_node_border_alpha(self, neti: int, nodei: int, alpha: int):
        iod.setNodeBorderColorAlpha(neti, nodei, alpha / 255)

    @iod_setter
    def rename_reaction(self, neti: int, reai: int, new_id: str):
        iod.setReactionID(neti, reai, new_id)

    @iod_setter
    def set_reaction_line_thickness(self, neti: int, reai: int, thickness: float):
        iod.setReactionLineThickness(neti, reai, thickness)

    @iod_setter
    def set_reaction_fill_rgb(self, neti: int, reai: int, color: wx.Colour):
        iod.setReactionFillColorRGB(neti, reai, color.Red(), color.Green(), color.Blue())

    @iod_setter
    def set_reaction_fill_alpha(self, neti: int, reai: int, alpha: int):
        iod.setReactionFillColorAlpha(neti, reai, alpha / 255)

    @iod_setter
    def set_reaction_bezier_curves(self, neti: int, reai: int, bezierCurves: bool):
        iod.setReactionBezierCurves(neti, reai, bezierCurves)

    @iod_setter
    def set_node_border_width(self, neti: int, nodei: int, width: float):
        iod.setNodeBorderWidth(neti, nodei, width)

    @iod_setter
    def set_reaction_modifiers(self, neti: int, reai: int, modifiers: Set[int]):
        iod.setReactionModifiers(neti, reai, modifiers)

    def get_reaction_modifiers(self, neti: int, reai: int) -> Set[int]:
        return iod.getReactionModifiers(neti, reai)

    @iod_setter
    def set_modifier_tip_style(self, neti: int, reai: int, style: ModifierTipStyle):
        iod.setModifierTipStyle(neti, reai, style)

    def get_modifier_tip_style(self, neti: int, reai: int) -> ModifierTipStyle:
        return iod.getModifierTipStyle(neti, reai)

    @iod_setter
    def set_network_parameter(self, neti: int, param_id: str, param_value: float):
        iod.setParameter(neti, param_id, param_value)

    @iod_setter
    def remove_network_parameter(self, neti: int, param_id: str):
        iod.removeParameter(neti, param_id)

    def get_network_parameters(self, neti: int):
        return iod.getParameters(neti)

    @iod_setter
    def delete_node(self, neti: int, nodei: int) -> bool:
        return iod.deleteNode(neti, nodei)

    @iod_setter
    def delete_reaction(self, neti: int, reai: int):
        iod.deleteReaction(neti, reai)

    @iod_setter
    def delete_compartment(self, neti: int, compi: int):
        iod.deleteCompartment(neti, compi)

    def add_reaction_g(self, neti: int, reaction: Reaction) -> int:
        """Try create a reaction."""
        with self.group_action():
            iod.createReaction(neti, reaction.id, reaction.sources, reaction.targets)
            reai = iod.getReactionIndex(neti, reaction.id)

            for sidx in reaction.sources:
                iod.setReactionSrcNodeStoich(neti, reai, sidx, 1.0)

            for tidx in reaction.targets:
                iod.setReactionDestNodeStoich(neti, reai, tidx, 1.0)

            iod.setReactionFillColorRGB(neti, reai,
                                        reaction.fill_color.Red(),
                                        reaction.fill_color.Green(),
                                        reaction.fill_color.Blue())
            for (gi, nodei), handle in zip(gchain(reaction.sources, reaction.targets), reaction.handles):
                pos = handle.tip
                if gi == 0:
                    iod.setReactionSrcNodeHandlePosition(neti, reai, nodei, pos.x, pos.y)
                else:
                    iod.setReactionDestNodeHandlePosition(neti, reai, nodei, pos.x, pos.y)

            cpos = reaction.src_c_handle.tip
            iod.setReactionCenterHandlePosition(neti, reai, cpos.x, cpos.y)
            post_event(DidAddReactionEvent(reai, reaction.sources, reaction.targets))
        return reai

    @iod_setter
    def set_reaction_ratelaw(self, neti: int, reai: int, ratelaw: str):
        iod.setRateLaw(neti, reai, ratelaw)

    @iod_setter
    def set_reaction_center(self, neti: int, reai: int, center_pos: Optional[Vec2]):
        iod.setReactionCenterPos(neti, reai, center_pos)

    @iod_setter
    def set_src_node_stoich(self, neti: int, reai: int, nodei: int, stoich: float):
        iod.setReactionSrcNodeStoich(neti, reai, nodei, stoich)

    @iod_setter
    def set_dest_node_stoich(self, neti: int, reai: int, nodei: int, stoich: float):
        iod.setReactionDestNodeStoich(neti, reai, nodei, stoich)

    @iod_setter
    def set_src_node_handle(self, neti: int, reai: int, nodei: int, pos: Vec2):
        iod.setReactionSrcNodeHandlePosition(neti, reai, nodei, pos.x, pos.y)

    @iod_setter
    def set_dest_node_handle(self, neti: int, reai: int, nodei: int, pos: Vec2):
        iod.setReactionDestNodeHandlePosition(neti, reai, nodei, pos.x, pos.y)

    @iod_setter
    def set_center_handle(self, neti: int, reai: int, pos: Vec2):
        iod.setReactionCenterHandlePosition(neti, reai, pos.x, pos.y)

    def get_src_node_handle(self, neti: int, reai: int, nodei: int) -> Vec2:
        return Vec2(iod.getReactionSrcNodeHandlePosition(neti, reai, nodei))

    def get_dest_node_handle(self, neti: int, reai: int, nodei: int) -> Vec2:
        return Vec2(iod.getReactionDestNodeHandlePosition(neti, reai, nodei))

    def get_center_handle(self, neti: int, reai: int) -> Vec2:
        return Vec2(iod.getReactionCenterHandlePosition(neti, reai))

    def get_src_node_stoich(self, neti: int, reai: int, nodei: int):
        return iod.getReactionSrcNodeStoich(neti, reai, nodei)

    def get_dest_node_stoich(self, neti: int, reai: int, nodei: int):
        return iod.getReactionDestNodeStoich(neti, reai, nodei)

    def get_list_of_src_indices(self, neti: int, reai: int):
        return iod.getListOfReactionSrcNodes(neti, reai)

    def get_list_of_dest_indices(self, neti: int, reai: int):
        return iod.getListOfReactionDestNodes(neti, reai)

    def get_list_of_node_ids(self, neti: int) -> List[str]:
        return iod.getListOfNodeIDs(neti)

    def get_reactions_as_reactant(self, neti: int, nodei: int) -> Set[int]:
        return iod.getSrcReactions(neti, nodei)

    def get_reactions_as_product(self, neti: int, nodei: int) -> Set[int]:
        return iod.getDestReactions(neti, nodei)

    def get_node_indices(self, neti: int) -> Set[int]:
        return iod.getListOfNodeIndices(neti)

    def get_reaction_indices(self, neti: int) -> Set[int]:
        return iod.getListOfReactionIndices(neti)

    def get_compartment_indices(self, neti: int) -> Set[int]:
        return iod.getListOfCompartmentIndices(neti)

    def get_list_of_nodes(self, neti: int) -> List[Node]:
        nodes = list()
        for nodei in iod.getListOfNodeIndices(neti):
            nodes.append(self.get_node_by_index(neti, nodei))
        return nodes

    def get_list_of_reactions(self, neti: int) -> List[Reaction]:
        reactions = list()
        for reai in iod.getListOfReactionIndices(neti):
            reactions.append(self.get_reaction_by_index(neti, reai))
        return reactions

    def get_list_of_compartments(self, neti: int) -> List[Compartment]:
        return [self.get_compartment_by_index(neti, compi)
                for compi in iod.getListOfCompartments(neti)]

    @iod_setter
    def rename_compartment(self, neti: int, compi: int, new_id: str):
        iod.setCompartmentID(neti, compi, new_id)

    @iod_setter
    def move_compartment(self, neti: int, compi: int, pos: Vec2):
        try:
            iod.setCompartmentPosition(neti, compi, *pos)
        except:
            wx.MessageBox("Can not move the compartment.", "Message", wx.OK | wx.ICON_INFORMATION)

    @iod_setter
    def set_compartment_size(self, neti: int, compi: int, size: Vec2):
        iod.setCompartmentSize(neti, compi, *size)

    @iod_setter
    def set_compartment_fill(self, neti: int, compi: int, fill: wx.Colour):
        iod.setCompartmentFillColor(neti, compi, self.wx_to_tcolor(fill))

    @iod_setter
    def set_compartment_border(self, neti: int, compi: int, border: wx.Colour):
        iod.setCompartmentOutlineColor(neti, compi, self.wx_to_tcolor(border))

    @iod_setter
    def set_compartment_border_width(self, neti: int, compi: int, width: float):
        iod.setCompartmentOutlineThickness(neti, compi, width)

    @iod_setter
    def set_compartment_volume(self, neti: int, compi: int, volume: float):
        iod.setCompartmentVolume(neti, compi, volume)

    @iod_setter
    def set_compartment_of_node(self, neti: int, nodei: int, compi: int):
        iod.setCompartmentOfNode(neti, nodei, compi)

    def get_compartment_of_node(self, neti: int, nodei: int) -> int:
        return iod.getCompartmentOfNode(neti, nodei)

    def get_nodes_in_compartment(self, neti: int, compi: int) -> List[int]:
        return iod.getNodesInCompartment(neti, compi)

    def get_node_index(self, neti: int, node_id: str) -> int:
        return iod.getNodeIndex(neti, node_id)

    def get_node_id(self, neti: int, nodei: int) -> str:
        return iod.getNodeID(neti, nodei)

    def get_reaction_index(self, neti: int, rxn_id: str) -> int:
        return iod.getReactionIndex(neti, rxn_id)

    def get_node_by_index(self, neti: int, nodei: int) -> Node:
        id = iod.getNodeID(neti, nodei)
        x, y, w, h = iod.getNodeCoordinateAndSize(neti, nodei)
        # fill_alpha = iod.getNodeFillColorAlpha(neti, nodei)
        # fill_rgb = iod.getNodeFillColorRGB(neti, nodei)
        # fill_color = rgba_to_wx_colour(fill_rgb, fill_alpha)
        # border_alpha = iod.getNodeBorderColorAlpha(neti, nodei)
        # border_rgb = iod.getNodeBorderColorRGB(neti, nodei)
        # border_color = rgba_to_wx_colour(border_rgb, border_alpha)
        return Node(
            id,
            neti,
            index=nodei,
            pos=Vec2(x, y),
            size=Vec2(w, h),
            concentration=iod.getNodeConcentration(neti, nodei),
            # fill_color=fill_color,
            # border_color=border_color,
            # border_width=iod.getNodeBorderWidth(neti, nodei),
            comp_idx=iod.getCompartmentOfNode(neti, nodei),
            floatingNode=iod.IsFloatingNode(neti, nodei),
            lockNode=iod.IsNodeLocked(neti, nodei),
            shape_index=iod.getNodeShapeIndex(neti, nodei),
            composite_shape=iod.getNodeShape(neti, nodei),
            original_index=iod.getOriginalIndex(neti, nodei)
        )

    def get_reaction_by_index(self, neti: int, reai: int) -> Reaction:
        id = iod.getReactionID(neti, reai)
        sindices = iod.getListOfReactionSrcNodes(neti, reai)
        tindices = iod.getListOfReactionDestNodes(neti, reai)
        fill_rgb = iod.getReactionFillColorRGB(neti, reai)
        fill_alpha = iod.getReactionFillColorAlpha(neti, reai)

        # Handle positions array
        items = list()
        items.append(self.get_center_handle(neti, reai))
        items += [self.get_src_node_handle(neti, reai, i) for i in sindices]
        items += [self.get_dest_node_handle(neti, reai, i) for i in tindices]

        return Reaction(id,
                        neti,
                        sources=sindices,
                        targets=tindices,
                        fill_color=rgba_to_wx_colour(fill_rgb, fill_alpha),
                        line_thickness=iod.getReactionLineThickness(neti, reai),
                        index=reai,
                        rate_law=iod.getReactionRateLaw(neti, reai),
                        handle_positions=items,
                        center_pos=iod.getReactionCenterPos(neti, reai),
                        bezierCurves=iod.bezier_curves(neti, reai),
                        modifiers=iod.getReactionModifiers(neti, reai),
                        modifier_tip_style=iod.getModifierTipStyle(neti, reai),
                        )

    def get_compartment_by_index(self, neti: int, compi: int) -> Compartment:
        id = iod.getCompartmentID(neti, compi)

        return Compartment(id,
                           nodes=iod.getNodesInCompartment(neti, compi),
                           volume=iod.getCompartmentVolume(neti, compi),
                           position=Vec2(iod.getCompartmentPosition(neti, compi)),
                           size=Vec2(iod.getCompartmentSize(neti, compi)),
                           fill=self.tcolor_to_wx(iod.getCompartmentFillColor(neti, compi)),
                           border=self.tcolor_to_wx(iod.getCompartmentOutlineColor(neti, compi)),
                           border_width=iod.getCompartmentOutlineThickness(neti, compi),
                           index=compi,
                           net_index=neti,
                           )    

    def update_view(self):
        """Immediately update the view with using latest model."""
        return self._update_view()
    
    def dump_network(self, neti: int):
        return iod.dumpNetwork(neti)

    def load_network(self, json_obj: Any) -> int:
        net_index =  iod.loadNetwork(json_obj)
        self._update_view()
        return net_index

    def new_network(self):
        iod.clearNetwork(0)
        post_event(DidNewNetworkEvent())
        self._update_view()

    # get the updated list of nodes from model and update

    def _update_view(self):
        """tell the view to update by re-populating its list of nodes."""

        self.stacklen += 1  # TODO remove once fixed
        neti = 0
        self.view.update_all(self.get_list_of_nodes(neti), self.get_list_of_reactions(neti),
                             self.get_list_of_compartments(neti))
