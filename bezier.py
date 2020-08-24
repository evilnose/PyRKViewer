from dataclasses import dataclass
from graphicsUtils import *
import copy

MAXINTERSECTIONS = 20  # should ty to make this dynamic


@dataclass
class TNode:
    x: int
    y: int
    w: int
    h: int

# TArcDirection = (adInArc, adOutArc);  # Arc comes into the arc center or out of the arc center

# Enumerated type


@dataclass
class TActionMode:
    sSelect = 0
    sMovingBezierHandle = 1


class View(wx.Panel):
    def __init__(self, parent):
        super(View, self).__init__(parent)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_SIZE, self.onSize)
        self.Bind(wx.EVT_PAINT, self.onPaint)
        self.Bind(wx.EVT_MOVE, self.onMouseMove)
        self.Bind(wx.EVT_LEFT_DOWN, self.onMouseDown)
        self.Bind(wx.EVT_LEFT_UP, self.onMouseUp)
        self.Bind(wx.EVT_MOTION, self.onMouseMove)
        self.pi = [TPointF(0.0, 0.0) for j in range(MAXSEGS)]
        self.actionMode = TActionMode.sSelect
        self.SetDoubleBuffered(True)  # avoids flicker

        self.currentlySelectedControlHandle = 0
        self.currentlySelectedBezierCurve = 0
        self.reactionSelected = False

        self.intersectPt = [TPointF(0.0, 0.0) for j in range(MAXINTERSECTIONS+1)]

        createDefaultArrowTip()

    def onSize(self, event):
        event.Skip()
        self.Refresh()

    def onMouseDown(self, event):
        self.mouseDownFlag = True
        pos = event.GetPosition()

        # This is for moving a bezier handle. We need to know which bezier curve and which control handle was selected
        result, self.currentlySelectedBezierCurve, self.currentlySelectedControlHandle, HandleCoords = self.IsMouseOnBezierHandle(
            pos.x, pos.y)
        if result:
            self.OldX = pos.x - HandleCoords.x
            self.OldY = pos.y - HandleCoords.y
            self.actionMode = TActionMode.sMovingBezierHandle
            return

        result, bid = self.IsOnEdge(pos.x, pos.y)
        if result:
            self.reactionSelected = True
        else:
            self.reactionSelected = False
        self.Refresh()

    def onMouseMove(self, event):
        pos = event.GetPosition()
        if self.actionMode == TActionMode.sMovingBezierHandle:
            # Each bezier curve has two control handles, h1 and h2, update which ever is being moved
            if self.currentlySelectedControlHandle == 0:
                self.bezierCurves[self.currentlySelectedBezierCurve].h1.x = (pos.x - self.OldX)
                self.bezierCurves[self.currentlySelectedBezierCurve].h1.y = (pos.y - self.OldY)

            if self.currentlySelectedControlHandle == 1:
                self.bezierCurves[self.currentlySelectedBezierCurve].h2.x = (pos.x - self.OldX)
                self.bezierCurves[self.currentlySelectedBezierCurve].h2.y = (pos.y - self.OldY)

            self.adjustMovedBezierHandles()
            self.Refresh()

    def onMouseUp(self, event):
        self.mouseDownFlag = False
        self.actionMode = TActionMode.sSelect

    def onPaint(self, event):

        self.dc = wx.AutoBufferedPaintDC(self)
        self.dc.Clear()

        # Create paint DC
        self.dc = wx.PaintDC(self)
        self.dc.SetPen(wx.BLACK_PEN)
        # Create graphics context from it
        gc = wx.GraphicsContext.Create(self.dc)

        gc.SetPen(wx.BLACK_PEN)
        self.drawNode(self.node1)
        self.drawNode(self.node2)

        bezierCurveId = 0
        self.drawBezierToCentroid(self.dc, bezierCurveId, self.node1)
        bezierCurveId = 1
        self.drawBezierFromCentroid(self.dc, bezierCurveId, self.node2)

    # Check if the mouse in on a particular control handle, note that a reaction arc will be made
    # up of one or more bezier curves. Each bezier curve has two handles. This routine
    # will return the number Id of the particular bezier curve which includes the moused handle

    def IsMouseOnBezierHandle(self, x, y):

        # This would for loop over all the bezier curves that make upa reaction
        numOfBezierCurves = 2  # For a uni-uni reaction
        for bezierCurve in range(0, numOfBezierCurves - 1 + 1):

            h1 = self.bezierCurves[bezierCurve].h1
            h2 = self.bezierCurves[bezierCurve].h2
            # currentlySelectedControlHandle either returns 0 or 1, 0 for the first handle and 1 for the second one
            foundHandle, self.currentlySelectedControlHandle, handleCoords = checkParticularBezierCurve(
                x, y, h1, h2)

            if foundHandle:
                # We return the bezier curve number and the control handle selected
                return foundHandle, bezierCurve, self.currentlySelectedControlHandle, handleCoords
        # If we didn't hid a contro lhandle just return False
        return False, 0, 0, 0

    def IsOnEdge(self, x: float, y: float):

        pt1 = self.intersectPt[0]
        pt2 = self.arcCenter

        result, t = PtOnBezier([pt1, self.bezierCurves[0].h1,
                                self.bezierCurves[0].h2, pt2], TPointF(x, y))
        if result:
            bezierId = 0
            return True, bezierId

        pt1 = self.arcCenter
        pt2 = self.intersectPt[1]

        result, t = PtOnBezier([pt1, self.bezierCurves[1].h1,
                                self.bezierCurves[1].h2, pt2], TPointF(x, y))
        if result:
            bezierId = 1
            return True, bezierId

        return False, 0

    # If the contol handles have been moved make sure they look nice
    # This routine should work not matter how many bezier curves make up a reaction
    def adjustMovedBezierHandles(self):
        subArcSeg = self.bezierCurves[self.currentlySelectedBezierCurve]

        nReactants = 1
        nProducts = 1
        if self.currentlySelectedBezierCurve < nReactants:
            for i in range(nReactants):
                self.bezierCurves[i].h2 = subArcSeg.h2

            bnx = self.arcCenter.x
            bny = self.arcCenter.y
            bn_1x = self.bezierCurves[0].h2.x
            bn_1y = self.bezierCurves[0].h2.y

            for i in range(nReactants, nReactants + nProducts):
                self.bezierCurves[i].h1.x = 2*bnx - bn_1x
                self.bezierCurves[i].h1.y = 2*bny - bn_1y
        else:
            for i in range(nReactants, nReactants + nProducts):
                self.bezierCurves[i].h1 = subArcSeg.h1

            bnx = self.arcCenter.x
            bny = self.arcCenter.y
            c1x = self.bezierCurves[nReactants].h1.x
            c1y = self.bezierCurves[nReactants].h1.y

            for i in range(nReactants):
                self.bezierCurves[i].h2.x = 2*bnx - c1x
                self.bezierCurves[i].h2.y = 2*bny - c1y

    def drawNode(self, node):
        gc = wx.GraphicsContext.Create(self.dc)
        gc.SetPen(wx.BLACK_PEN)
        gc.DrawRoundedRectangle(node.x, node.y, node.w, node.h, 8)

    # bezierCurveId is a number form 0 to how many bezier curves there are.
    # This routine will draw the bezierCurveId_th curve. For a uni-uni this would be zero
    def drawBezierToCentroid(self, dc, bezierCurveId, node):

        # Get the bezier control handle coordinates for the bezier curve
        h1 = TPointF(self.bezierCurves[bezierCurveId].h1.x, self.bezierCurves[bezierCurveId].h1.y)
        h2 = TPointF(self.bezierCurves[bezierCurveId].h2.x, self.bezierCurves[bezierCurveId].h2.y)

        # We will draw a bezier curve form the node to the reaction center (called arcCenter)
        # First calculate the centre of the src node, then get the arc center
        pSrc = getCenterPt(node)
        pDest = TPointF(self.arcCenter.x, self.arcCenter.y)

        # Compute the points along the bezier from node center to arc center
        computeBezierPoints([pSrc, h1, h2, pDest])

        # Clip the src starting point by returning the bezier segment number which intersects with the node outer rectangle
        # relPosn is a number between 0 and 1 and gives the relative position of intersection point
        # pSrct is the intersection point
        # segn is the segment number at this the intersection occured (bezier is made of MAXSEGS segments)
        result, pSrc, segn, relPosn = computeBezLineIntersection(node)
        if result:
            self.intersectPt[bezierCurveId] = copy.copy(pSrc)
            drawBezier(dc, [pSrc, h1, h2, pDest])
        if self.reactionSelected:
            drawBezierHandles(dc, [pSrc, h1, h2, self.arcCenter])

    def drawBezierFromCentroid(self, dc, bezierCurveId, node):

        # This time we're going to draw from the arcCenter to the destination node
        h1 = self.bezierCurves[bezierCurveId].h1
        h2 = self.bezierCurves[bezierCurveId].h2

        pSrc = TPointF(self.arcCenter.x, self.arcCenter.y)

        computeBezierPoints([self.arcCenter, h1, h2, getCenterPt(node)])

        result, pDest, segn, relPosn = computeBezLineIntersection(node)

        if result:
            # Move the end point slightly back (along the slope of the line) to make room for the arrow
            alpha = angle(pDest.x - h2.x, pDest.y - h2.y)
            adX = 8 * math.cos(alpha)
            adY = 8 * math.sin(alpha)
            adX = pDest.x - adX
            adY = pDest.y - adY

            self.intersectPt[bezierCurveId] = copy.copy(pDest)

            drawBezier(dc, [self.arcCenter, h1, h2, TPointF(adX, adY)])
    #      //if arrowTip.visible then
        paintArrowTip(dc, pDest, pDest.x - h2.x, pDest.y - h2.y)  # dxdt, dydt
        if self.reactionSelected:
            drawBezierHandles(dc, [self.arcCenter, h1, h2, pDest])


