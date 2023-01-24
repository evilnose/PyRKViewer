"""
Arrow tip designer for reaction plugin.

Version 1.0.1: Author: Gary Geng (2020)
"""

# pylint: disable=maybe-no-member
from rkviewer.utils import opacity_mul
from rkviewer.canvas.state import ArrowTip
import wx
from typing import List, Tuple
from rkviewer.plugin import api
from rkviewer.plugin.classes import PluginMetadata, WindowedPlugin, PluginCategory
from rkviewer.plugin.api import Vec2


class DesignerWindow(wx.Window):
    """
    The arrow designer window.
    """
    def __init__(self, parent, arrow_tip: ArrowTip):
        """
        Initialize the arrow designer window with the given starting arrow tip.

        Args: 
            parent: The parent window.
            arrow_tip: ArrowTip object defining the arrow tip used.
        """
        dim = Vec2(22, 16)
        self.csize = 20
        size = dim * self.csize + Vec2.repeat(1)
        super().__init__(parent, size=size.as_tuple())
        # add 1 to range end, so that the grid rectangle side will be included.
        rows = [r for r in range(0, int(size.y), self.csize)]
        cols = [c for c in range(0, int(size.x), self.csize)]

        self.begin_points = list()
        self.end_points = list()

        for r in rows:
            self.begin_points.append(wx.Point2D(0, r))
            self.end_points.append(wx.Point2D(size.x - 1, r))

        for c in cols:
            self.begin_points.append(wx.Point2D(c, 0))
            self.end_points.append(wx.Point2D(c, size.y - 1))

        self.handle_c = api.get_theme('handle_color')
        self.hl_handle_c = api.get_theme('highlighted_handle_color')
        self.handle_pen = wx.Pen(self.handle_c)
        self.hl_handle_pen = wx.Pen(self.hl_handle_c)
        self.handle_brush = wx.Brush(self.handle_c)
        self.hl_handle_brush = wx.Brush(self.hl_handle_c)
        phantom_c = opacity_mul(self.handle_c, 0.5)
        self.phantom_pen = wx.Pen(phantom_c)
        self.phantom_brush = wx.Brush(phantom_c)

        self.arrow_tip = arrow_tip
        self.radius = 12
        self.radius_sq = self.radius ** 2
        self.hover_idx = -1
        self.dragged_point = None
        self.dragging = False
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.SetDoubleBuffered(True)

    def OnPaint(self, evt):
        """
        Overrides wx Paint event to draw the grid, arrow, etc. as if on a canvas.

        Args: 
            self: the Designer Window to initialize.
            evt: the event being executed.

        """
        dc = wx.PaintDC(self)
        gc = wx.GraphicsContext.Create(dc)
        self.draw_background(gc)
        self.draw_points(gc, self.arrow_tip.points, self.radius)
        evt.Skip()

    def OnLeftDown(self, evt: wx.MouseEvent):
        """
        Handler for mouse left button down event.
        """
        if self.hover_idx != -1:
            self.dragging = True

    def OnLeftUp(self, evt: wx.MouseEvent):
        """
        Handler for mouse left button up event.
        """
        if self.dragging:
            assert self.dragged_point is not None
            drop = self.projected_landing(self.dragged_point)
            assert self.hover_idx != -1
            self.dragging = False
            self.arrow_tip.points[self.hover_idx] = Vec2(drop.x // self.csize, drop.y // self.csize)
            self.update_hover_idx(Vec2(evt.GetPosition()))
            self.Refresh()

    def update_arrow_tip(self, arrow_tip: ArrowTip):
        """
        Updating the current arrow tip in designer.

        Args: 
            self: the Designer Window to initialize.
            arrow_tip: modified arrow tip.

        """
        self.arrow_tip = arrow_tip
        self.Refresh()

    def projected_landing(self, point: Vec2) -> Vec2:
        """
        Return the projected discrete landing point for the cursor.

        This is to make sure the user sees where the dragged arrow tip point will be dropped on
        the grid.

        Args: 
            point: The cursor position relative to the window.

        Returns:
            Vec2 : projected point for landing.
        """
        lx = point.x - point.x % self.csize
        ly = point.y - point.y % self.csize
        drop_x: float
        drop_y: float

        if point.x - lx < self.csize / 2:
            drop_x = lx
        else:
            drop_x = lx + self.csize

        if point.y - ly < self.csize / 2:
            drop_y = ly
        else:
            drop_y = ly + self.csize

        return Vec2(drop_x, drop_y)

    def OnMotion(self, evt: wx.MouseEvent):
        """
        Handler for mouse motion events.

        Args: 
            self: the Designer Window to initialize.
            evt: the event being executed.

        """
        pos = Vec2(evt.GetPosition())
        if self.dragging:
            self.dragged_point = pos
        else:
            self.update_hover_idx(pos)
            evt.Skip()
        self.Refresh()

    def update_hover_idx(self, pos: Vec2):
        """
        Helper to update the hovered arrow tip point index.
        """
        self.hover_idx = -1

        for i, pt in enumerate(self.arrow_tip.points):
            pt *= self.csize
            if (pos - pt).norm_sq <= self.radius_sq:
                self.hover_idx = i
                break

    def draw_background(self, gc: wx.GraphicsContext):
        """
        Drawing the gridlines background.
        """
        gc.SetPen(wx.Pen(wx.BLACK))
        gc.StrokeLineSegments(self.begin_points, self.end_points)

    def draw_points(self, gc: wx.GraphicsContext, points: List[Vec2], radius: float):
        """
        Drawing points for arrow.

        Args: 
            gc: The Graphics context to modify.
            points: The points to be drawn, in counterclockwise order, with the last point being
                    the tip.
            radius: The radius of the points.
        """
        gc.SetPen(wx.Pen(wx.BLACK, 2))
        gc.SetBrush(wx.Brush(wx.BLACK, wx.BRUSHSTYLE_FDIAGONAL_HATCH))
        plotted = [p * self.csize for p in points]  # points to be plotted
        if self.dragging:
            assert self.hover_idx != -1 and self.dragged_point is not None
            plotted[self.hover_idx] = self.dragged_point

        gc.DrawLines([wx.Point2D(*p) for p in plotted] + [wx.Point2D(*plotted[0])])
        for i, p in enumerate(plotted):
            if self.dragging and i == self.hover_idx:
                continue
            if i == 3:
                # the last point is the tip, so draw it in a different color
                gc.SetPen(wx.BLACK_PEN)
                gc.SetBrush(wx.BLACK_BRUSH)
            else:
                gc.SetPen(self.handle_pen)
                gc.SetBrush(self.handle_brush)
            self.draw_point(gc, p, radius)

        # Draw the hover point
        if self.hover_idx != -1:
            point = self.dragged_point if self.dragging else plotted[self.hover_idx]
            assert self.hover_idx >= 0 and self.hover_idx < 4
            assert point is not None
            gc.SetPen(self.hl_handle_pen)
            gc.SetBrush(self.hl_handle_brush)
            self.draw_point(gc, point, radius)

            if self.dragging:
                assert self.dragged_point is not None
                drop_point = self.projected_landing(self.dragged_point)
                gc.SetPen(self.phantom_pen)
                gc.SetBrush(self.phantom_brush)
                self.draw_point(gc, drop_point, radius)

    def draw_point(self, gc: wx.GraphicsContext, point: Vec2, radius: float):
        """
        Drawing a single point.

        Args: 
            gc: Graphics context to modify.
            point: Point to be drawn.
            radius: Radius of the point.
        """
        center = point - Vec2.repeat(radius / 2)
        gc.DrawEllipse(center.x, center.y, radius, radius)


class ArrowDesigner(WindowedPlugin):
    """
    The ArrowDesigner plugin that subclasses WindowedPlugin.
    """
    metadata = PluginMetadata(
        name='ArrowDesigner',
        author='Gary Geng',
        version='1.0.1',
        short_desc='Arrow tip designer for reactions.',
        long_desc='Arrow tip designer for reactions.',
        category=PluginCategory.APPEARANCE,
    )
    def __init__(self):
        super().__init__()
        self.arrow_tip = api.get_arrow_tip()

    def create_window(self, dialog):
        """
        Called when creating a window. Create the designer window as well as control buttons.
        """
        window = wx.Window(dialog, size=(500, 500))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.designer = DesignerWindow(window, self.arrow_tip)
        save_btn = wx.Button(window, label='Save')
        save_btn.Bind(wx.EVT_BUTTON, self.OnSave)
        restore_btn = wx.Button(window, label='Restore default')
        restore_btn.Bind(wx.EVT_BUTTON, self.OnRestore)
        sizerflags = wx.SizerFlags().Align(wx.ALIGN_CENTER_HORIZONTAL).Border(wx.TOP, 20)
        sizer.Add(self.designer, sizerflags)
        sizer.Add(save_btn, sizerflags)
        sizer.Add(restore_btn, sizerflags)
        #dialog.SetSizer(sizer)
        window.SetSizer(sizer)
        return window

    def OnSave(self, evt):
        """
        Handler for the "save" button. Save the new arrow tip.
        """
        api.set_arrow_tip(self.arrow_tip)
        api.refresh_canvas()

    def OnRestore(self, evt):
        """
        Update the arrow point to be set to default values.
        """
        default_tip = api.get_default_arrow_tip()
        api.set_arrow_tip(default_tip)
        self.designer.update_arrow_tip(default_tip)
