"""Classes for storing and managing data for graph elements."""
# pylint: disable=maybe-no-member
import wx
import copy
import math
from itertools import chain
from typing import Callable, List, Optional, Tuple
from .geometry import Vec2, Rect, padded_rect, pt_in_circle, pt_on_line, segments_intersect
from .state import cstate
from ..config import settings, theme
from ..utils import pairwise


MAXSEGS = 29  # Number of segments used to construct bezier
HANDLE_RADIUS = 5  # Radius of the contro lhandle
HANDLE_BUFFER = 2
NODE_EDGE_GAP_DISTANCE = 4  # Distance between node and start of bezier line
TIP_DISPLACEMENT = 4
DEFAULT_ARROW_TIP = [Vec2(0, 14), Vec2(3, 7), Vec2(0, 0), Vec2(20, 7)]
arrowTipPoints = DEFAULT_ARROW_TIP


class Node:
    """Class that represents a Node for rendering purposes.

    Attributes:
        index: The index of the node. If this node has not yet been added to the NOM, this takes on
               the value of -1.
        id_: The ID of the node.
        fill_color: The fill color of the node.
        border_color: The border color of the node.
        border_width: The border width of the node.
    """
    index: int
    id_: str
    fill_color: wx.Colour
    border_color: wx.Colour
    border_width: float
    _position: Vec2
    _size: Vec2

    # force keyword-only arguments
    def __init__(self, id_: str, *, pos: Vec2, size: Vec2, fill_color: wx.Colour,
                 border_color: wx.Colour, border_width: float, index: int = -1):
        self.index = index
        self.id_ = id_
        self._position = pos
        self._size = size
        self.fill_color = fill_color
        self.border_color = border_color
        self.border_width = border_width

    @property
    def position(self):
        """The unscaled position of the node."""
        return self._position

    @position.setter
    def position(self, val: Vec2):
        self._position = val

    @property
    def s_position(self):
        """The scaled position of the node obtained by multiplying the scale."""
        return self._position * cstate.scale

    @s_position.setter
    def s_position(self, val: Vec2):
        self.position = val / cstate.scale

    @property
    def size(self):
        """The unscaled size of the node."""
        return self._size

    @size.setter
    def size(self, val: Vec2):
        self._size = val

    @property
    def s_size(self):
        """The scaled size of the node obtained by multiplying the scale."""
        return self._size * cstate.scale

    @s_size.setter
    def s_size(self, val: Vec2):
        self._size = val / cstate.scale

    @property
    def s_rect(self):
        """Return scaled position/size as Rect.

        Note that the fields of the returned rect is copied, so one cannot modify this node through
        the rect.
        """
        return Rect(copy.copy(self.s_position), copy.copy(self.s_size))

    @property
    def rect(self):
        """The same as s_rect, but the rectangle is unscaled.
        """
        return Rect(copy.copy(self.position), copy.copy(self.size))

    @property
    def center_point(self) -> Vec2:
        return self.position + self.size / 2


ToScrolledFn = Callable[[Vec2], Vec2]


def zeros2d(n_rows, n_cols) -> List[List[float]]:
    """Return a 2D list of zeros with dimensions (n_rows, n_cols)."""
    ret = [None] * n_rows
    for i in range(n_rows):
        ret[i] = [0] * n_cols

    return ret


# TODO OPTIMIZE. scipy has function that computes this but it seems like an overkill, since scipy
# would probably double the size of the executable.
# Also can solve this easily by upgrading to Python 3.8, which has a built-in comb method.
def comb(n: int, i: int):
    """Compute the bonimial coefficient/combinations C(n, i)"""
    return math.factorial(n) / (math.factorial(i) * math.factorial(n-i))


def compute_centroid(reactants: List[Node], products: List[Node]) -> Vec2:
    """Compute the centroid position of a list of reactant and product nodes."""
    total = sum((n.center_point for n in chain(reactants, products)), Vec2())
    return total / (len(reactants) + len(products))


BezJ = zeros2d(MAXSEGS + 1, 5)  #: Precomputed Bezier curve data
BezJPrime = zeros2d(MAXSEGS + 1, 5)  #: Precomputed bezier curve data
INITIALIZED = False  #: Flag for asserting that the above data is initialized
CURVE_SLACK = 5  #: Distance allowed on either side of a curve for testing click hit.


