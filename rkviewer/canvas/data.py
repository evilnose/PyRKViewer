"""Classes for storing and managing data for graph elements."""
from __future__ import annotations
# pylint: disable=maybe-no-member
from dataclasses import dataclass
import wx
import copy
import math
from itertools import chain
import numpy as np
from scipy.special import comb
from typing import Callable, Container, List, Optional, Sequence, Tuple
from .geometry import Vec2, Rect, padded_rect, pt_in_circle, pt_on_line, rotate_unit, segments_intersect
from .state import cstate
from ..config import get_setting, get_theme
from ..utils import gchain, pairwise


MAXSEGS = 8  # Number of segments used to construct bezier
HANDLE_RADIUS = 5  # Radius of the contro lhandle
HANDLE_BUFFER = 2
NODE_EDGE_GAP_DISTANCE = 4  # Distance between node and start of bezier line
TIP_DISPLACEMENT = 4


class RectData:
    position: Vec2
    size: Vec2


class Node(RectData):
    """Class that represents a Node for rendering purposes.

    Attributes:
        index: The index of the node. If this node has not yet been added to the NOM, this takes on
               the value of -1.
        id: The ID of the node.
        fill_color: The fill color of the node.
        border_color: The border color of the node.
        border_width: The border width of the node.
        position: Position of the size.
        size: Position of the size.
        net_index: The network index of the node.
    """
    id: str
    fill_color: wx.Colour
    border_color: wx.Colour
    border_width: float
    position: Vec2
    size: Vec2
    comp_idx: int
    index: int
    net_index: int
    floatingNode: bool

    # force keyword-only arguments
    def __init__(self, id: str, net_index: int, *, pos: Vec2, size: Vec2, fill_color: wx.Colour,
                 border_color: wx.Colour, border_width: float, comp_idx: int = -1, floatingNode: bool = True, index: int = -1):
        self.index = index
        self.net_index = net_index
        self.id = id
        self.position = pos
        self.size = size
        self.fill_color = fill_color
        self.border_color = border_color
        self.border_width = border_width
        self.comp_idx = comp_idx
        self.floatingNode = floatingNode

    @property
    def s_position(self):
        """The scaled position of the node obtained by multiplying the scale."""
        return self.position * cstate.scale

    @s_position.setter
    def s_position(self, val: Vec2):
        self.position = val / cstate.scale

    @property
    def s_size(self):
        """The scaled size of the node obtained by multiplying the scale."""
        return self.size * cstate.scale

    @s_size.setter
    def s_size(self, val: Vec2):
        self.size = val / cstate.scale

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
        return Rect(self.position, self.size)

    def __repr__(self):
        return 'Node(index={}, id="{}")'.format(self.index, self.id)

    def props_equal(self, other: Node):
        return self.id == other.id and self.position == other.position and \
            self.size == other.size and self.border_width == other.border_width and \
            self.border_color.GetRGB() == other.border_color.GetRGB() and \
            self.fill_color.GetRGB() == other.fill_color.GetRGB()


def compute_centroid(rects: Sequence[Rect]) -> Vec2:
    """Compute the centroid position of a list of reactant and product nodes."""
    total = sum((r.center_point for r in rects), Vec2())
    return total / (len(rects))


BezJ = np.zeros((MAXSEGS + 1, 5))  #: Precomputed Bezier curve data
BezJPrime = np.zeros((MAXSEGS + 1, 5))  #: Precomputed bezier curve data
INITIALIZED = False  #: Flag for asserting that the above data is initialized
CURVE_SLACK = 5  #: Distance allowed on either side of a curve for testing click hit.


def init_bezier():
    """Initialize (precompute) the Bezier data."""
    global INITIALIZED

    if not INITIALIZED:
        for ti in range(MAXSEGS+1):
            t = ti/MAXSEGS
            for i in range(4):  # i = 0, 1, 2, 3
                BezJ[ti, i] = comb(3, i) * math.pow(t, i) * math.pow(1-t, 3-i)
            # At the moment hard-wired for n = 3
            tm = 1 - t
            BezJPrime[ti, 0] = -3*tm*tm
            BezJPrime[ti, 1] = 3*tm*tm - 6*t*tm
            BezJPrime[ti, 2] = 6*t*tm - 3*t*t
            BezJPrime[ti, 3] = 3*t*t

        INITIALIZED = True



