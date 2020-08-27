"""Implementation of a controller.
"""
# pylint: disable=maybe-no-member
import wx
from typing import Collection, List, Optional, Set
import iodine as iod
from .utils import Vec2, Node, get_nodes_by_ident, get_nodes_by_idx, rgba_to_wx_colour
from .canvas.reactions import Reaction
from .mvc import IController, IView


def try_func(fn):
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
        # TODO record group depth
        try:
            iod.startGroup()
            self.group_depth += 1
        except iod.Error as e:
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
            return False
        except iod.Error as e:
            print('Error redoing:', str(e))
            return False

        self._update_view()
        return True

    @try_func
    def try_add_node_g(self, neti: int, node: Node):
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
        self.try_end_group()

    @try_func
    def try_move_node(self, neti: int, nodei: int, pos: Vec2):
        assert pos.x >= 0 and pos.y >= 0
        iod.setNodeCoordinate(neti, nodei, pos.x, pos.y)

    @try_func
    def try_set_node_size(self, neti: int, nodei: int, size: Vec2):
        iod.setNodeSize(neti, nodei, size.x, size.y)

    @try_func
    def try_rename_node(self, neti: int, nodei: int, new_id: str):
        iod.setNodeID(neti, nodei, new_id)

    @try_func
    def try_set_node_fill_rgb(self, neti: int, nodei: int, color: wx.Colour):
        iod.setNodeFillColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())

    @try_func
    def try_set_node_fill_alpha(self, neti: int, nodei: int, alpha: float):
        iod.setNodeFillColorAlpha(neti, nodei, alpha)

    @try_func
    def try_set_node_border_rgb(self, neti: int, nodei: int, color: wx.Colour):
        iod.setNodeOutlineColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())

    @try_func
    def try_set_node_border_alpha(self, neti: int, nodei: int, alpha: float):
        iod.setNodeOutlineColorAlpha(neti, nodei, alpha)

    @try_func
    def try_rename_reaction(self, neti: int, reai: int, new_id: str):
        iod.setReactionID(neti, reai, new_id)

    @try_func
    def try_set_reaction_fill_rgb(self, neti: int, reai: int, color: wx.Colour):
        iod.setReactionFillColorRGB(neti, reai, color.Red(), color.Green(), color.Blue())

    @try_func
    def try_set_reaction_fill_alpha(self, neti: int, reai: int, alpha: float):
        iod.setReactionFillColorAlpha(neti, reai, alpha)

    @try_func
    def try_set_node_border_width(self, neti: int, nodei: int, width: float):
        print('warning: TODO decide if node width is int or float')

    @try_func
    def try_delete_node(self, neti: int, nodei: int):
        iod.deleteNode(neti, nodei)

    @try_func
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
        self.try_end_group()

    @try_func
    def try_set_reaction_ratelaw(self, neti: int, reai: int, ratelaw: str):
        iod.setRateLaw(neti, reai, ratelaw)

    def get_list_of_node_ids(self, neti: int) -> List[str]:
        return iod.getListOfNodeIDs(neti)

    def get_node_index(self, neti: int, node_id: str) -> int:
        return iod.getNodeIndex(neti, node_id)

    # get the updated list of nodes from model and update
    def _update_view(self):
        """tell the view to update by re-populating its list of nodes."""
        self.stacklen += 1  # TODO remove
        # TODO multiple net IDs
        neti = 0
        nodes = list()
        reactions = list()
        # TODO try except
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
            reaction = Reaction(id_,
                                sources=sources,
                                targets=targets,
                                fill_color=rgba_to_wx_colour(fill_rgb, fill_alpha),
                                index=reai,
                                rate_law=iod.getReactionRateLaw(neti, reai)
                                )
            reactions.append(reaction)

        self.view.update_all(nodes, reactions)
