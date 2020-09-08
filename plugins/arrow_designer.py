# pylint: disable=maybe-no-member
import wx
from rkplugin import api
from rkplugin.plugins import PluginMetadata, WindowedPlugin
from rkplugin.api import Vec2

metadata = PluginMetadata(
    name='ArrowDesigner',
    author='Gary Geng',
    version='0.0.1',
    short_desc='Arrow tip designer for reactions.',
    long_desc='Arrow tip designer for reactions.'
)


class Grid:
    def __init__(self, size: Vec2, clen: int):
        self.size = size
        self.anchor = size / 2
        # add 1 to range end, so that the grid rectangle side will be included.
        rows = [r for r in range(int(self.anchor.y % clen), int(size.y), clen)]
        cols = [c for c in range(int(self.anchor.x % clen), int(size.x), clen)]

        self.draw_points = list()

        for r in rows:
            self.draw_points.append((0, r, size.x - 1, r))

        for c in cols:
            self.draw_points.append((c, 0, c, size.y - 1))

    def draw(self, dc: wx.DC):
        dc.DrawLineList(self.draw_points, wx.Pen(wx.BLACK))
        dc.SetPen(wx.Pen(wx.BLACK, 3))
        dc.DrawLine(0, self.anchor.y, self.size.x - 1, self.anchor.y)


class DesignerWindow(wx.Window):
    def __init__(self, parent, grid: Grid):
        super().__init__(parent, size=grid.size.as_tuple())
        self.grid = grid
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        self.grid.draw(dc)
        evt.Skip()


class ArrowDesigner(WindowedPlugin):
    def __init__(self):
        super().__init__(metadata)
        self.grid = Grid(Vec2(450, 300), 20)

    def create_window(self, dialog):
        window = wx.Window(dialog, size=(500, 500))
        sizer = wx.BoxSizer(wx.VERTICAL)
        designer = DesignerWindow(window, self.grid)
        save_btn = wx.Button(window, label='Save')
        sizerflags = wx.SizerFlags().Align(wx.ALIGN_CENTER_HORIZONTAL)
        sizer.Add(designer, sizerflags)
        sizer.Add(save_btn, sizerflags)
        dialog.SetSizer(sizer)
        return window