@dataclass
class Reaction:
    id: str
    net_index: int
    index: int
    center_pos: Optional[Vec2]
    fill_color: wx.Colour
    rate_law: str
    _sources: List[int]
    _targets: List[int]
    _thickness: float
    src_c_handle: HandleData
    dest_c_handle: HandleData
    handles: List[HandleData]

    def __init__(self, id: str, net_index: int, *, sources: List[int], targets: List[int],
                 handle_positions: List[Vec2], fill_color: wx.Colour,
                 line_thickness: float, rate_law: str, center_pos: Optional[Vec2] = None, bezierCurves: bool = True,
                 index: int = -1):
        """Constructor for a reaction.

        Args:
            id: Reaction ID.
            sources: List of source (reactant) nodes.
            targets: List of target (product) nodes.
            handle: List of HandleData structs for reactant nodes and product nodes. This is in the
                    same order as sources and targets, i.e. [*sources, *targets].
            src_c_handle: HandleData struct for the source centroid handle.
            dest_c_handle: HandleData struct for the dest centroid handle.
            fill_color: Fill color of the curve.
            rate_law: The rate law string of the reaction; may not be valid.
            index: Reaction index.
            net_index: The network index of the reaction.
        """
        self.id = id
        self.net_index = net_index
        self.index = index
        self.center_pos = center_pos
        self.fill_color = fill_color
        self.rate_law = rate_law
        self._sources = sources
        self._targets = targets
        self._thickness = line_thickness
        self.bezierCurves = bezierCurves

        assert len(handle_positions) == len(sources) + len(targets) + 1
        src_handle_pos = handle_positions[0]
        # Initialize to some arbitrary value. This should be controlled by ReactionBezier later.
        dest_handle_pos = Vec2()
        handle_pos = handle_positions[1:]

        self.src_c_handle = HandleData(src_handle_pos)
        self.dest_c_handle = HandleData(dest_handle_pos)

        self.handles = [HandleData(p) for p in handle_pos]

    @property
    def thickness(self) -> float:
        return self._thickness

    @property
    def sources(self) -> List[int]:
        return self._sources

    @property
    def targets(self) -> List[int]:
        return self._targets


def paint_handle(gc: wx.GraphicsContext, base: Vec2, handle: Vec2, hovering: bool):
    """Paint the handle as given by its base and tip positions, highlighting it if hovering."""
    c = get_theme('highlighted_handle_color') if hovering else get_theme('handle_color')
    brush = wx.Brush(c)
    pen = gc.CreatePen(wx.GraphicsPenInfo(c))

    gc.SetPen(pen)

    # Draw handle lines
    gc.StrokeLine(*base, *handle)

    # Draw handle circles
    gc.SetBrush(brush)
    gc.DrawEllipse(handle.x - HANDLE_RADIUS, handle.y - HANDLE_RADIUS,
                   2 * HANDLE_RADIUS, 2 * HANDLE_RADIUS)


class HandleData:
    """Struct for keeping handle data in-sync between the BezierHandle element and the Reaction.

    Attributes:
        tip: The position of the tip of the handle. May be modified by BezierHandle when user drags
             the handle element.
        base: The position of the base of the handle. May be modified by ReactionBezier, etc. as
              a response to movement of nodes, handles, etc. HACK this is only updated in the
              do_paint method of ReactionElement, and since the BezierHandles are drawn after
              the ReactionElements, the position of the base *happens* to be updated each time, but
              if it were drawn before, it would be one step behind.
    """
    tip: Vec2
    base: Optional[Vec2]

    def __init__(self, tip: Vec2, base: Vec2 = None):
        self.tip = tip
        self.base = base



