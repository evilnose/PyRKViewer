# from __future__ import annotations
from functools import partial
from re import S
from rkviewer.utils import T, int_round
import abc
# pylint: disable=maybe-no-member
import wx
import copy
from enum import Enum
import math
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple, Union


TNum = Union[float, int]


class Vec2:
    """Class that represents a 2D vector. Supports common vector operations like add and sub.

    Note:
        Vec2 objects are immutable, meaning one cannot modify elements of the vector.
    """
    _x: TNum
    _y: TNum
    _i: int

    def __init__(self, x=None, y=None):
        """Initialize a 2D vector.

        If two arguments are specified, they are considered the x and y coordinate
        of the Vec2. If only the first argument is given, then it is unpacked as a two-element
        sequence (x, y). Otherweise, if no arguments are given at all, a (0, 0) Vec2 is created.
        """

        self._i = 0
        if x is None:
            assert y is None, 'y cannot be set when x is None'
            self._x = 0
            self._y = 0
        elif y is None:
            self._x, self._y = x
        else:
            self._x = x
            self._y = y

        '''
        for e in (self.x, self.y):
            if not isinstance(e, int) and not isinstance(e, float):
                raise ValueError('Vec2 should be initialized with int or float. Got {} \
    instead'.format(type(e)))
        '''

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def __iter__(self) -> 'Vec2':
        self._i = 0
        return self

    def __next__(self) -> TNum:
        if self._i == 0:
            self._i += 1
            return self.x
        elif self._i == 1:
            self._i += 1
            return self.y
        else:
            raise StopIteration

    def __add__(self, other) -> 'Vec2':
        return Vec2(self.x + other.x, self.y + other.y)

    __iadd__ = __add__

    def __sub__(self, other) -> 'Vec2':
        return Vec2(self.x - other.x, self.y - other.y)

    __isub__ = __sub__

    def __mul__(self, k) -> 'Vec2':
        return Vec2(self.x * k, self.y * k)

    __rmul__ = __mul__

    __imul__ = __mul__

    def __truediv__(self, k) -> 'Vec2':
        return Vec2(self.x / k, self.y / k)

    def __repr__(self) -> str:
        return '({}, {})'.format(self.x, self.y)

    def __getitem__(self, i: int):
        if i == 0:
            return self.x
        elif i == 1:
            return self.y
        else:
            raise IndexError("Tried to get axis {} of a Vec2".format(i))

    def swapped(self, i: int, val: TNum):
        """Return a Vec2 equal to this one but with the ith element swapped for val."""
        if i == 0:
            return Vec2(val, self.y)
        elif i == 1:
            return Vec2(self.x, val)
        else:
            raise IndexError("Tried to swap axis {} of a Vec2".format(i))

    def __len__(self) -> int:
        return 2

    def __eq__(self, other: 'Vec2') -> bool:
        return abs(self.x - other.x) < 1e-6 and abs(self.y - other.y) < 1e-6

    def to_wx_point(self) -> wx.Point:
        """Convert this to wx.Point; return the result."""
        return wx.Point(int(self.x), int(self.y))

    # element-wise multiplication
    def elem_mul(self, other: 'Vec2') -> 'Vec2':
        """Return the resulting Vec2 by performing element-wise multiplication.

        Examples:
            >>> c = a.elem_mul(b)  # is equivalent to...
            >>> c = Vec2(a.x * b.x, a.y * b.y)
        """
        return Vec2(self.x * other.x, self.y * other.y)

    def elem_div(self, other: 'Vec2') -> 'Vec2':
        """Return the resulting Vec2 by performing element-wise division.

        Examples:
            >>> c = a.elem_div(b)  # is equivalent to...
            >>> c = Vec2(a.x / b.x, a.y / b.y)
        """
        return Vec2(self.x / other.x, self.y / other.y)

    def elem_abs(self) -> 'Vec2':
        """Return the Vec2 obtained by taking the element-wise absolute value of this Vec2."""
        return Vec2(abs(self.x), abs(self.y))

    def map(self, op: Callable[[TNum], Any]) -> 'Vec2':
        """Map the given operation across the two elements of the vector."""
        return Vec2(op(self.x), op(self.y))

    def reduce2(self, op: Callable[[TNum, TNum], Any], other: 'Vec2') -> 'Vec2':
        return Vec2(op(self.x, other.x), op(self.y, other.y))

    def as_int(self) -> 'Vec2':
        """Convert each element to integers using `int()`"""
        return self.map(int)

    @property
    def norm(self) -> TNum:
        return math.sqrt(self.norm_sq)

    @property
    def norm_sq(self) -> TNum:
        return self.x ** 2 + self.y ** 2

    def normalized(self, norm: TNum = 1) -> 'Vec2':
        old_norm = self.norm
        assert old_norm != 0, "Cannot normalize a zero vector!"
        return self * (norm / old_norm)

    def dot(self, other: 'Vec2') -> TNum:
        return self.x * other.x + self.y * other.y

    @classmethod
    def repeat(cls, val: TNum = 1) -> 'Vec2':
        """Return the Vec2 obtained by repeating the given scalar value across the two elements.

        Examples:

            >>> print(Vec2.repeat(5.4))
            (5.4, 5.4)
        """
        return Vec2(val, val)

    def as_tuple(self) -> Tuple[TNum, TNum]:
        return (self.x, self.y)


