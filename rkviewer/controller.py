"""Implementation of a controller.
"""
# pylint: disable=maybe-no-member
import wx
import traceback
from typing import Collection, List, Optional, Set
import iodine as iod
import logging

from iodine import TColor
from .utils import gchain, rgba_to_wx_colour
from .events import DidAddNodeEvent, DidCommitNodePositionsEvent, post_event
from .canvas.data import Compartment, Node, Reaction
from .canvas.geometry import Vec2
from .canvas.utils import get_nodes_by_ident, get_nodes_by_idx
from .mvc import IController, IView


def iod_setter(controller_iod_setter):
    """Decorator for controller iod_setter methods that catches Errors and auto updates views."""
    # If programmatic is True, then do not trigger a C-Event

    def ret(self, *args):
        controller_iod_setter(self, *args)
        '''
        try:
            controller_iod_setter(self, *args)
        except iod.Error:
            logger = logging.getLogger('controller')
            logger.error('Caught error when trying to set something in controller:')
            logger.error(traceback.format_exc())
            return False
        '''

        if self.group_depth == 0:
            self._update_view()
        return True

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

    def start_group(self) -> bool:
        self.group_depth += 1

        # already in a group before; don't start startGroup()
        if self.group_depth > 1:
            return False
        iod.startGroup()
        return True

    def end_group(self) -> bool:
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
        except iod.StackEmptyError:
            logging.getLogger('controller').info('Undo stack is empty')
            return False
        except iod.Error as e:
            print('Error undoing:', str(e))
            return False

        self.stacklen -= 2  # -2 to correct the +1 in update_view
        self._update_view()
        return True

    def redo(self) -> bool:
        try:
            assert self.group_depth == 0
            iod.redo()
        except iod.StackEmptyError:
            logging.getLogger('controller').info('Redo stack is empty')
            return False
        except iod.Error as e:
            print('Error redoing:', str(e))
            return False

        self._update_view()
        return True

    @iod_setter
    def add_node_g(self, neti: int, node: Node, programmatic: bool = False):
        '''
        Add node represented by the given Node variable.

        The 'g' suffix indicates that this operation creates its own group
        '''
        self.start_group()
        iod.addNode(neti, node.id_, node.position.x, node.position.y, node.size.x, node.size.y)
        nodei = iod.getNodeIndex(neti, node.id_)
        iod.setNodeFillColorAlpha(neti, nodei, node.fill_color.Alpha() / 255)
        iod.setNodeFillColorRGB(neti, nodei, node.fill_color.Red(),
                                node.fill_color.Green(), node.fill_color.Blue())
        iod.setNodeOutlineColorAlpha(neti, nodei, node.border_color.Alpha() / 255)
        iod.setNodeOutlineColorRGB(neti, nodei, node.border_color.Red(),
                                   node.border_color.Green(), node.border_color.Blue())
        iod.setNodeOutlineThickness(neti, nodei, int(node.border_width))
        iod.setCompartmentOfNode(neti, nodei, node.comp_idx)

        if not programmatic:
            post_event(DidAddNodeEvent(node))
        self.end_group()

    def wx_to_tcolor(self, color: wx.Colour) -> TColor:
        return TColor(color.Red(), color.Green(), color.Blue(), color.Alpha())

    def tcolor_to_wx(self, color: TColor) -> wx.Colour:
        return wx.Colour(color.r, color.g, color.b, color.a)

    @iod_setter
    def add_compartment_g(self, neti: int, compartment: Compartment):
        self.start_group()
        compi = iod.addCompartment(neti, compartment.id_, *compartment.position, *compartment.size)
        iod.setCompartmentFillColor(neti, compi, self.wx_to_tcolor(compartment.fill))
        iod.setCompartmentOutlineColor(neti, compi, self.wx_to_tcolor(compartment.border))
        iod.setCompartmentOutlineThickness(neti, compi, compartment.border_width)
        iod.setCompartmentVolume(neti, compi, compartment.volume)
        self.end_group()

    @iod_setter
    def move_node(self, neti: int, nodei: int, pos: Vec2, programmatic: bool = False):
        assert pos.x >= 0 and pos.y >= 0
        iod.setNodeCoordinate(neti, nodei, pos.x, pos.y)
        # dispatch event if the call was caused by user input
        if not programmatic:
            post_event(DidCommitNodePositionsEvent())

    @iod_setter
    def set_node_size(self, neti: int, nodei: int, size: Vec2):
        iod.setNodeSize(neti, nodei, size.x, size.y)

    @iod_setter
    def rename_node(self, neti: int, nodei: int, new_id: str):
        iod.setNodeID(neti, nodei, new_id)

    @iod_setter
    def set_node_fill_rgb(self, neti: int, nodei: int, color: wx.Colour):
        iod.setNodeFillColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())

    @iod_setter
    def set_node_fill_alpha(self, neti: int, nodei: int, alpha: int):
        iod.setNodeFillColorAlpha(neti, nodei, alpha / 255)

    @iod_setter
    def set_node_border_rgb(self, neti: int, nodei: int, color: wx.Colour):
        iod.setNodeOutlineColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())

    @iod_setter
    def set_node_border_alpha(self, neti: int, nodei: int, alpha: int):
        iod.setNodeOutlineColorAlpha(neti, nodei, alpha / 255)

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
    def set_node_border_width(self, neti: int, nodei: int, width: float):
        iod.setNodeOutlineThickness(neti, nodei, width)

    @iod_setter
    def delete_node(self, neti: int, nodei: int):
        iod.deleteNode(neti, nodei)

    @iod_setter
    def delete_reaction(self, neti: int, reai: int):
        iod.deleteReaction(neti, reai)

    @iod_setter
    def delete_compartment(self, neti: int, compi: int):
        iod.deleteCompartment(neti, compi)

    @iod_setter
    def add_reaction_g(self, neti: int, reaction: Reaction):
        """Try create a reaction."""
        self.start_group()
        iod.createReaction(neti, reaction.id_)
        reai = iod.getReactionIndex(neti, reaction.id_)

        for sidx in reaction.sources:
            iod.addSrcNode(neti, reai, sidx, 1.0)

        for tidx in reaction.targets:
            iod.addDestNode(neti, reai, tidx, 1.0)

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
        self.end_group()

    @iod_setter
    def set_reaction_ratelaw(self, neti: int, reai: int, ratelaw: str):
        iod.setRateLaw(neti, reai, ratelaw)

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

    def get_list_of_nodes(self, neti: int) -> List[Node]:
        nodes = list()
        for id_ in iod.getListOfNodeIDs(neti):
            nodei = iod.getNodeIndex(neti, id_)
            nodes.append(self.get_node_by_index(neti, nodei))
        return nodes

    def get_list_of_reactions(self, neti: int) -> List[Reaction]:
        reactions = list()
        for id_ in iod.getListOfReactionIDs(neti):
            reai = iod.getReactionIndex(neti, id_)
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
        iod.setCompartmentPosition(neti, compi, *pos)

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

    def get_node_index(self, neti: int, node_id: str) -> int:
        return iod.getNodeIndex(neti, node_id)

    def get_node_id(self, neti: int, nodei: int) -> str:
        return iod.getNodeID(neti, nodei)

    def get_reaction_index(self, neti: int, rxn_id: str) -> int:
        return iod.getReactionIndex(neti, rxn_id)

    def get_node_by_index(self, neti: int, nodei: int) -> Node:
        id_ = iod.getNodeID(neti, nodei)
        x, y, w, h = iod.getNodeCoordinateAndSize(neti, nodei)
        fill_alpha = iod.getNodeFillColorAlpha(neti, nodei)
        fill_rgb = iod.getNodeFillColorRGB(neti, nodei)
        fill_color = rgba_to_wx_colour(fill_rgb, fill_alpha)
        border_alpha = iod.getNodeOutlineColorAlpha(neti, nodei)
        border_rgb = iod.getNodeOutlineColorRGB(neti, nodei)
        border_color = rgba_to_wx_colour(border_rgb, border_alpha)
        return Node(
            id_,
            index=nodei,
            pos=Vec2(x, y),
            size=Vec2(w, h),
            fill_color=fill_color,
            border_color=border_color,
            border_width=iod.getNodeOutlineThickness(neti, nodei),
            comp_idx=iod.getCompartmentOfNode(neti, nodei),
        )

    def get_reaction_by_index(self, neti: int, reai: int) -> Reaction:
        id_ = iod.getReactionID(neti, reai)
        sindices = iod.getListOfReactionSrcNodes(neti, reai)
        tindices = iod.getListOfReactionDestNodes(neti, reai)
        fill_rgb = iod.getReactionFillColorRGB(neti, reai)
        fill_alpha = iod.getReactionFillColorAlpha(neti, reai)

        # Handle positions array
        items = list()
        items.append(self.get_center_handle(neti, reai))
        items += [self.get_src_node_handle(neti, reai, i) for i in sindices]
        items += [self.get_dest_node_handle(neti, reai, i) for i in tindices]

        return Reaction(id_,
                        sources=sindices,
                        targets=tindices,
                        fill_color=rgba_to_wx_colour(fill_rgb, fill_alpha),
                        line_thickness=iod.getReactionLineThickness(neti, reai),
                        index=reai,
                        rate_law=iod.getReactionRateLaw(neti, reai),
                        handle_positions=items
                        )

    def get_compartment_by_index(self, neti: int, compi: int) -> Compartment:
        id_ = iod.getCompartmentID(neti, compi)

        return Compartment(id_,
                           nodes=iod.getNodesInCompartment(neti, compi),
                           volume=iod.getCompartmentVolume(neti, compi),
                           position=Vec2(iod.getCompartmentPosition(neti, compi)),
                           size=Vec2(iod.getCompartmentSize(neti, compi)),
                           fill=self.tcolor_to_wx(iod.getCompartmentFillColor(neti, compi)),
                           border=self.tcolor_to_wx(iod.getCompartmentOutlineColor(neti, compi)),
                           border_width=iod.getCompartmentOutlineThickness(neti, compi),
                           index=compi,
                           )

    # get the updated list of nodes from model and update

    def _update_view(self):
        """tell the view to update by re-populating its list of nodes."""

        self.stacklen += 1  # TODO remove once fixed
        neti = 0
        self.view.update_all(self.get_list_of_nodes(neti), self.get_list_of_reactions(neti),
                             self.get_list_of_compartments(neti))
