import wx
import IodineAPI


# pylint: disable=maybe-no-member
class Toolbar(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.select_btn = wx.ToggleButton(self, label='select')
        self.add_btn = wx.ToggleButton(self, label='add')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.select_btn, wx.SizerFlags().Align(wx.ALIGN_CENTER).Border(wx.TOP, 10))
        sizer.Add(self.add_btn, wx.SizerFlags().Align(wx.ALIGN_CENTER).Border(wx.TOP, 10))
        self.SetSizer(sizer)


# pylint: disable=maybe-no-member
class NodeRect(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, evt):
        # Create paint DC
        dc = wx.PaintDC(self)

        # Create graphics context from it
        gc = wx.GraphicsContext.Create(dc)

        if gc:
            width, height = self.GetSize()
            # make a path that contains a circle and some lines
            brush = wx.Brush(wx.Colour(0, 255, 0, 50), wx.BRUSHSTYLE_SOLID)
            gc.SetBrush(brush)
            gc.SetPen(wx.RED_PEN)
            path = gc.CreatePath()
            path.AddRectangle(0.0, 0.0, width - 1, height - 1)

            gc.FillPath(path)
            gc.StrokePath(path)


# pylint: disable=maybe-no-member
class Canvas(wx.Panel):
    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, **kw)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)


    def OnLeftDown(self, event):
        x, y = event.GetPosition()
        w, h = (50, 30)
        NodeRect(self, size=(w, h), pos=(x - w/2, y - h/2))
        self.Refresh()


# pylint: disable=maybe-no-member
class ExampleFrame(wx.Frame):

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super().__init__(*args, **kw)

        # create a panel in the frame
        self.toolbar = Toolbar(self, size=(120, 500))
        self.toolbar.SetBackgroundColour(wx.WHITE)

        self.canvas = Canvas(self, size=(630, 500))
        self.canvas.SetBackgroundColour(wx.WHITE)

        # and create a sizer to manage the layout of child widgets
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.toolbar, wx.SizerFlags().Border(wx.TOP|wx.LEFT, 10))
        sizer.Add(self.canvas, wx.SizerFlags().Border(wx.TOP|wx.LEFT, 10))
        self.SetSizer(sizer)

        # and a status bar
        self.CreateStatusBar()
        self.SetStatusText("Welcome to wxPython!")


if __name__ == '__main__':
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    app = wx.App()
    frm = ExampleFrame(None, title='Example', size=(800, 600))
    frm.Show()
    app.MainLoop()

