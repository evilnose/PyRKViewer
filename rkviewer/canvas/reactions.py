"""Module for drawing Bezier curves and handling user input on Bezier curves.

Note that if new nodes are constructed, all ReactionBezier instances that use these nodes should be
re-constructed with the new nodes. On the other hand, if the nodes are merely modified, the
corresponding update methods should be called.
"""
# pylint: disable=maybe-no-member
import wx
from dataclasses import dataclass
from enum import Enum
import math
from itertools import chain
from typing import Callable, List, Optional, Tuple
from ..utils import Node, Vec2, clamp_point_outside, pairwise
from .utils import padded_rect, within_rect


MAXSEGS = 29  # Number of segments used to construct bezier
HANDLE_RADIUS = 3  # Radius of the contro lhandle
HANDLE_BUFFER = 2
NODE_EDGE_GAP_DISTANCE = 4  # Distance between node and start of bezier line
TIP_DISPLACEMENT = 4
DEFAULT_ARROW_TIP = [Vec2(0, 14), Vec2(3, 7), Vec2(0, 0), Vec2(20, 7)]
arrowTipPoints = DEFAULT_ARROW_TIP


ToScrolledFn = Callable[[Vec2], Vec2]


def zeros2d(n_rows, n_cols) -> List[List[float]]:
    """Return a 2D list of zeros with dimensions (n_rows, n_cols).
    """
    ret = [None] * n_rows
    for i in range(n_rows):
        ret[i] = [0] * n_cols

    return ret


# TODO OPTIMIZE. scipy has function that computes this but it seems like an overkill, since scipy
# would probably double the size of the executable.
# Also can solve this easily by upgrading to Python 3.8, which has a built-in comb method.
def comb(n: int, i: int):
    return math.factorial(n) / (math.factorial(i) * math.factorial(n-i))


def compute_centroid(reactants: List[Node], products: List[Node]) -> Vec2:
    total = sum((n.center_point for n in chain(reactants, products)), Vec2())
    return total / (len(reactants) + len(products))


# TODO move the following to a geometry module, along with Vec2
def pt_on_line(a: Vec2, b: Vec2, point: Vec2, threshold: float = 0) -> bool:
    delta = b - a
    b_comp_sq = delta.norm_sq
    direction = delta.normalized()
    ap = point - a
    comp = ap.dot(direction)

    # projection not on the line
    if comp < 0 or comp * comp > b_comp_sq:
        return False

    projected = a + comp * direction
    return (point - projected).norm_sq <= threshold ** 2


def pt_in_circle(center: Vec2, radius: float, point: Vec2) -> bool:
    return (point - center).norm_sq <= radius ** 2


class Orientation(Enum):
    CLOCKWISE = 0
    COUNTERCLOCKWISE = 1
    COLINEAR = 2


def determinant(v1: Vec2, v2: Vec2):
    return v1.x * v2.y - v2.x * v1.y


def orientation(p1: Vec2, p2: Vec2, p3: Vec2) -> Orientation:
    det = determinant(p3 - p2, p2 - p1)
    if det == 1:
        return Orientation.CLOCKWISE
    elif det == -1:
        return Orientation.COUNTERCLOCKWISE
    else:
        return Orientation.COLINEAR


def segments_intersect(seg1: Tuple[Vec2, Vec2], seg2: Tuple[Vec2, Vec2]) -> Optional[Vec2]:
    """Returns the intersection point if line1 and line2 intersect, and None otherwise."""
    p1, q1 = seg1
    p2, q2 = seg2
    lk = q2 - p2
    nm = p1 - q1
    mk = q1 - p2

    det = determinant(nm, lk)
    if abs(det) < 1e-6:
        return None
    else:
        detinv = 1.0 / det
        s = (nm.x * mk.y - nm.y * mk.x) * detinv
        t = (lk.x * mk.y - lk.y * mk.x) * detinv
        if s < 0.0 or s > 1.0 or t < 0.0 or t > 1.0:
            return None
        else:
            return p2 + lk * s


def linear_coefficients(p: Vec2, q: Vec2) -> Tuple[float, float]:
    delta = q - p
    slope = delta.y / delta.x
    c = p.y - p.x * slope
    return (slope, c)