class Rect:
    """Class that represents a rectangle by keeping a position and a size."""

    def __init__(self, pos: 'Vec2', size: 'Vec2'):
        assert size.x >= 0 and size.y >= 0
        self.position = pos
        self.size = size

    @property
    def center_point(self) -> 'Vec2':
        return self.position + self.size / 2

    def __eq__(self, other: 'Rect') -> bool:
        return self.position == other.position and self.size == other.size

    def __mul__(self, k) -> 'Rect':
        return Rect(self.position * k, self.size * k)

    __rmul__ = __mul__

    __imul__ = __mul__

    def as_tuple(self) -> Tuple[Vec2, Vec2]:
        """Return the position and the size in a tuple."""
        return (self.position, self.size)

    def nth_vertex(self, n: int):
        """Return the nth vertex of the rectangle.

        The top-left vertex is the 0th vertex, and subsequence vertices are indexed in clockwise
        fashion.
        """
        if n == 0:
            return self.position
        elif n == 1:
            return self.position + Vec2(self.size.x, 0)
        elif n == 2:
            return self.position + self.size
        elif n == 3:
            return self.position + Vec2(0, self.size.y)
        else:
            assert False, "Rect.nth_vertex() index out of bounds"

    def sides(self):
        i = 0
        for i in range(3):
            yield (self.nth_vertex(i), self.nth_vertex(i + 1))
        yield (self.nth_vertex(3), self.nth_vertex(0))

    def to_wx_rect(self):
        return wx.Rect(int(self.position.x), int(self.position.y), int(self.size.x),
                       int(self.size.y))

    def union(self, other: 'Rect') -> 'Rect':
        """Return a Rect that contains both self and other"""
        pos = self.position.reduce2(min, other.position)
        botright = (self.position + self.size).reduce2(max, other.position + other.size)
        return Rect(pos, botright - pos)

    def aligned(self) -> 'Rect':
        """Return rectangle aligned to the pixel coordinate system.

        Note:
            See https://github.com/evilnose/PyRKViewer/issues/12 for why this is necessary.
        """
        aligned_pos = self.position.map(int_round)
        # Make sure the size is at least 1
        aligned_size = self.size.map(int_round).map(partial(max, 1))
        return Rect(aligned_pos, aligned_size)

    def __repr__(self):
        return 'Rect({}, {})'.format(self.position, self.size)

    def contains(self, other: 'Rect') -> bool:
        """Returns whether self contains the other rectangle entirely."""
        botright = self.position + self.size
        other_botright = other.position + other.size
        return (self.position.x <= other.position.x) and (self.position.y <= other.position.y) and \
            (botright.x >= other_botright.x) and (botright.y >= other_botright.y)


