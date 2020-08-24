# pylint: disable=maybe-no-member
import wx  # Only for getting access to wx.MessageBox
from dataclasses import dataclass
import math
from typing import List

# f = open( 'c:\\tmp\\file.txt', 'a')
# f .write( 'dataX = ' + repr(BezPoints) + '\n' )
# f.close()
# wx.MessageBox('data = ' + str (99), 'Info', wx.OK | wx.ICON_INFORMATION)

MAXSEGS = 29  # Number of segments used to construct bezier
HANDLE_RADIUS = 3  # Radius of the contro lhandle
HANDLE_BUFFER = 2
NODE_EDGE_GAP_DISTANCE = 4  # Distance between node and start of bezier line


@dataclass
class TPointF:   # A 2D point
    x: float
    y: float


@dataclass
class TLineSegment:  # A line segment
    p: TPointF
    q: TPointF


class TBezierCurve:  # A Bezier curve
    def __init__(self):
        self.h1 = TPointF(0.0, 0.0)
        self.h2 = TPointF(0.0, 0.0)


# Array 1 to 4 of TLineSegment
# We don't use the first one, legacy form original code
squareSegments = [TLineSegment(TPointF(0, 0), TPointF(0, 0)),
                  TLineSegment(TPointF(0, 0), TPointF(0, 0)),
                  TLineSegment(TPointF(0, 0), TPointF(0, 0)),
                  TLineSegment(TPointF(0, 0), TPointF(0, 0)),
                  TLineSegment(TPointF(0, 0), TPointF(0, 0))]

# Some pre-sized array to hold data on bezier curves
BezierPoints = [TPointF(0.0, 0.0) for j in range(MAXSEGS+1)]


def getCenterPt(node):
    return TPointF(node.x + node.w / 2, node.y + node.h / 2)


# Find angle between x and y
def angle(x, y):
    if abs(x) < 1e-5:
        if abs(y) < 1e-5:
            return 0.0
        else:
            if y > 0.0:
                return math.pi * 0.5
            else:
                return math.pi * 1.5
    else:
        if x < 0.0:
            return math.atan2(y, x) + math.pi
        else:
            return math.atan2(y, x)


# Compute the centroid between two nodes
# Note this will also work for any number of nodes, just pass more nodes and
# change nSrcNode and nDestNodes
# Return the value of the centriod
def computeCentroid(node1, node2):

    # Number of nodes that go into the reaction
    nSrcNodes = 1
    # Number of nodes that come off the arc
    nDestNodes = 1

    # Calculate the centroid from the nodes associated with the reaction
    arcCentre = TPointF(0, 0)

    for i in range(nSrcNodes):
        pt = getCenterPt(node1)
        arcCentre.x = arcCentre.x + pt.x
        arcCentre.y = arcCentre.y + pt.y

    for i in range(nDestNodes):
        pt = getCenterPt(node2)
        arcCentre.x = arcCentre.x + pt.x
        arcCentre.y = arcCentre.y + pt.y

    totalNodes = nSrcNodes + nDestNodes
    return TPointF(arcCentre.x / totalNodes, arcCentre.y / totalNodes)


# Combination function. For some reason in Python Comb is stored in itertools
# If we move to Python 3.8 we can use math.comb
# Note this doesn't have to be efficient because we're just using this to compute
# the bezier blending functions once.
def Comb(n: int, i: int):
    return math.factorial(n) / (math.factorial(i) * math.factorial(n-i))


# Compute the Bezier blending functions here, ready for when we need them
# Assume 2 control points, MAXSEGS is number of steps to draw bezier curve

# Stores the blending function values
def zeros2d(n_rows, n_cols) -> List[List[float]]:
    ret = [None] * n_rows
    for i in range(n_rows):
        ret[i] = [0] * n_cols

    return ret


#BezJ = np.zeros ((MAXSEGS+1, 5))
BezJ = zeros2d(MAXSEGS + 1, 5)
#BezJPrime = np.zeros ((MAXSEGS+1, 5))
BezJPrime = zeros2d(MAXSEGS + 1, 5)


def computeBezierBlendingFunctions():
    for ti in range(MAXSEGS+1):
        t = ti/MAXSEGS
        for i in range(4):  # i = 0, 1, 2, 3
            BezJ[ti][i] = Comb(3, i) * math.pow(t, i) * math.pow(1-t, 3-i)
        # At the moment hard-wired for n = 3
        tm = 1 - t
        BezJPrime[ti][0] = -3*tm*tm
        BezJPrime[ti][1] = 3*tm*tm - 6*t*tm
        BezJPrime[ti][2] = 6*t*tm - 3*t*t
        BezJPrime[ti][3] = 3*t*t


