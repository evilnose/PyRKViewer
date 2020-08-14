"""Implementation of a controller.
"""
# pylint: disable=maybe-no-member
import wx
from typing import List
import iodine as iod
from .utils import Vec2, Node, rgba_to_wx_colour
from .mvc import IController, IView


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
        self.in_group = False
        self.stacklen = 0  # TODO temporary hack to not undo the first newNetwork() operation.

    def try_start_group(self) -> bool:
        assert not self.in_group
        try:
            iod.startGroup()
            self.in_group = True
        except iod.Error as e:
            print('Error starting group:', str(e))
            return False
        return True

    def try_end_group(self) -> bool:
        assert self.in_group
        try:
            iod.endGroup()
            self.in_group = False
        except iod.Error as e:
            print('Error ending group:', str(e))
            return False
        self._update_view()
        return True

    def try_undo(self) -> bool:
        if self.stacklen == 0:
            return False
        try:
            assert not self.in_group
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
            assert not self.in_group
            iod.redo()
        except iod.StackEmptyError:
            return False
        except iod.Error as e:
            print('Error redoing:', str(e))
            return False

        self._update_view()
        return True

    def try_add_node(self, node: Node) -> bool:
        '''
        Add node represented by the given Node variable.

        Returns whether the operation was successful.
        '''
        neti = 0
        try:
            # if this fails in case a group is already in place, modify startGroup to not start
            # group if already in group
            iod.startGroup()
            iod.addNode(neti, node.id_, node.position.x, node.position.y, node.size.x, node.size.y)
            nodei = iod.getNodeIndex(neti, node.id_)
            iod.setNodeFillColorAlpha(neti, nodei, node.fill_color.Alpha() / 255)
            iod.setNodeFillColorRGB(neti, nodei, node.fill_color.Red(),
                                    node.fill_color.Green(), node.fill_color.Blue())
            iod.setNodeOutlineColorAlpha(neti, nodei, node.border_color.Alpha() / 255)
            iod.setNodeOutlineColorRGB(neti, nodei, node.border_color.Red(),
                                    node.border_color.Green(), node.border_color.Blue())
            iod.setNodeOutlineThickness(neti, nodei, int(node.border_width))
            iod.endGroup()
        except iod.Error as e:
            print('Error adding node:', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True

    def try_move_node(self, id_: str, pos: Vec2) -> bool:
        assert pos.x >= 0 and pos.y >= 0
        neti = 0
        # TODO exception
        nodei = iod.getNodeIndex(neti, id_)
        try:
            iod.setNodeCoordinate(neti, nodei, pos.x, pos.y)
        except iod.Error as e:
            print('Error moving node:', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True

    def try_set_node_size(self, id_: str, size: Vec2) -> bool:
        neti = 0
        # TODO exception
        try:
            nodei = iod.getNodeIndex(neti, id_)
            iod.setNodeSize(neti, nodei, size.x, size.y)
        except iod.Error as e:
            print('Error resizing node:', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True

    def try_rename_node(self, old_id: str, new_id: str) -> bool:
        neti = 0
        try:
            nodei = iod.getNodeIndex(neti, old_id)
            iod.setNodeId(neti, nodei, new_id)
        except iod.Error as e:
            print('Error renaming node:', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True

    def try_set_node_fill_rgb(self, id_: str, color: wx.Colour) -> bool:
        neti = 0
        try:
            nodei = iod.getNodeIndex(neti, id_)
            iod.setNodeFillColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())
        except iod.Error as e:
            print('Error setting node fill color:', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True


    def try_set_node_fill_alpha(self, id_: str, alpha: float) -> bool:
        neti = 0
        try:
            nodei = iod.getNodeIndex(neti, id_)
            iod.setNodeFillColorAlpha(neti, nodei, alpha)
        except iod.Error as e:
            print('Error setting node fill alpha:', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True

    def try_set_node_border_rgb(self, id_: str, color: wx.Colour) -> bool:
        neti = 0
        try:
            nodei = iod.getNodeIndex(neti, id_)
            iod.setNodeOutlineColorRGB(neti, nodei, color.Red(), color.Green(), color.Blue())
        except iod.Error as e:
            print('Error setting node border color:', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True

    def try_set_node_border_alpha(self, id_: str, alpha: float) -> bool:
        neti = 0
        try:
            nodei = iod.getNodeIndex(neti, id_)
            iod.setNodeOutlineColorAlpha(neti, nodei, alpha)
        except iod.Error as e:
            print('Error setting node border alpha:', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True

    def try_set_node_border_width(self, id_: str, width: float) -> bool:
        neti = 0
        try:
            nodei = iod.getNodeIndex(neti, id_)
            print('warning: TODO decide if node width is int or float')
            iod.setNodeOutlineThickness(neti, nodei, int(width))
        except iod.Error as e:
            print('Error setting node border width', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True

    def try_delete_node(self, id_: str) -> bool:
        neti = 0
        try:
            nodei = iod.getNodeIndex(neti, id_)
            iod.deleteNode(neti, nodei)
        except iod.Error as e:
            print('Error deleting node:', str(e))
            return False

        if not self.in_group:
            self._update_view()
        return True

    def get_list_of_node_ids(self) -> List[str]:
        neti = 0
        return iod.getListOfNodeIds(neti)

    # get the updated list of nodes from model and update
    def _update_view(self):
        """tell the view to update by re-populating its list of nodes."""
        self.stacklen += 1  #TODO remove
        # TODO multiple net IDs
        neti = 0
        ids = iod.getListOfNodeIds(neti)
        nodes = list()
        # TODO try except
        for id_ in ids:
            nodei = iod.getNodeIndex(neti, id_)
            x, y, w, h = iod.getNodeCoordinateAndSize(neti, nodei)
            fill_alpha = iod.getNodeFillColorAlpha(neti, nodei)
            fill_rgb = iod.getNodeFillColorRGB(neti, nodei)
            fill_color = rgba_to_wx_colour(fill_rgb, fill_alpha)
            border_alpha = iod.getNodeOutlineColorAlpha(neti, nodei)
            border_rgb = iod.getNodeOutlineColorRGB(neti, nodei)
            border_color = rgba_to_wx_colour(border_rgb, border_alpha)
            node = Node(
                id_=id_,
                pos=Vec2(x, y),
                size=Vec2(w, h),
                fill_color=fill_color,
                border_color=border_color,
                border_width=iod.getNodeOutlineThickness(neti, nodei)
            )
            nodes.append(node)

        self.view.update_all(nodes)