def init_bezier():
    """Initialize (precompute) the Bezier data."""
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
    """Class that keeps track of data for a reaction as well as its Bezier curve.

    Attributes:
        id_: reaction ID.
        index: reaction index.
        fill_color: reaction fill color.
        rate_law: reaction rate law.
        bezier: Instance that keeps track of the Bezier curve data associated to this reaction.
        position: The centroid position.
        s_position: The scaled centroid position. TODO this is sort of redundant.
        sources: The source (reactant) nodes.
        target: The target (product) nodes.
    """

    def __init__(self, id_: str, *, sources: List[Node], targets: List[Node],
                 handle_pos: List[Vec2] = None, fill_color: wx.Colour, rate_law: str,
                 index: int = -1):
        """Constructor for a reaction.

        Args:
            id_: Reaction ID.
            sources: List of source (reactant) nodes.
            targets: List of target (product) nodes.
            handle_pos: List of handle positions. Refer to the identically named argument in the
                        ReactionBezier constructor.
            fill_color: Fill color of the curve.
            rate_law: The rate law string of the reaction; may not be valid.
            index: Reaction index.
        """
        self.id_ = id_
        self.index = index
        self.fill_color = fill_color
        self.rate_law = rate_law
        self._sources = sources
        self._targets = targets
        self.bezier = ReactionBezier(sources, targets, handle_pos)

        self.update_nodes(sources, targets)

    def update_nodes(self, sources: List[Node], targets: List[Node]):
        """Called when the node position/size has changed."""
        s = sum((n.position + n.size / 2 for n in sources + targets), Vec2())
        self._position = s / (len(sources) + len(targets))

    @property
    def position(self) -> Vec2:
        return self._position

    @property
    def s_position(self) -> Vec2:
        return self._position * cstate.scale

    @property
    def sources(self) -> List[Node]:
        return self._sources

    @property
    def targets(self) -> List[Node]:
        return self._targets


def paint_handle(gc: wx.GraphicsContext, base: Vec2, handle: Vec2, hovering: bool):
    """Paint the handle as given by its base and tip positions, highlighting it if hovering."""
    c = wx.Colour(255, 112, 0) if hovering else wx.Colour(0, 102, 204)
    brush = wx.Brush(c)
    pen = wx.Pen(c)

    gc.SetPen(pen)

    # Draw handle lines
    path = gc.CreatePath()
    path.MoveToPoint(*base)
    path.AddLineToPoint(*handle)
    gc.StrokePath(path)

    # Draw handle circles
    gc.SetBrush(brush)
    gc.DrawEllipse(handle.x - HANDLE_RADIUS, handle.y - HANDLE_RADIUS,
                   2 * HANDLE_RADIUS, 2 * HANDLE_RADIUS)


class BezierHandle:
    """Class that keeps track of a Bezier control handle (tip).

    Attributes:
        position: Position of the tip of the handle.
        mouse_hovering: Whether the mouse is currently hovering over the handle. This should be
                        updated outside manually.
        on_moved: The callback for when the handle is moved.
    """
    position: Vec2
    _mouse_offset: Vec2  #: Convenient field that stores (center - mouse_pos) on mouse down.
    mouse_hovering: bool
    on_moved: Optional[Callable[[Vec2], None]]

    def __init__(self, position: Vec2, on_moved: Callable[[Vec2], None] = None):
        self.position = position
        self._mouse_offset = Vec2()
        self.on_moved = on_moved
        self.mouse_hovering = False

    def do_drag(self, pos: Vec2):
        self.position = (pos + self._mouse_offset) / cstate.scale
        if self.on_moved:
            self.on_moved(self.position)

    def do_left_down(self, pos: Vec2):
        self._mouse_offset = self.position - pos