# Prebuild this array for efficiency, used for intermediate bezier poinst calculations
tmpBezierPoints = [TPointF(0.0, 0.0) for i in range(MAXSEGS+1)]

# Compute points along bezier curve and store in global variable BezierPoints
# p is a list that holds the start, two control points and end point


def computeBezierPoints(p):
    # Scale up dimensions (mult by 1000) to get a smooth curve
    # Now compute the bezier points
    for i in range(MAXSEGS+1):
        tmpBezierPoints[i].x = 0
        tmpBezierPoints[i].y = 0
        for j in range(4):
            tmpBezierPoints[i].x = tmpBezierPoints[i].x + ((p[j].x * 1000)*BezJ[i][j])
            tmpBezierPoints[i].y = tmpBezierPoints[i].y + ((p[j].y * 1000)*BezJ[i][j])

        # and scale back down again
        BezierPoints[i].x = tmpBezierPoints[i].x / 1000
        BezierPoints[i].y = tmpBezierPoints[i].y / 1000

 # Note sure what this was for, doens't seem to be needed.
 # c = MAXSEGS // 2   # Integer division
 # return BezierPoints[c]


# Construct the outer rectangle segments which forms the
# boundary where arcs start and stop at nodes.
def computeOuterSegs(node):

    tx = node.x
    ty = node.y
    tw = node.w
    th = node.h

    gap = NODE_EDGE_GAP_DISTANCE

    squareSegments[1].p.x = tx - gap
    squareSegments[1].p.y = ty - gap
    squareSegments[1].q.x = tx + tw + gap
    squareSegments[1].q.y = ty - gap

    squareSegments[2].p.x = tx + tw + gap
    squareSegments[2].p.y = ty - gap
    squareSegments[2].q.x = tx + tw + gap
    squareSegments[2].q.y = ty + th + gap

    squareSegments[3].p.x = tx + tw + gap
    squareSegments[3].p.y = ty + th + gap
    squareSegments[3].q.x = tx - gap
    squareSegments[3].q.y = ty + th + gap

    squareSegments[4].p.x = tx - gap
    squareSegments[4].p.y = ty + th + gap
    squareSegments[4].q.x = tx - gap
    squareSegments[4].q.y = ty - gap

    return squareSegments


# Check if the target line (v2) intersects the SEGMENT line (v1). Returns
# true if lines intersect with intersection coordinate returned in v, else
# returns false
# Returns True/False and v
def segmentIntersects(v1: TPointF, v2: TPointF):  # Returns TPointF, v1 and v2 : TLineSegment

    xlk = v2.q.x - v2.p.x
    ylk = v2.q.y - v2.p.y
    xnm = v1.p.x - v1.q.x
    ynm = v1.p.y - v1.q.y
    xmk = v1.q.x - v2.p.x
    ymk = v1.q.y - v2.p.y

    det = xnm*ylk - ynm*xlk
    if abs(det) < 1e-6:
        return False, 0
    else:
        detinv = 1.0/det
        s = (xnm*ymk - ynm*xmk)*detinv
        t = (xlk*ymk - ylk*xmk)*detinv
        if (s < 0.0) or (s > 1.0) or (t < 0.0) or (t > 1.0):
            return False, 0
        else:
            v = TPointF(0, 0)
            v.x = v2.p.x + xlk*s
            v.y = v2.p.y + ylk*s
            return True, v


# Prebuild this lineSegment fvariable or efficiecny purposes.
BezierSegment = TLineSegment(TPointF(0, 0), TPointF(0, 0))

# Returns True/False, pointersection point (pt), segment number (segn) and relative position


def computeBezLineIntersection(node):
    # Construct the outer rectangle for the node
    outerSegs = computeOuterSegs(node)

    for segn in range(1, MAXSEGS+1):
        relPosn = segn / MAXSEGS
        BezierSegment.p = BezierPoints[segn - 1]
        BezierSegment.q = BezierPoints[segn]
        for j in range(1, 4+1):
            isIntersects, pt = segmentIntersects(outerSegs[j], BezierSegment)
            if isIntersects:
                return True, pt, segn, relPosn
    return False, 0, 0, 0


