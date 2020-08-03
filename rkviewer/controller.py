# pylint: disable=maybe-no-member
import wx
from typing import List
import IodineAPI as iod
from .types import Vec2, Node, IView, IController
from .utils import IodToWxColour


class Controller(IController):
    view: IView

    def __init__(self, view: IView):
        self.view = view
        iod.newNetwork('the one')

    def TryAddNode(self, node: Node) -> bool:
        '''
        Add node represented by the given Node variable.

        Returns whether the operation was successful.
        '''
        neti = 0
        # keep incrementing as long as there is duplicate ID
        # TODO change
        try:
            iod.addNode(neti, node.id_, node.position.x, node.position.y, node.size.x, node.size.y)
            nodei = iod.getNodeIndex(neti, node.id_)
            iod.setNodeFillColorAlpha(neti, nodei, node.fill_color.Alpha() / 255)
            iod.setNodeFillColorRGB(neti, nodei, node.fill_color.Red(), node.fill_color.Green(), node.fill_color.Blue())
        except iod.Error as e:
            print('Error:', str(e))
            return False

        self._UpdateView()
        return True

    def TryMoveNode(self, id_: str, pos: Vec2):
        neti = 0
        # TODO exception
        nodei = iod.getNodeIndex(neti, id_)
        iod.setNodeCoordinate(neti, nodei, pos.x, pos.y)
        self._UpdateView()

    def TrySetNodeSize(self, id_: str, size: Vec2):
        neti = 0
        # TODO exception
        nodei = iod.getNodeIndex(neti, id_)
        iod.setNodeSize(neti, nodei, size.x, size.y)
        self._UpdateView()

    def GetListOfNodeIds(self) -> List[str]:
        neti = 0
        return iod.getListOfNodeIds(neti)

    # get the updated list of nodes from model and update
    def _UpdateView(self):
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
            fill_color = IodToWxColour(fill_rgb, fill_alpha)
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

        self.view.UpdateAll(nodes)