class SpeciesBezier:
    """Class that keeps track of the Bezier curve associated with a reaction species.

    Attributes:
        node: The associated node.
        node_intersection: The intersection point between the handle and the padded node, i.e. the
                           point after which the handle is not drawn, to create a gap.
        handle: Beizer handle for the side on the species.
        cnetroid_handle: Bezier handle for the centroid, shared among all reactants/products of
                         this reaction.
        is_source: Whether this species is considered a source or a dest node.
        arrow_adjusted_coords: Coordinate array for the arrow vertices.
    """
    node: Node
    node_intersection: Optional[Vec2]
    handle: BezierHandle
    centroid_handle: BezierHandle
    is_source: bool
    bezier_points: List[Vec2]
    _dirty: bool  #: Whether the Bezier curve needs to be recomputed.

    def __init__(self, node: Node, handle: BezierHandle, centroid: Vec2,
                 centroid_handle: BezierHandle, is_source: bool):
        assert INITIALIZED, 'Bezier matrices not initialized! Call init_bezier()'

        self.node = node
        self.node_intersection = None
        self.handle = handle
        self.centroid_handle = centroid_handle
        self.is_source = is_source
        self.bezier_points = [Vec2() for _ in range(MAXSEGS + 1)]
        self._dirty = True
        self.update_curve(centroid)
        self.arrow_adjusted_coords = list()

    def update_curve(self, centroid: Vec2):
        """Called after either the node, the centroid, or at least one of their handles changed.
        """
        self.centroid = centroid
        self._dirty = True

    def _recompute_curve(self):
        """Recompute the curve points and arrow points."""
        node_center = self.node.position + self.node.size / 2

        # add a padding to node, so that the Bezier curve starts outside the node. The portion
        # of the handle within this is not drawn
        outer_rect = padded_rect(self.node.rect, NODE_EDGE_GAP_DISTANCE)

        self.node_intersection = None
        # extend handle to make sure that an intersection is found between the handle and the
        # node rectangle sides. We're essentially making the handle a ray.
        longer_side = max(outer_rect.size.x, outer_rect.size.y)
        long_dist = (longer_side + NODE_EDGE_GAP_DISTANCE) * 10
        extended_handle = node_center + (self.handle.position - node_center).normalized(long_dist)
        handle_segment = (node_center, extended_handle)
        # check for intersection on the side
        sides = outer_rect.sides()
        for side in sides:
            x = segments_intersect(side, handle_segment)
            if x is not None:
                self.node_intersection = x
                break

        assert self.node_intersection is not None

        # Scale up dimensions (mult by 1000) to get a smooth curve
        for i in range(MAXSEGS+1):
            tmp = Vec2()
            for j, point in enumerate((self.node_intersection, self.handle.position,
                                       self.centroid_handle.position, self.centroid)):
                tmp += point * 1000 * BezJ[i][j]

            # and scale back down again
            self.bezier_points[i] = tmp / 1000

        if not self.is_source:
            self._recompute_arrow_tip(self.node_intersection,
                                      self.node_intersection - extended_handle)

    def _recompute_arrow_tip(self, tip, slope):
        """Helper that recomputes the vertex coordinates of the arrow, given the tip pos and slope.
        """
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

        return any(pt_on_line(p1 * cstate.scale, p2 * cstate.scale, pos, CURVE_SLACK)
                   for p1, p2 in pairwise(self.bezier_points))

    def do_paint(self, gc: wx.GraphicsContext, fill: wx.Colour, to_scrolled_fn: ToScrolledFn,
                 selected: bool):
        if self._dirty:
            self._recompute_curve()
            self._dirty = False
        # Draw bezier curve
        if selected:
            #pen = wx.Pen(theme['selected_reaction_fill'], 2, style=wx.PENSTYLE_LONG_DASH)
            pen = wx.Pen(theme['selected_reaction_fill'], 2)
        else:
            pen = wx.Pen(fill, 2)
        gc.SetPen(pen)
        path = gc.CreatePath()

        path.MoveToPoint(*to_scrolled_fn(self.bezier_points[0] * cstate.scale))
        for i in range(1, MAXSEGS+1):
            path.AddLineToPoint(*to_scrolled_fn(self.bezier_points[i] * cstate.scale))
        gc.StrokePath(path)

        # Draw arrow tip
        if not self.is_source:
            color = theme['select_box_color'] if selected else fill
            self.paint_arrow_tip(gc, color, to_scrolled_fn)

        if selected:
            node_intersect = Vec2(to_scrolled_fn(self.node_intersection * cstate.scale))
            node_handle = Vec2(to_scrolled_fn(self.handle.position * cstate.scale))
            paint_handle(gc, node_intersect, node_handle, self.handle.mouse_hovering)

    def paint_arrow_tip(self, gc: wx.Colour, fill: wx.Colour, to_scrolled_fn: ToScrolledFn):
        assert len(self.arrow_adjusted_coords) == 4
        gc.SetPen(wx.Pen(fill))
        gc.SetBrush(wx.Brush(fill))
        gc.DrawLines([wx.Point2D(*to_scrolled_fn(coord * cstate.scale))
                      for coord in self.arrow_adjusted_coords])


