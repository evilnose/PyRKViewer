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

    def try_start_group(self) -> bool:
        try:
            iod.startGroup()
        except iod.Error as e:
            print('Error:', str(e))
            return False
        return True

    def try_end_group(self) -> bool:
        try:
            iod.endGroup()
        except iod.Error as e:
            print('Error:', str(e))
            return False
        return True

    def try_add_node(self, node: Node) -> bool:
        '''
        Add node represented by the given Node variable.

        Returns whether the operation was successful.
        '''
        neti = 0
        # keep incrementing as long as there is duplicate ID
        # TODO change
        try:
            iod.startGroup()
            iod.addNode(neti, node.id_, node.position.x, node.position.y, node.size.x, node.size.y)
            nodei = iod.getNodeIndex(neti, node.id_)
            iod.setNodeFillColorAlpha(neti, nodei, node.fill_color.Alpha() / 255)
            iod.setNodeFillColorRGB(neti, nodei, node.fill_color.Red(),
                                    node.fill_color.Green(), node.fill_color.Blue())
            iod.setNodeOutlineThickness(neti, nodei, node.border_width)
            iod.endGroup()
        except iod.Error as e:
            print('Error:', str(e))
            return False

        self._update_view()
        return True

    def try_move_node(self, id_: str, pos: Vec2) -> bool:
        neti = 0
        # TODO exception
        nodei = iod.getNodeIndex(neti, id_)
        try:
            iod.setNodeCoordinate(neti, nodei, pos.x, pos.y)
        except iod.Error as e:
            print('Error:', str(e))
            return False

        self._update_view()
        return True

    def try_set_node_size(self, id_: str, size: Vec2):
        neti = 0
        # TODO exception
        nodei = iod.getNodeIndex(neti, id_)
        iod.setNodeSize(neti, nodei, size.x, size.y)
        self._update_view()

    def get_list_of_node_ids(self) -> List[str]:
        neti = 0
        return iod.getListOfNodeIds(neti)

    # get the updated list of nodes from model and update
    def _update_view(self):
        """tell the view to update by re-populating its list of nodes."""
        # TODO multiple net IDs
        neti = 0
        ids = iod.getListOfNodeIds(neti)
        nodes = list()
        # TODO try except
        for id_ in ids:
            nodei = iod.getNodeIndex(neti, id_)
            x, y, w, h = iod.getNodeCoordinateAndSize(neti, nodei)
            fill_rgb = iod.getNodeFillColorRGB(neti, nodei)
            fill_alpha = iod.getNodeFillColorAlpha(neti, nodei)
            fill_color = rgba_to_wx_colour(fill_rgb, fill_alpha)
            # TODO don't hardcode border color and width
            node = Node(
                id_=id_,
                pos=Vec2(x, y),
                size=Vec2(w, h),
                fill_color=fill_color,
                border_color=wx.Colour(255, 0, 0, 255),
                border_width=1
            )
            nodes.append(node)

        self.view.update_all(nodes)
