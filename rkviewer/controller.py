"""Implementation of a controller.
"""
# pylint: disable=maybe-no-member
import wx
from typing import Collection, List, Optional, Set
import iodine as iod
from .utils import rgba_to_wx_colour
from .events import DidAddNodeEvent, DidCommitNodePositionsEvent, post_event
from .canvas.data import Node, Reaction
from .canvas.geometry import Vec2
from .canvas.utils import get_nodes_by_ident, get_nodes_by_idx
from .mvc import IController, IView


def try_setter(fn):
    """Decorator for controller setter methods that catches Errors and auto updates views."""
    # If programmatic is True, then do not trigger a C-Event
    def ret(self, *args):
        try:
            fn(self, *args)
        except iod.Error as e:
            print("Function '{}' failed, reason: {}.".format(fn.__name__, str(e)))
            return False

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
        iod.newNetwork('the one')
        self.stacklen = 0  # TODO temporary hack to not undo the first newNetwork() operation.
        self.group_depth = 0

    def try_start_group(self) -> bool:
        self.group_depth += 1

        # already in a group before; don't start startGroup()
        if self.group_depth > 1:
            return False
        try:
            iod.startGroup()
        except iod.Error as e:
            # TODO replace all print statements with logging
            print('Error starting group:', str(e))
            return False
        return True

    def try_end_group(self) -> bool:
        assert self.group_depth > 0
        self.group_depth -= 1

        # still in a group; don't call endGroup()
        if self.group_depth > 0:
            return False

        try:
            iod.endGroup()
        except iod.Error as e:
            print('Error ending group:', str(e))
            return False

        self._update_view()
        return True

    def in_group(self) -> bool:
        return self.group_depth > 0

    def try_undo(self) -> bool:
        if self.stacklen == 0:
            return False
        try:
            assert self.group_depth == 0
            iod.undo()
        except iod.StackEmptyError:
            return False
        except iod.Error as e:
            print('Error undoing:', str(e))
            return False

        self.stacklen -= 2  # -2 to correct the +1 in update_view
        self._update_view()
        return True

    def try_redo(self) -> bool:
        try:
            assert self.group_depth == 0
            iod.redo()
        except iod.StackEmptyError:
            print('empty')
            return False
        except iod.Error as e:
            print('Error redoing:', str(e))
            return False

        self._update_view()
        return True

    @try_setter
    def try_add_node_g(self, neti: int, node: Node, programmatic: bool = False):
        '''
        Add node represented by the given Node variable.

        The 'g' suffix indicates that this operation creates its own group
        '''
        self.try_start_group()
        iod.addNode(neti, node.id_, node.position.x, node.position.y, node.size.x, node.size.y)
        nodei = iod.getNodeIndex(neti, node.id_)
        iod.setNodeFillColorAlpha(neti, nodei, node.fill_color.Alpha() / 255)
        iod.setNodeFillColorRGB(neti, nodei, node.fill_color.Red(),
                                node.fill_color.Green(), node.fill_color.Blue())
        iod.setNodeOutlineColorAlpha(neti, nodei, node.border_color.Alpha() / 255)
        iod.setNodeOutlineColorRGB(neti, nodei, node.border_color.Red(),
                                    node.border_color.Green(), node.border_color.Blue())
        iod.setNodeOutlineThickness(neti, nodei, int(node.border_width))

        if not programmatic:
            post_event(DidAddNodeEvent(node))
        self.try_end_group()

    @try_setter
    def try_move_node(self, neti: int, nodei: int, pos: Vec2, programmatic: bool = False):
        assert pos.x >= 0 and pos.y >= 0
        iod.setNodeCoordinate(neti, nodei, pos.x, pos.y)
        # dispatch event if the call was caused by user input
        if not programmatic:
            post_event(DidCommitNodePositionsEvent())

    @try_setter
    def try_set_node_size(self, neti: int, nodei: int, size: Vec2):
        iod.setNodeSize(neti, nodei, size.x, size.y)

    @try_setter
    def try_rename_node(self, neti: int, nodei: int, new_id: str):
        iod.setNodeID(neti, nodei, new_id)

    @try_setter
    def try_set_node_fill_rgb(self, neti: int, nodei: int, color: wx.Colour):
        iod.setNodeFillColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())

    @try_setter
    def try_set_node_fill_alpha(self, neti: int, nodei: int, alpha: int):
        iod.setNodeFillColorAlpha(neti, nodei, alpha / 255)

    @try_setter
    def try_set_node_border_rgb(self, neti: int, nodei: int, color: wx.Colour):
        iod.setNodeOutlineColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())

    @try_setter
    def try_set_node_border_alpha(self, neti: int, nodei: int, alpha: int):
        iod.setNodeOutlineColorAlpha(neti, nodei, alpha / 255)

    @try_setter
    def try_rename_reaction(self, neti: int, reai: int, new_id: str):
        iod.setReactionID(neti, reai, new_id)

    @try_setter
    def try_set_reaction_fill_rgb(self, neti: int, reai: int, color: wx.Colour):
        iod.setReactionFillColorRGB(neti, reai, color.Red(), color.Green(), color.Blue())

    @try_setter
    def try_set_reaction_fill_alpha(self, neti: int, reai: int, alpha: int):
        iod.setReactionFillColorAlpha(neti, reai, alpha / 255)

    @try_setter
    def try_set_node_border_width(self, neti: int, nodei: int, width: float):
        iod.setNodeOutlineThickness(neti, nodei, width)

    @try_setter
    def try_delete_node(self, neti: int, nodei: int):
        iod.deleteNode(neti, nodei)

    @try_setter
    def try_add_reaction_g(self, neti: int, reaction: Reaction):
        """Try create a reaction."""
        self.try_start_group()
        iod.createReaction(neti, reaction.id_)
        reai = iod.getReactionIndex(neti, reaction.id_)

        for src in reaction.sources:
            iod.addSrcNode(neti, reai, src.index, 1.0)

        for tar in reaction.targets:
            iod.addDestNode(neti, reai, tar.index, 1.0)

        iod.setReactionFillColorRGB(neti, reai,
                                    reaction.fill_color.Red(),
                                    reaction.fill_color.Green(),
                                    reaction.fill_color.Blue())
        for bez, node in zip(reaction.bezier.src_beziers, reaction.sources):
            pos = bez.handle.position
            iod.setReactionSrcNodeHandlePosition(neti, reai, node.id_, pos.x, pos.y)
        for bez, node in zip(reaction.bezier.dest_beziers, reaction.targets):
            pos = bez.handle.position
            iod.setReactionDestNodeHandlePosition(neti, reai, node.id_, pos.x, pos.y)

        cpos = reaction.bezier.src_c_handle.position
        iod.setReactionCenterHandlePosition(neti, reai, cpos.x, cpos.y)
        self.try_end_group()

    @try_setter
    def try_set_reaction_ratelaw(self, neti: int, reai: int, ratelaw: str):
        iod.setRateLaw(neti, reai, ratelaw)

    @try_setter
    def try_set_src_node_stoich(self, neti: int, reai: int, node_id: str, stoich: float):
        iod.setReactionSrcNodeStoich(neti, reai, node_id, stoich)

    @try_setter
    def try_set_dest_node_stoich(self, neti: int, reai: int, node_id: str, stoich: float):
        iod.setReactionDestNodeStoich(neti, reai, node_id, stoich)

    @try_setter
    def try_set_src_node_handle(self, neti: int, reai: int, node_id: str, pos: Vec2):
        iod.setReactionSrcNodeHandlePosition(neti, reai, node_id, pos.x, pos.y)

    @try_setter
    def try_set_dest_node_handle(self, neti: int, reai: int, node_id: str, pos: Vec2):
        iod.setReactionDestNodeHandlePosition(neti, reai, node_id, pos.x, pos.y)

    @try_setter
    def try_set_center_handle(self, neti: int, reai: int, pos: Vec2):
        iod.setReactionCenterHandlePosition(neti, reai, pos.x, pos.y)

    def get_src_node_handle(self, neti: int, reai: int, node_id: str) -> Vec2:
        return Vec2(iod.getReactionSrcNodeHandlePosition(neti, reai, node_id))

    def get_dest_node_handle(self, neti: int, reai: int, node_id: str) -> Vec2:
        return Vec2(iod.getReactionDestNodeHandlePosition(neti, reai, node_id))

    def get_center_handle(self, neti: int, reai: int) -> Vec2:
        return Vec2(iod.getReactionCenterHandlePosition(neti, reai))

    def get_src_node_stoich(self, neti: int, reai: int, node_id: str):
        return iod.getReactionSrcNodeStoich(neti, reai, node_id)

    def get_dest_node_stoich(self, neti: int, reai: int, node_id: str):
        return iod.getReactionDestNodeStoich(neti, reai, node_id)

    def get_list_of_src_ids(self, neti: int, reai: int):
        return iod.getListOfReactionSrcNodes(neti, reai)

    def get_list_of_dest_ids(self, neti: int, reai: int):
        return iod.getListOfReactionDestNodes(neti, reai)

    def get_list_of_node_ids(self, neti: int) -> List[str]:
        return iod.getListOfNodeIDs(neti)

    def get_node_index(self, neti: int, node_id: str) -> int:
        return iod.getNodeIndex(neti, node_id)

    def get_reaction_index(self, neti: int, rxn_id: str) -> int:
        return iod.getReactionIndex(neti, rxn_id)

    # get the updated list of nodes from model and update
    def _update_view(self):
        """tell the view to update by re-populating its list of nodes."""
        self.stacklen += 1  # TODO remove once fixed
        neti = 0
        nodes = list()
        reactions = list()
        for id_ in iod.getListOfNodeIDs(neti):
            nodei = iod.getNodeIndex(neti, id_)
            x, y, w, h = iod.getNodeCoordinateAndSize(neti, nodei)
            fill_alpha = iod.getNodeFillColorAlpha(neti, nodei)
            fill_rgb = iod.getNodeFillColorRGB(neti, nodei)
            fill_color = rgba_to_wx_colour(fill_rgb, fill_alpha)
            border_alpha = iod.getNodeOutlineColorAlpha(neti, nodei)
            border_rgb = iod.getNodeOutlineColorRGB(neti, nodei)
            border_color = rgba_to_wx_colour(border_rgb, border_alpha)
            node = Node(
                id_,
                index=nodei,
                pos=Vec2(x, y),
                size=Vec2(w, h),
                fill_color=fill_color,
                border_color=border_color,
                border_width=iod.getNodeOutlineThickness(neti, nodei),
            )
            nodes.append(node)

        for id_ in iod.getListOfReactionIDs(neti):
            reai = iod.getReactionIndex(neti, id_)
            sids = iod.getListOfReactionSrcNodes(neti, reai)
            sources = get_nodes_by_ident(nodes, sids)
            tids = iod.getListOfReactionDestNodes(neti, reai)
            targets = get_nodes_by_ident(nodes, tids)
            fill_rgb = iod.getReactionFillColorRGB(neti, reai)
            fill_alpha = iod.getReactionFillColorAlpha(neti, reai)

            items = list()
            items.append(self.get_center_handle(neti, reai))
            for node in sources:
                items.append(self.get_src_node_handle(neti, reai, node.id_))
            for node in targets:
                items.append(self.get_dest_node_handle(neti, reai, node.id_))

            reaction = Reaction(id_,
                                sources=sources,
                                targets=targets,
                                fill_color=rgba_to_wx_colour(fill_rgb, fill_alpha),
                                index=reai,
                                rate_law=iod.getReactionRateLaw(neti, reai),
                                handle_pos=items
                                )
            reactions.append(reaction)

        self.view.update_all(nodes, reactions)