def segment_intersects_line(seg: Tuple[Vec2, Vec2], line: Tuple[Vec2, Vec2]) -> Optional[Vec2]:
    """Returns the intersection between seg and line or None if there is no intersection.

    line is defined by any two points on it.
    """
    o1 = orientation(seg[0], line[0], line[1])
    if o1 == Orientation.COLINEAR:
        return seg[0]
    o2 = orientation(seg[1], line[0], line[1])
    if o2 == Orientation.COLINEAR:
        return seg[1]

    if o1 != o2:
        # intersects
        a, c = linear_coefficients(*seg)
        b, d = linear_coefficients(*line)
        t = (d - c) / (a - b)
        return Vec2(t, a * t + c)
    else:
        return None


BezJ = zeros2d(MAXSEGS + 1, 5)
BezJPrime = zeros2d(MAXSEGS + 1, 5)
INITIALIZED = False
CURVE_SLACK = 5


def init_bezier():
    global INITIALIZED

    if not INITIALIZED:
        for ti in range(MAXSEGS+1):
            t = ti/MAXSEGS
            for i in range(4):  # i = 0, 1, 2, 3
                BezJ[ti][i] = comb(3, i) * math.pow(t, i) * math.pow(1-t, 3-i)
            # At the moment hard-wired for n = 3
            tm = 1 - t
            BezJPrime[ti][0] = -3*tm*tm
            BezJPrime[ti][1] = 3*tm*tm - 6*t*tm
            BezJPrime[ti][2] = 6*t*tm - 3*t*t
            BezJPrime[ti][3] = 3*t*t

        INITIALIZED = True


class Reaction:
    def __init__(self, id_: str, *, sources: List[Node], targets: List[Node],
                 fill_color: wx.Colour, scale: float = 1, index: int = -1):
        self.id_ = id_
        self.index = index
        self.fill_color = fill_color
        self._scale = scale
        self._sources = sources
        self._targets = targets
        self.bezier = ReactionBezier(sources, targets)

        self.update_nodes(sources, targets)

    @property
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def scale(self, val: float):
        self._scale = val
        self.bezier.scale = val

    def do_paint(self, gc: wx.GraphicsContext, to_scrolled_fn: ToScrolledFn):
        self.bezier.do_paint(gc, to_scrolled_fn)

    def do_paint_selected(self, gc: wx.GraphicsContext, to_scrolled_fn: ToScrolledFn):
        self.bezier.do_paint_selected(gc, to_scrolled_fn)

    def update_nodes(self, sources: List[Node], targets: List[Node]):
        s = sum((n.position + n.size / 2 for n in sources + targets), Vec2())
        self._position = s / (len(sources) + len(targets))

    def update(self):
        self.update_nodes(self._sources, self._targets)
        self.bezier.nodes_updated()

    @property
    def position(self) -> Vec2:
        return self._position

    @property
    def s_position(self) -> Vec2:
        return self._position * self.scale

    @property
    def sources(self) -> List[Node]:
        return self._sources

    @property
    def targets(self) -> List[Node]:
        return self._targets