# p is a list of bezier control and start/stop points (start, h1, h2, stop)
def drawBezier(dc, p):
    computeBezierPoints(p)

    gc = wx.GraphicsContext.Create(dc)
    gc.SetPen(wx.Pen(wx.BLACK, 2))
    path = gc.CreatePath()
    path.MoveToPoint(BezierPoints[0].x, BezierPoints[0].y)
    for i in range(1, MAXSEGS+1):
        path.AddLineToPoint(BezierPoints[i].x, BezierPoints[i].y)
    gc.StrokePath(path)


LINE_HIT_BREADTH = 5
# Returns true if pt is on the line p1 to p2. The constant
# LINE_HIT_BREADTH is the slack on either side of the line,
# means users don't have to be super precise when selecting a line


def PtOnLine(p1, p2, pt):

    Deltax = p2.x - p1.x
    Deltay = p2.y - p1.y

    if (abs(Deltax) > 0) and (abs(Deltay) < abs(Deltax)):
        t = (pt.x - p1.x)/(p2.x - p1.x)
        if (t >= 0) and (t <= 1):
            y = p1.y + (p2.y - p1.y)*t
            if (y - LINE_HIT_BREADTH <= pt.y) and (pt.y <= y + LINE_HIT_BREADTH):
                return True
        else:
            return False
    else:
        if abs(Deltay) > 0:
            t = (pt.y - p1.y)/(p2.y - p1.y)
            if (t >= 0) and (t <= 1):
                x = p1.x + (p2.x - p1.x)*t
                if (x - LINE_HIT_BREADTH <= pt.x) and (pt.x <= x + LINE_HIT_BREADTH):
                    return True
            else:
                return False
        else:
            return False
    return False


# Is a point in a rectangle?
def PtInRect(x, y, w, h, p):
    return (p.x >= x) and (p.x < x + w) and (p.y >= y) and (p.y < y + h)


# Check if pt is within a circle with centre x, y
# Bit of a fudge, assumes a circle is a square!
# Circle is assumed to have a 'radius' of HANDLE_RADIUS
def PtWithinCircle(x, y, pt):
    r = HANDLE_RADIUS + HANDLE_BUFFER
    if PtInRect(pt.x-r, pt.y-r, 2*r, 2*r, TPointF(x, y)):
        return True
    else:
        return False


# Determine whether the point 'pt' is on the bezier curve defined by the
# control points 'p' (start, h1, h2, end). This brute force method works through
# each segment making up the bezier curve checking to see if pt in on one of
# the segments - seems to be quick enough. t is the parametric distance along
# the bezier
# Returns True/False and the parametric distance (0 to 1)

# Prebuild these array for efficiency, used for intermediate bezier point calculations
tmpOnBezier = [TPointF(0.0, 0.0) for i in range(MAXSEGS+1)]

finalBezPoints = [TPointF(0.0, 0.0) for j in range(MAXSEGS+1)]


def PtOnBezier(p, pt):

    # Scale up dimensions to get smooth curve
    # Compute the first point because later on I pass i-1 point to PtOnLine
    tmpOnBezier[0].x = 0
    tmpOnBezier[0].y = 0
    for j in range(4):
        tmpOnBezier[0].x = tmpOnBezier[0].x + (p[j].x * 1000)*BezJ[0][j]
        tmpOnBezier[0].y = tmpOnBezier[0].y + (p[j].y * 1000)*BezJ[0][j]

    finalBezPoints[0].x = tmpOnBezier[0].x / 1000
    finalBezPoints[0].y = tmpOnBezier[0].y / 1000

    for i in range(1, MAXSEGS+1):
        tmpOnBezier[i].x = 0
        tmpOnBezier[i].y = 0
        for j in range(4):
            tmpOnBezier[i].x = tmpOnBezier[i].x + (p[j].x * 1000)*BezJ[i][j]
            tmpOnBezier[i].y = tmpOnBezier[i].y + (p[j].y * 1000)*BezJ[i][j]

        finalBezPoints[i].x = tmpOnBezier[i].x / 1000
        finalBezPoints[i].y = tmpOnBezier[i].y / 1000
        # Check if pt in on the line segment, i-1 to i
        if PtOnLine(finalBezPoints[i-1], finalBezPoints[i], pt):
            return True, i/MAXSEGS
    return False, 0


# Find out whether the x, y coordinate is on either
# the h1 or h2 control handles
# Returns True/False as well as the handleID (0 or 1) and the coordinates of the handle
def checkParticularBezierCurve(x, y, h1, h2):

    if PtWithinCircle(x, y, h1):
        handleId = 0
        hcoords = h1
        return True, handleId, hcoords
    else:
        if PtWithinCircle(x, y, h2):
            handleId = 1
            hcoords = h2
            return True, handleId, hcoords
        else:
            handleId = -1
            return False, handleId, 0