class SpeciesBezier:
    """Class that keeps track of the Bezier curve associated with a reaction species.

    Note:
        When drawing the reaction curve, the builtin AddCurveToPoint is used. However, for the
        purpose of detecting a click on the curve, we still need to compute a rough approximation
        of the Bezier curve (e.g. 5 straight line segments). Hence why we need to compute the Bezier
        curve.

    Attributes:
        node: The associated node.
        node_intersection: The intersection point between the handle and the padded node, i.e. the
                           point after which the handle is not drawn, to create a gap.
        handle: Beizer handle for the side on the species.
        cnetroid_handle: Bezier handle for the centroid, shared among all reactants/products of
                         this reaction.
        is_source: Whether this species is considered a source or a dest node.
        arrow_adjusted_coords: Coordinate array for the arrow vertices.
        bezierCurves: True if we are drawing Bezier curves. Otherwise we are drawing simple
                      straight lines.
    """
    node_idx: int
    node_intersection: Optional[Vec2]
    handle: HandleData
    centroid_handle: HandleData
    is_source: bool
    bezier_points: List[Vec2]
    real_center: Vec2
    thickness: float
    _extended_handle: Vec2
    _collision_dirty: bool  #: Whether the Bezier curve needs to be recomputed.
    _paint_dirty: bool
    bezierCurves: bool

    def __init__(self, node_idx: int, node_rect: Rect, handle: HandleData, real_center: Vec2,
                 centroid_handle: HandleData, is_source: bool, thickness: float, bezierCurves: bool):
        assert INITIALIZED, 'Bezier matrices not initialized! Call init_bezier()'
        self.node_idx = node_idx
        self.node_rect = node_rect
        self.node_intersection = None
        self.handle = handle
        self.centroid_handle = centroid_handle
        self.is_source = is_source
        self.bezier_points = [Vec2() for _ in range(MAXSEGS + 1)]
        self._collision_dirty = True
        self._paint_dirty = True
        self.update_curve(real_center)
        self.arrow_adjusted_coords = list()
        self.bounding_box = None
        self.thickness = thickness
        self.bezierCurves = bezierCurves

    def update_curve(self, real_center: Vec2):
        """Called after either the node, the centroid, or at least one of their handles changed.
        """
        self.real_center = real_center
        self._collision_dirty = True
        self._paint_dirty = True

    def _recompute(self, for_collision):
        """Recompute everything that could have changed, but only recompute the curve if calc_curve.
        """
        if self._collision_dirty or self._paint_dirty:
            # STEP 1, get intersection between handle and node outer padding
            node_center = self.node_rect.position + self.node_rect.size / 2

            # add a padding to node, so that the Bezier curve starts outside the node. The portion
            # of the handle within this is not drawn
            outer_rect = padded_rect(self.node_rect, NODE_EDGE_GAP_DISTANCE)

            self.node_intersection = None
            # extend handle to make sure that an intersection is found between the handle and the
            # node rectangle sides. We're essentially making the handle a ray.
            longer_side = max(outer_rect.size.x, outer_rect.size.y)
            long_dist = (longer_side + NODE_EDGE_GAP_DISTANCE) * 10

            other_point = self.handle.tip if self.bezierCurves else self.real_center
            handle_diff = other_point - node_center
            if handle_diff.norm_sq <= 1e-6:
                # if norm is too small, make it a hardcoded value to avoid zero vectors
                handle_diff = Vec2(0, 1)
            self._extended_handle = node_center + handle_diff.normalized(long_dist)
            handle_segment = (node_center, self._extended_handle)
            # check for intersection on the side
            sides = outer_rect.sides()
            for side in sides:
                x = segments_intersect(side, handle_segment)
                if x is not None:
                    self.node_intersection = x
                    break

            assert self.node_intersection is not None

        if for_collision:
            # STEP 2, recompute Bezier curve
            if self._collision_dirty:
                for i in range(MAXSEGS+1):
                    tmp = Vec2()
                    for j, point in enumerate((self.node_intersection, self.handle.tip,
                                               self.centroid_handle.tip, self.real_center)):
                        tmp += point * float(BezJ[i, j])

                    # and scale back down again
                    self.bezier_points[i] = tmp

                self._collision_dirty = False
        else:
            # STEP 3, recompute arrow tip
            if self._paint_dirty:
                self._paint_dirty = False
                if not self.is_source:
                    self._recompute_arrow_tip(self.node_intersection,
                                              self.node_intersection - self._extended_handle)

    def arrow_tip_changed(self):
        self._paint_dirty = True

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
        points = cstate.arrow_tip.points
        for i in range(4):
            coord = Vec2(points[i].x * cosine + points[i].y * sine,
                         -points[i].x * sine + points[i].y * cosine)
            self.arrow_adjusted_coords.append(coord)

        # Compute the distance of the tip of the arrow to the end point on the line
        # where the arrow should be placed. Then use this distance to translate the arrow
        offset = tip - self.arrow_adjusted_coords[3]
        # Translate the remaining coordinates of the arrow, note tip = Q
        for i in range(4):
            self.arrow_adjusted_coords[i] += offset

    def is_on_curve(self, pos: Vec2) -> bool:
        """Check if position is on curve; pos is scaled logical position."""
        self._recompute(for_collision=True)
        if self.bezierCurves:
            return any(pt_on_line(p1 * cstate.scale, p2 * cstate.scale, pos,
                                  CURVE_SLACK + self.thickness / 2)
                       for p1, p2 in pairwise(self.bezier_points))
        else:
            return pt_on_line(self.node_intersection * cstate.scale,
                              self.real_center * cstate.scale, pos,
                              CURVE_SLACK + self.thickness / 2)

    def do_paint(self, gc: wx.GraphicsContext, fill: wx.Colour, selected: bool):
        self._recompute(for_collision=False)
        rxn_color: wx.Colour
        # Draw bezier curve
        if selected:
            rxn_color = get_theme('selected_reaction_fill')
        else:
            rxn_color = fill

        pen = gc.CreatePen(wx.GraphicsPenInfo(rxn_color).Width(self.thickness))

        gc.SetPen(pen)
        # gc.StrokeLines([wx.Point2D(*(p * cstate.scale)) for p in self.bezier_points])
        path = gc.CreatePath()
        points = [p * cstate.scale for p in (self.node_intersection,
                                             self.handle.tip,
                                             self.centroid_handle.tip,
                                             self.real_center)]
        path.MoveToPoint(*points[0])
        if self.bezierCurves:
            path.AddCurveToPoint(*points[1], *points[2], *points[3])
        else:
            path.AddLineToPoint(*points[3])
        gc.StrokePath(path)

        if selected:
            assert self.node_intersection is not None
            self.handle.base = self.node_intersection

        # Draw arrow tip
        if not self.is_source:
            color = get_theme('handle_color') if selected else fill
            self.paint_arrow_tip(gc, color)

    def paint_arrow_tip(self, gc: wx.GraphicsContext, fill: wx.Colour):
        assert len(self.arrow_adjusted_coords) == 4, \
            "Arrow adjusted coords is not of length 4: {}".format(self.arrow_adjusted_coords)
        gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(fill)))
        gc.SetBrush(wx.Brush(fill))
        gc.DrawLines([wx.Point2D(*(coord * cstate.scale))
                      for coord in self.arrow_adjusted_coords])