class Frame(wx.Frame):
    def __init__(self):
        super(Frame, self).__init__(None)
        self.setUpNodes()
        computeBezierBlendingFunctions()
        self.SetTitle('My Title')
        self.SetClientSize((600, 500))
        self.Center()
        self.view = View(self)
        self.view.node1 = self.node1
        self.view.node2 = self.node2
        self.view.bezierCurves = self.bezierCurves
        self.view.arcCenter = self.arcCenter

    def setUpNodes(self):
        self.node1 = TNode(100, 100, 50, 30)
        self.node2 = TNode(350, 250, 50, 30)
        src = getCenterPt(self.node1)
        dest = getCenterPt(self.node2)

        self.arcCenter = computeCentroid(self.node1, self.node2)

        self.bezierCurves = []
        self.bezierCurves.append(TBezierCurve())
        self.bezierCurves.append(TBezierCurve())

        self.bezierCurves[0].h1.x = (src.x + (self.arcCenter.x - src.x) / 2)
        self.bezierCurves[0].h1.y = (src.y + (self.arcCenter.y - src.y) / 2)

        self.bezierCurves[0].h2.x = self.bezierCurves[0].h1.x
        self.bezierCurves[0].h2.y = self.bezierCurves[0].h1.y

        self.bezierCurves[0].h2.x += 20
        self.bezierCurves[0].h2.y -= 20

        cx = self.arcCenter.x
        cy = self.arcCenter.y

        # Make h1 handles on SubArcs 2 colinear with h2 on SubArc 1
        self.bezierCurves[1].h1.x = 2*cx - self.bezierCurves[0].h2.x
        self.bezierCurves[1].h1.y = 2*cy - self.bezierCurves[0].h2.y

        self.bezierCurves[1].h2.x = self.bezierCurves[1].h1.x
        self.bezierCurves[1].h2.y = self.bezierCurves[1].h1.y

        self.bezierCurves[1].h2.x += 20
        self.bezierCurves[1].h2.y -= 20


def main():
    app = wx.App(False)
    frame = Frame()
    frame.Show()
    app.MainLoop()


main()