# Draw the bezier control points
def drawBezierHandles(dc, p):  # : array of TPointF);

    try:
        gc = wx.GraphicsContext.Create(dc)

        c = wx.Colour(0, 102, 204, 255)
        brush = wx.Brush(c)
        pen = wx.Pen(c)

        gc.SetPen(pen)
        # Draw smooth lines
        path = gc.CreatePath()
        path.MoveToPoint(p[0].x, p[0].y)
        path.AddLineToPoint(p[1].x, p[1].y)

        path.MoveToPoint(p[2].x, p[2].y)
        path.AddLineToPoint(p[3].x, p[3].y)
        gc.StrokePath(path)

        gc.SetBrush(brush)
        gc.DrawEllipse(p[1].x - HANDLE_RADIUS, p[1].y - HANDLE_RADIUS,
                       2*HANDLE_RADIUS, 2*HANDLE_RADIUS)
        gc.DrawEllipse(p[2].x - HANDLE_RADIUS, p[2].y - HANDLE_RADIUS,
                       2*HANDLE_RADIUS, 2*HANDLE_RADIUS)

    finally:
        gc.SetPen(wx.BLACK_PEN)


# The last point is the tip  of the arrow, the lst point then joins up with the first point
DEFAULT_ARROW_TIP = [TPointF(0, 14), TPointF(3, 7), TPointF(0, 0), TPointF(20, 7)]
arrowTipPoints = [TPointF(0.0, 0.0) for i in range(4)]
arrowTipFinalCoordinates = [(0.0, 0.0) for i in range(4)]
tipDisplacement = 4


def createDefaultArrowTip():

    for i in range(4):
        arrowTipPoints[i] = DEFAULT_ARROW_TIP[i]


# def paintArrowTip (oEdge: TObject; tip : TPointF; dxdt, dydt : Double):
def paintArrowTip(dc, tip, dxdt, dydt):

    alpha = -angle(dxdt, dydt)
    cosine = math.cos(alpha)
    sine = math.sin(alpha)

    # Adjust the tip so that it moves forward slightly
    adX = tipDisplacement * math.cos(-alpha)
    adY = tipDisplacement * math.sin(-alpha)
    tip.x = tip.x + adX
    tip.y = tip.y + adY

    # DrawPolygon expects the following type of points array [(x1,y1), (x2,y2), (x3,y3), etc]

    # Rotate the arrow into the correct orientation
    arrowTipFinalCoordinates[0] = (arrowTipPoints[0].x * cosine + arrowTipPoints[0].y * sine,
                                   -arrowTipPoints[0].x * sine + arrowTipPoints[0].y * cosine)

    arrowTipFinalCoordinates[1] = (arrowTipPoints[1].x * cosine + arrowTipPoints[1].y * sine,
                                   -arrowTipPoints[1].x * sine + arrowTipPoints[1].y * cosine)

    arrowTipFinalCoordinates[2] = (arrowTipPoints[2].x * cosine + arrowTipPoints[2].y * sine,
                                   -arrowTipPoints[2].x * sine + arrowTipPoints[2].y * cosine)

    arrowTipFinalCoordinates[3] = (arrowTipPoints[3].x * cosine + arrowTipPoints[3].y * sine,
                                   -arrowTipPoints[3].x * sine + arrowTipPoints[3].y * cosine)

    # Compute the distance of the tip of the arrow to the end point on the line
    # where the arrow should be placed. Then use this distance to translate the arrow
    dx = tip.x - arrowTipFinalCoordinates[3][0]
    dy = tip.y - arrowTipFinalCoordinates[3][1]

    # Translate the remaining coordinates of the arrow, note tip = Q
    arrowTipFinalCoordinates[0] = (arrowTipFinalCoordinates[0][0] + dx,
                                   arrowTipFinalCoordinates[0][1] + dy)  # S
    arrowTipFinalCoordinates[1] = (arrowTipFinalCoordinates[1][0] + dx,
                                   arrowTipFinalCoordinates[1][1] + dy)  # T
    arrowTipFinalCoordinates[2] = (arrowTipFinalCoordinates[2][0] + dx,
                                   arrowTipFinalCoordinates[2][1] + dy)  # Q
    arrowTipFinalCoordinates[3] = (tip.x, tip.y)

    c = wx.Colour(0, 0, 0, 255)
    dc.SetPen(wx.Pen(c))
    dc.SetBrush(wx.Brush(c))
    dc.DrawPolygon(arrowTipFinalCoordinates, 0, 0)