class SpeciesBezier:
    def __init__(self, node: Node, handle: Vec2, centroid: Vec2, centroid_handle: Vec2,
                 is_source: bool):
        assert INITIALIZED, 'Bezier matrices not initialized! Call init_bezier()'

        self.node = node
        self.node_intersection = None
        self.handle = handle
        self.is_source = is_source
        self.bezier_points = [Vec2() for _ in range(MAXSEGS + 1)]
        self._dirty = True
        self.scale = 1
        self.update_curve(centroid, centroid_handle)
        self.arrow_adjusted_coords = list()

    def update_curve(self, centroid: Vec2, centroid_handle: Vec2):
        """Called after either the node, the centroid, or at least one of their handles changed.
        """
        self.centroid = centroid
        self.centroid_handle = centroid_handle
        self._dirty = True

    def _recompute_curve(self):
        node_center = self.node.position + self.node.size / 2

        # add a padding to node, so that the Bezier curve starts outside the node. The portion
        # of the handle within this is not drawn
        outer_rect = padded_rect(self.node.rect, NODE_EDGE_GAP_DISTANCE)

        self.node_intersection = None
        # extend handle to make sure that an intersection is found between the handle and the
        # node rectangle sides. We're essentially making the handle a ray.
        longer_side = max(outer_rect.size.x, outer_rect.size.y)
        extended_handle = node_center + (self.handle - node_center).normalized(longer_side * 10)
        handle_segment = (node_center, extended_handle)
        # check for intersection on the side
        sides = outer_rect.sides()
        for side in sides:
            x = segments_intersect(side, handle_segment)
            if x is not None:
                self.node_intersection = x
                break

        assert self.node_intersection is not None
        #node_end = segments_intersect((node_center, self.handle), )
        # Scale up dimensions (mult by 1000) to get a smooth curve
        for i in range(MAXSEGS+1):
            tmp = Vec2()
            for j, point in enumerate((self.node_intersection, self.handle, self.centroid_handle,
                                       self.centroid)):
                tmp += point * 1000 * BezJ[i][j]

            # and scale back down again
            self.bezier_points[i] = tmp / 1000

        if not self.is_source:
            self._recompute_arrow_tip(self.node_intersection,
                                      self.node_intersection - extended_handle)

    def _recompute_arrow_tip(self, tip, slope):
        alpha = -math.atan2(slope.y, slope.x)
        cosine = math.cos(alpha)
        sine = math.sin(alpha)

        # Adjust the tip so that it moves forward slightly
        tip += TIP_DISPLACEMENT * Vec2(cosine, -sine)

        # Rotate the arrow into the correct orientation
        self.arrow_adjusted_coords = list()
        for i in range(4):
            coord = Vec2(arrowTipPoints[i].x * cosine + arrowTipPoints[i].y * sine,
                         -arrowTipPoints[i].x * sine + arrowTipPoints[i].y * cosine)
            self.arrow_adjusted_coords.append(coord)

        # Compute the distance of the tip of the arrow to the end point on the line
        # where the arrow should be placed. Then use this distance to translate the arrow
        offset = tip - self.arrow_adjusted_coords[3]
        # Translate the remaining coordinates of the arrow, note tip = Q
        for i in range(4):
            self.arrow_adjusted_coords[i] += offset

    def is_on_curve(self, pos: Vec2) -> bool:
        """Check if position is on curve; pos is scaled logical position."""
        if self._dirty:
            self._recompute_curve()
            self._dirty = False

        return any(pt_on_line(p1 * self.scale, p2 * self.scale, pos, CURVE_SLACK)
                   for p1, p2 in pairwise(self.bezier_points))

    def do_paint(self, gc: wx.GraphicsContext, to_scrolled_fn: ToScrolledFn):
        if self._dirty:
            self._recompute_curve()
            self._dirty = False
        # Draw bezier curve
        gc.SetPen(wx.Pen(wx.BLACK, 2))
        path = gc.CreatePath()

        path.MoveToPoint(*to_scrolled_fn(self.bezier_points[0] * self.scale))
        for i in range(1, MAXSEGS+1):
            path.AddLineToPoint(*to_scrolled_fn(self.bezier_points[i] * self.scale))
        gc.StrokePath(path)

        # Draw arrow tip
        if not self.is_source:
            self.paint_arrow_tip(gc)

    def do_paint_selected(self, gc: wx.GraphicsContext, to_scrolled_fn: ToScrolledFn):
        node_intersect = Vec2(to_scrolled_fn(self.node_intersection * self.scale))
        node_handle = Vec2(to_scrolled_fn(self.handle * self.scale))
        centroid = Vec2(to_scrolled_fn(self.centroid * self.scale))
        centroid_handle = Vec2(to_scrolled_fn(self.centroid_handle * self.scale))
        self.paint_handles(gc, node_intersect, node_handle, centroid, centroid_handle)

    def paint_arrow_tip(self, gc):
        assert len(self.arrow_adjusted_coords) == 4
        c = wx.Colour(0, 0, 0, 255)
        gc.SetPen(wx.Pen(c))
        gc.SetBrush(wx.Brush(c))
        gc.DrawLines([wx.Point2D(*coord) for coord in self.arrow_adjusted_coords])

    def paint_handles(self, gc: wx.GraphicsContext, base1: Vec2, handle1: Vec2, base2: Vec2,
                      handle2: Vec2):
        c = wx.Colour(0, 102, 204, 255)
        brush = wx.Brush(c)
        pen = wx.Pen(c)

        gc.SetPen(pen)

        # Draw handle lines
        path = gc.CreatePath()
        path.MoveToPoint(*base1)
        path.AddLineToPoint(*handle1)

        path.MoveToPoint(*base2)
        path.AddLineToPoint(*handle2)
        gc.StrokePath(path)

        # Draw handle circles
        gc.SetBrush(brush)
        gc.DrawEllipse(handle1.x - HANDLE_RADIUS, handle1.y - HANDLE_RADIUS,
                       2 * HANDLE_RADIUS, 2 * HANDLE_RADIUS)
        gc.DrawEllipse(handle2.x - HANDLE_RADIUS, handle2.y - HANDLE_RADIUS,
                       2 * HANDLE_RADIUS, 2 * HANDLE_RADIUS)