class ReactionBezier:
    """Class that keeps track of all Bezier curve data for a reaction.

    Attributes:
        src_beziers: List of SpeciesBezier instances for reactants.
        dest_beziers: List of SpeciesBezier instances for products.
        src_c_handle: Centroid bezier handle that controls the reactant curves.
        dest_c_handle: Centroid bezier handle that controls the product curves.
        handles: List of all the BezierHandle instances, stored for convenience.
    """
    src_beziers: List[SpeciesBezier]
    dest_beziers: List[SpeciesBezier]
    src_c_handle: BezierHandle
    dest_c_handle: BezierHandle
    handles: List[BezierHandle]

    def __init__(self, reactants: List[Node], products: List[Node],
                 handle_positions: List[Vec2] = None):
        """Constructor.

        Args:
            reactants: List of reactant nodes.
            products: List of product nodes.
            handle_positions: The list of positions of the handles. 0th element is the position of
                              the reactant-side centroid handle, followed by the reactant handle
                              positions given in the same order as the reactants list, and
                              similarly followed by the product handle positins. Leave as None to
                              automatically initialize the handle positions (e.g. when a new
                              reaction is created).
        """
        self.reactants = reactants
        self.products = products
        self.centroid = compute_centroid(reactants, products)
        self.src_beziers = list()
        self.dest_beziers = list()

        src_handle_pos: Vec2
        handle_pos: List[Vec2]
        if handle_positions is not None:
            assert len(handle_positions) == len(self.reactants) + len(self.products) + 1
            src_handle_pos = handle_positions[0]
            handle_pos = handle_positions[1:]
        else:
            src_handle_pos = (self.reactants[0].center_point + self.centroid) / 2
            handle_pos = [(n.center_point + self.centroid) / 2 for n in chain(reactants, products)]

        self.src_c_handle = BezierHandle(src_handle_pos, lambda _: self.src_handle_moved())
        self.dest_c_handle = BezierHandle(2 * self.centroid - src_handle_pos,
                                          lambda _: self.dest_handle_moved())

        self.handles = [self.src_c_handle, self.dest_c_handle]

        # create handles for species
        in_products = False  # whether the loop has reached the products part
        index = 0
        for node in chain(self.reactants, [None], self.products):
            if node is None:
                in_products = True
                continue

            node_handle = BezierHandle(handle_pos[index])
            centroid_handle = self.dest_c_handle if in_products else self.src_c_handle
            sb = SpeciesBezier(node, node_handle, self.centroid, centroid_handle, not in_products)
            to_append = self.dest_beziers if in_products else self.src_beziers
            to_append.append(sb)
            #node_handle.on_moved = lambda _: sb.update_curve(self.centroid)
            node_handle.on_moved = self.make_handle_moved_func(sb)
            self.handles.append(node_handle)
            index += 1

    def make_handle_moved_func(self, sb: SpeciesBezier):
        """Manufacture a callback function (on_moved) for the given SpeciesBezier."""
        return lambda _: sb.update_curve(self.centroid)

    def is_mouse_on(self, pos: Vec2) -> bool:
        """Return whether mouse is on the Bezier curve (not including the handles).

        pos is the logical position of the mouse (and not multiplied by any scale).
        """
        if (pos - self.centroid).norm_sq <= settings['reaction_radius'] ** 2:
            return True
        return any(bz.is_on_curve(pos) for bz in chain(self.src_beziers, self.dest_beziers))

    def in_which_handle(self, pos: Vec2) -> Optional[BezierHandle]:
        """Return the handle that pos is inside, or None if it's not in any."""
        for handle in self.handles:
            if pt_in_circle(pos, HANDLE_RADIUS, handle.position * cstate.scale):
                return handle
        return None

    def src_handle_moved(self):
        """Special callback for when the source centroid handle is moved."""
        self.dest_c_handle.position = 2 * self.centroid - self.src_c_handle.position
        for bz in chain(self.src_beziers, self.dest_beziers):
            bz.update_curve(self.centroid)

    def dest_handle_moved(self):
        """Special callback for when the dest centroid handle is moved."""
        self.src_c_handle.position = 2 * self.centroid - self.dest_c_handle.position
        for bz in chain(self.src_beziers, self.dest_beziers):
            bz.update_curve(self.centroid)

    def nodes_updated(self):
        """Function called after reactant/product nodes have been updated.
        
        It is assumed that the node referenced held by this instance has been changed
        automatically.
        """
        for sp_bz in self.src_beziers:
            sp_bz.update_curve(self.centroid)
        for sp_bz in self.dest_beziers:
            sp_bz.update_curve(self.centroid)

    def do_paint(self, gc: wx.GraphicsContext, fill: wx.Colour, to_scrolled_fn: ToScrolledFn,
                 selected: bool):
        new_centroid = compute_centroid(self.reactants, self.products)
        if new_centroid != self.centroid:
            self.centroid = new_centroid
            self.src_handle_moved()

        for bz in chain(self.src_beziers, self.dest_beziers):
            bz.do_paint(gc, fill, to_scrolled_fn, selected)

        if selected:
            centroid = Vec2(to_scrolled_fn(self.centroid * cstate.scale))
            center_handles = [self.src_c_handle, self.dest_c_handle]
            hovering = any(h.mouse_hovering for h in center_handles)
            for handle in center_handles:
                handle_pos = Vec2(to_scrolled_fn(handle.position * cstate.scale))
                paint_handle(gc, centroid, handle_pos, hovering)