class Direction(Enum):
    LEFT = 0
    TOP = 1
    RIGHT = 2
    BOTTOM = 3


def clamp_rect_pos(rect: Rect, bounds: Rect, padding=0) -> 'Vec2':
    """Clamp the position of rect, so that it is entirely within the bounds rectangle.

    The position is clamped such that the new position of the rectangle moves the least amount
    of distance possible.

    Note:
        The clamped rectangle must be able to fit inside the bounds rectangle, inclusive. The
        given rect is not modified, but a position is returned.

    Returns:
        The clamped position.
    """

    if rect.size.x + 2 * padding > bounds.size.x or rect.size.y + 2 * padding > bounds.size.y:
        raise ValueError("The clamped rectangle cannot fit inside the given bounds")

    topleft = bounds.position + Vec2.repeat(padding)
    botright = bounds.position + bounds.size - rect.size - Vec2.repeat(padding)
    ret = rect.position
    ret = Vec2(max(ret.x, topleft.x), ret.y)
    ret = Vec2(min(ret.x, botright.x), ret.y)
    ret = Vec2(ret.x, max(ret.y, topleft.y))
    ret = Vec2(ret.x, min(ret.y, botright.y))
    return ret


def clamp_rect_size(rect: Rect, botright: 'Vec2', padding: int = 0) -> 'Vec2':
    """Clamp the size of the given rectangle if its bottom-right corner exceeds botright."""
    limit = botright - rect.position - Vec2.repeat(padding)
    assert limit.x > 0 and limit.y > 0

    return Vec2(min(limit.x, rect.size.x), min(limit.y, rect.size.y))


def clamp_point(pos: 'Vec2', bounds: Rect, padding: int = 0) -> 'Vec2':
    """Clamp the given point (pos) so that it is entirely within the bounds rectangle.

    This is the same as calling clamp_rect_pos() with a clamped rectangle of size 1x1.

    Returns:
        The clamp position.
    """
    pad = Vec2.repeat(padding)
    diff = bounds.size + pad
    assert diff.x >= 0 and diff.y >= 0
    topleft = bounds.position + pad
    botright = bounds.position + bounds.size - pad
    ret = pos
    ret = Vec2(max(ret.x, topleft.x), ret.y)
    ret = Vec2(min(ret.x, botright.x), ret.y)
    ret = Vec2(ret.x, max(ret.y, topleft.y))
    ret = Vec2(ret.x, min(ret.y, botright.y))
    return ret


def clamp_point_outside(pos: 'Vec2', bounds: Rect) -> 'Vec2':
    """Clamp the point so that it is outside the given bounds rectangle.

    The point is clamped so that its new position differs minimally from the old position.
    """
    botright = bounds.position + bounds.size
    # (distance, tiebreak, direction for recording)
    left = (pos.x - bounds.position.x, 0, Direction.LEFT)
    top = (pos.y - bounds.position.y, 1, Direction.TOP)
    right = (botright.x - pos.x, 2, Direction.RIGHT)
    bottom = (botright.y - pos.y, 3, Direction.BOTTOM)

    minimum = min(left, right, top, bottom)

    dist, _, direct = minimum
    if dist <= 0:
        return pos

    if direct == Direction.LEFT:
        return pos.swapped(0, bounds.position.x)
    elif direct == Direction.RIGHT:
        return pos.swapped(0, botright.x)
    elif direct == Direction.TOP:
        return pos.swapped(1, bounds.position.y)
    else:
        assert direct == Direction.BOTTOM
        return pos.swapped(1, botright.y)