@dataclass
class BezierHandle:
    is_centroid_reactant: Optional[bool]
    species_bezier: Optional[SpeciesBezier]
    mouse_offset: Vec2


class ReactionBezier:
    src_beziers: List[SpeciesBezier]
    dest_beziers: List[SpeciesBezier]

    def __init__(self, reactants: List[Node], products: List[Node]):
        self.reactants = reactants
        self.products = products
        self.centroid = compute_centroid(reactants, products)
        self.src_beziers = list()
        self.dest_beziers = list()

        self._scale = 1

        # TODO hard-coded for now
        self.src_c_handle = (self.reactants[0].center_point + self.centroid) / 2
        self.dest_c_handle = 2 * self.centroid - self.src_c_handle

        for node in self.reactants:
            node_handle = (node.center_point + self.centroid) / 2
            self.src_beziers.append(SpeciesBezier(node, node_handle, self.centroid,
                                                  self.src_c_handle, True))
        for node in self.products:
            node_handle = (node.center_point + self.centroid) / 2
            self.dest_beziers.append(SpeciesBezier(node, node_handle, self.centroid,
                                                   self.dest_c_handle, False))

    @property
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def scale(self, val: float):
        self._scale = val
        for bz in chain(self.src_beziers, self.dest_beziers):
            bz.scale = val

    def is_on_curve(self, pos: Vec2) -> bool:
        """Return whether mouse is on the Bezier curve (not including the handles).

        pos is the logical position of the mouse (and not multiplied by any scale).
        """
        return any(bz.is_on_curve(pos) for bz in chain(self.src_beziers, self.dest_beziers))

    def on_which_handle(self, pos: Vec2) -> Optional[BezierHandle]:
        # check centroid handles
        scaled_src_ch = self.src_c_handle * self._scale
        scaled_dest_ch = self.dest_c_handle * self._scale
        if pt_in_circle(pos, HANDLE_RADIUS, scaled_src_ch):
            return BezierHandle(True, None, scaled_src_ch - pos)
        if pt_in_circle(pos, HANDLE_RADIUS, scaled_dest_ch):
            return BezierHandle(False, None, scaled_dest_ch - pos)

        for bz in self.src_beziers:
            scaled_handle = bz.handle * self._scale
            if pt_in_circle(pos, HANDLE_RADIUS, scaled_handle):
                return BezierHandle(None, bz, scaled_handle - pos)

        for bz in self.dest_beziers:
            scaled_handle = bz.handle * self._scale
            if pt_in_circle(pos, HANDLE_RADIUS, scaled_handle * self._scale):
                return BezierHandle(None, bz, scaled_handle - pos)

        return None

    def do_move_handle(self, handle: BezierHandle, pos: Vec2):
        if handle.is_centroid_reactant is not None:
            if handle.is_centroid_reactant:
                self.src_c_handle = (handle.mouse_offset + pos) / self._scale
                self.dest_c_handle = (2 * self.centroid - self.src_c_handle) / self._scale
            else:
                self.dest_c_handle = (handle.mouse_offset + pos) / self._scale
                self.src_c_handle = (2 * self.centroid - self.dest_c_handle) / self._scale

            for sp_bz in self.src_beziers:
                sp_bz.update_curve(self.centroid, self.src_c_handle)
            for sp_bz in self.dest_beziers:
                sp_bz.update_curve(self.centroid, self.dest_c_handle)
        else:
            assert handle.species_bezier is not None
            handle.species_bezier.handle = (handle.mouse_offset + pos) / self._scale
            centroid_handle = self.src_c_handle if handle.species_bezier.is_source else \
                self.dest_c_handle
            handle.species_bezier.update_curve(self.centroid, centroid_handle)

    def nodes_updated(self):
        for sp_bz in self.src_beziers:
            sp_bz.update_curve(self.centroid, self.src_c_handle)
        for sp_bz in self.dest_beziers:
            sp_bz.update_curve(self.centroid, self.dest_c_handle)

    def do_paint(self, gc: wx.GraphicsContext, to_scrolled_fn: ToScrolledFn):
        for bz in chain(self.src_beziers, self.dest_beziers):
            bz.do_paint(gc, to_scrolled_fn)

    def do_paint_selected(self, gc: wx.GraphicsContext, to_scrolled_fn: ToScrolledFn):
        for bz in chain(self.src_beziers, self.dest_beziers):
            bz.do_paint_selected(gc, to_scrolled_fn)