class ReactionBezier:
    """Class that keeps track of all Bezier curve data for a reaction.

    Attributes:
        TODO move this documentation to utils
        CENTER_RATIO: The ratio of source centroid handle length to the distance between the zeroth
                      node and the centroid (center handle is aligned with the zeroth node)
        DUPLICATE_RATIO: Valid for a Bezier whose node is both a product and a reactant. The ratio
                         of length of the product Bezier handle to the distance between the node
                         and the centroid.
        DUPLICATE_ROT: Rotation (radians) applied to the product Bezier handle, for nodes that are
                       both reactant and product. The handle is rotated so as to not align perfectly
                       with the source Bezier handle (otherwise the reactant and product curves
                       would completely overlap).
        src_beziers: List of SpeciesBezier instances for reactants.
        dest_beziers: List of SpeciesBezier instances for products.
        TODO move this to Reaction
        src_c_handle: Centroid bezier handle that controls the reactant curves.
        dest_c_handle: Centroid bezier handle that controls the product curves.
        handles: List of all the BezierHandle instances, stored for convenience.
    """
    src_beziers: List[SpeciesBezier]
    dest_beziers: List[SpeciesBezier]

    def __init__(self, reaction: Reaction, reactants: List[Node], products: List[Node]):
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
        assert len(reactants) == len(reaction.sources)
        assert len(products) == len(reaction.targets)
        self.reaction = reaction
        self.centroid = compute_centroid([n.rect for n in chain(reactants, products)])
        self.src_beziers = list()
        self.dest_beziers = list()

        reaction.dest_c_handle.tip = self.real_center * 2 - reaction.src_c_handle.tip
        reaction.src_c_handle.base = self.real_center
        reaction.dest_c_handle.base = self.real_center
        # create handles for species
        for index, (gi, node) in enumerate(gchain(reactants, products)):
            in_products = bool(gi)

            node_handle = reaction.handles[index]
            centroid_handle = self.reaction.dest_c_handle if in_products else self.reaction.src_c_handle
            sb = SpeciesBezier(node.index, node.rect, node_handle, self.real_center, centroid_handle,
                               not in_products, self.reaction.thickness, self.reaction.bezierCurves)
            to_append = self.dest_beziers if in_products else self.src_beziers
            to_append.append(sb)

    @property
    def real_center(self) -> Vec2:
        return self.reaction.center_pos if self.reaction.center_pos else self.centroid

    def make_handle_moved_func(self, sb: SpeciesBezier):
        """Manufacture a callback function (on_moved) for the given SpeciesBezier."""
        return lambda _: sb.update_curve(self.real_center)

    def is_mouse_on(self, pos: Vec2) -> bool:
        """Return whether mouse is on the Bezier curve (not including the handles).

        pos is the logical position of the mouse (and not multiplied by any scale).
        """
        return any(bz.is_on_curve(pos) for bz in chain(self.src_beziers, self.dest_beziers))

    def src_handle_moved(self):
        """Special callback for when the source centroid handle is moved."""
        self.reaction.dest_c_handle.tip = 2 * self.real_center - self.reaction.src_c_handle.tip
        for bz in chain(self.src_beziers, self.dest_beziers):
            bz.update_curve(self.real_center)

    def dest_handle_moved(self):
        """Special callback for when the dest centroid handle is moved."""
        self.reaction.src_c_handle.tip = 2 * self.real_center - self.reaction.dest_c_handle.tip
        for bz in chain(self.src_beziers, self.dest_beziers):
            bz.update_curve(self.real_center)

    def center_moved(self, offset: Vec2):
        self.reaction.src_c_handle.base = self.real_center
        self.reaction.dest_c_handle.base = self.real_center
        self.reaction.src_c_handle.tip += offset
        self.src_handle_moved()

    def nodes_moved(self, rects: List[Rect]):
        # TODO set center pos, but not controller. Need to update controller later.
        self.centroid = compute_centroid(rects)
        self.reaction.src_c_handle.base = self.real_center
        self.reaction.dest_c_handle.base = self.real_center
        for i, sb in enumerate(chain(self.src_beziers, self.dest_beziers)):
            sb.node_rect = rects[i]
        self.src_handle_moved()

    def do_paint(self, gc: wx.GraphicsContext, fill: wx.Colour, selected: bool):
        for bz in chain(self.src_beziers, self.dest_beziers):
            bz.do_paint(gc, fill, selected)


@dataclass
class Compartment(RectData):
    id: str
    net_index: int
    nodes: List[int]
    volume: float  #: Size (i.e. length/area/volume/...) of the container
    position: Vec2
    size: Vec2  #: Size for drawing on the GUI
    fill: wx.Colour
    border: wx.Colour
    border_width: float
    index: int = -1
    #dimensions: int

    @property
    def rect(self):
        """The same as s_rect, but the rectangle is unscaled.
        """
        return Rect(self.position, self.size)