def get_bounding_rect(rects: Sequence[Rect], padding: float = 0) -> Rect:
    """Compute the bounding rectangle of a given list of rects.

    This computes the smallest possible rectangle needed to cover each of the rects (inclusive), as
    well as its position. Additionally a padding may be specified to provide some space.

    Args:
        rets: The list of rectangles.
        padding: The padding of the bounding rectangle. If positive, there will be x pixels of
            padding for each side of the rectangle.

    Returns:
        The bounding rectangle.
    """
    min_x = min(r.position.x for r in rects)
    min_y = min(r.position.y for r in rects)
    max_x = max(r.position.x + r.size.x for r in rects)
    max_y = max(r.position.y + r.size.y for r in rects)
    size_x = max_x - min_x + padding * 2
    size_y = max_y - min_y + padding * 2
    return Rect(Vec2(min_x - padding, min_y - padding), Vec2(size_x, size_y))


def padded_rect(rect: Rect, padding: float) -> Rect:
    """Return a rectangle padded by length padding, with the same center as the original."""
    return Rect(rect.position - Vec2.repeat(padding), rect.size + Vec2.repeat(padding) * 2)


def rects_overlap(r1: Rect, r2: Rect) -> bool:
    """Returns whether the two given rectangles overlap, counting if they are touching."""
    botright1 = r1.position + r1.size
    botright2 = r2.position + r2.size

    # The two rects do not overlap if and only if the two rects do not overlap along at least one
    # of the axes.
    for axis in [0, 1]:
        if botright1[axis] < r2.position[axis] or botright2[axis] < r1.position[axis]:
            return False

    return True


# def circle_overlaps_rect(center: 'Vec2', radius: float, rect: Rect) -> bool:
#     pass


def circle_bounds(center: 'Vec2', radius: float) -> Rect:
    """Return the bounding rectangle (actually a square) of circle."""
    offset = Vec2.repeat(radius)
    return Rect(center - offset, Vec2.repeat(radius * 2))


def pt_on_line(a: 'Vec2', b: 'Vec2', point: 'Vec2', threshold: float = 0) -> bool:
    """Returns whether point is on line ab, with the given threshold distance on either side."""
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


def pt_in_circle(center: 'Vec2', radius: float, point: 'Vec2') -> bool:
    """Returns whether point is inside the circle with the given center and radius."""
    return (point - center).norm_sq <= radius ** 2


def pt_in_rect(pos: 'Vec2', rect: Rect) -> bool:
    """Returns whether the given position is within the rectangle, inclusive."""
    end = rect.position + rect.size
    return pos.x >= rect.position.x and pos.y >= rect.position.y and pos.x <= end.x and \
        pos.y <= end.y


class Orientation(Enum):
    CLOCKWISE = 0
    COUNTERCLOCKWISE = 1
    COLINEAR = 2


def determinant(v1: 'Vec2', v2: 'Vec2'):
    """Computes the 2D determinant of the two vectors."""
    return v1.x * v2.y - v2.x * v1.y


def orientation(p1: 'Vec2', p2: 'Vec2', p3: 'Vec2') -> Orientation:
    """Compute the orientation of the three points listed in order."""
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


def segment_rect_intersection(segment: Tuple[Vec2, Vec2], rect: Rect) -> Optional[Vec2]:
    sides = rect.sides()
    for side in sides:
        x = segments_intersect(side, segment)
        if x is not None:
            return x
    return None


def linear_coefficients(p: 'Vec2', q: 'Vec2') -> Tuple[float, float]:
    """Given two points that define a line ax + c, return (a, c)"""
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


def rotate_unit(vec: 'Vec2', rad: float) -> 'Vec2':
    """Rotate a vector by rad radians and return the rotated *unit vector*.
    """
    angle = math.atan2(vec.y, vec.x)
    angle += rad
    return Vec2(math.cos(angle), math.sin(angle))

def calc_node_dimensions(x: int, y: int, ratio: float):
    """Resize node so that area is unchanged and y/x=ratio. Returns vector in form (x,y).
    """
    area = x * y
    height = round(math.sqrt(area * ratio))
    width = round(math.sqrt(area/ratio))
    return Vec2(width, height)