# pylint: disable=maybe-no-member
import wx
import copy
from typing import Callable, List, Dict, Any, Optional, Set, Tuple
from .canvas.events import EVT_DID_DRAG_MOVE_NODES, EVT_DID_DRAG_RESIZE_NODES, \
    EVT_DID_SELECT_NODES, EVT_DID_UPDATE_NODES
from .canvas.wx import Canvas, InputMode
from .config import DEFAULT_SETTINGS, DEFAULT_THEME, DEFAULT_SETTINGS
from .mvc import IController, IView
from .utils import Node, Rect, Vec2, clamp_rect_size, decode_rgba, encode_rgba, get_nodes_by_ids, no_rzeros, \
    clamp_rect_pos, on_msw, rgba_to_wx_colour, wx_colour_to_rgb
from .canvas.utils import get_bounding_rect
from .widgets import ButtonGroup


class EditPanel(wx.Panel):
    canvas: Canvas
    controller: IController
    _nodes: List[Node]
    ColorCallback = Callable[[wx.Colour], None]
    FloatCallback = Callable[[float], None]

    def __init__(self, parent, canvas: Canvas, controller: IController, theme: Dict[str, Any],
                 settings: Dict[str, Any], **kw):
        super().__init__(parent, **kw)
        self.canvas = canvas
        self.controller = controller
        self.theme = theme
        self.settings = settings
        self._nodes = list()
        self._selected_ids = set()
        self._label_font = wx.Font(wx.FontInfo().Bold())
        info_image = wx.Image('resources/info-2-16.png', wx.BITMAP_TYPE_PNG)
        self._info_bitmap = wx.Bitmap(info_image)
        self._info_length = 16
        self.form = wx.Panel(self)
        self._title = wx.StaticText(self.form)  # only displayed when node(s) are selected
        title_font = wx.Font(wx.FontInfo(10))
        self._title.SetFont(title_font)
        self._subtitle = wx.StaticText(self)
        self._bounding_rect = None  # No padding
        self._dirty = False

        self.labels = dict()
        self.badges = dict()

        self.CreateControls()

        canvas.Bind(EVT_DID_UPDATE_NODES, self.OnDidUpdateNodes)
        canvas.Bind(EVT_DID_SELECT_NODES, self.OnDidSelectNodes)
        canvas.Bind(EVT_DID_DRAG_MOVE_NODES, self.OnDidDragMoveNodes)
        canvas.Bind(EVT_DID_DRAG_RESIZE_NODES, self.OnDidDragResizeNodes)

    def CreateControls(self):
        VGAP = 8
        HGAP = 5
        MORE_LEFT_PADDING = 0  # Left padding in addition to vgap
        MORE_TOP_PADDING = 5  # Top padding in addition to hgap
        MORE_RIGHT_PADDING = 0

        self.null_message = wx.StaticText(self, label="Nothing is selected.", style=wx.ALIGN_CENTER)

        form_sizer = wx.GridBagSizer(vgap=VGAP, hgap=HGAP)

        # Set paddings
        # Add spacer of width w on the 0th column; add spacer of height h on the 0th row.
        # This results in a left padding of w + hgap and a top padding of h + vgap
        form_sizer.Add(MORE_LEFT_PADDING, MORE_TOP_PADDING, wx.GBPosition(0, 0), wx.GBSpan(1, 1))
        # Add spacer on column 3 to reserve space for info badge
        form_sizer.Add(self._info_length, 0, wx.GBPosition(0, 3), wx.GBSpan(1, 1))
        # Add spacer of width 5 on the 3rd column. This results in a right padding of 5 + hgap
        form_sizer.Add(MORE_RIGHT_PADDING, 0, wx.GBPosition(0, 4), wx.GBSpan(1, 1))

        # Ensure the input field takes up some percentage of width
        width = self.GetSize()[0]
        right_width = (width - VGAP * 3 - MORE_LEFT_PADDING - MORE_RIGHT_PADDING -
                       self._info_length) * 0.6
        form_sizer.Add(right_width, 0, wx.GBPosition(0, 2), wx.GBSpan(1, 1))
        form_sizer.AddGrowableCol(0, 0.3)
        form_sizer.AddGrowableCol(1, 0.7)

        form_sizer.Add(self._title, wx.GBPosition(1, 0), wx.GBSpan(1, 5), flag=wx.ALIGN_CENTER)
        self.AppendSpacer(form_sizer, 6)

        # ID form control
        self.id_textctrl = wx.TextCtrl(self.form)
        self.id_textctrl.Bind(wx.EVT_TEXT, self.OnIdText)
        self.AppendControl(form_sizer, 'identifier', self.id_textctrl)

        self.pos_ctrl = wx.TextCtrl(self.form)
        self.pos_ctrl.Bind(wx.EVT_TEXT, self.OnPosText)
        self.AppendControl(form_sizer, 'position', self.pos_ctrl)

        self.size_ctrl = wx.TextCtrl(self.form)
        self.size_ctrl.Bind(wx.EVT_TEXT, self.OnSizeText)
        self.AppendControl(form_sizer, 'size', self.size_ctrl)

        self.fill_ctrl, self.fill_alpha_ctrl = self.CreateColorControl(
            'fill color', 'fill opacity',
            self.OnFillColorChanged, self.FillAlphaCallback,
            form_sizer)

        self.border_ctrl, self.border_alpha_ctrl = self.CreateColorControl(
            'border color', 'border opacity',
            self.OnBorderColorChanged, self.BorderAlphaCallback,
            form_sizer)

        self.border_width_ctrl = wx.TextCtrl(self.form)
        self.AppendControl(form_sizer, 'border width', self.border_width_ctrl)
        border_callback = self.MakeFloatCtrlFunction(self.border_width_ctrl.GetId(),
                                                     self.BorderWidthCallback, (1, 100))
        self.border_width_ctrl.Bind(wx.EVT_TEXT, border_callback)

        self.form.SetSizer(form_sizer)

        # overall sizer for alternating form and "nothing selected" displays
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.form, proportion=1, flag=wx.EXPAND)
        sizer.Add(self.null_message, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL)
        self.form.Show(False)
        self.null_message.Show(True)
        self.SetSizer(sizer)

    def AppendControl(self, sizer: wx.Sizer, label_str: str, ctrl: wx.Control):
        """Append a control, its label, and its info badge to the last row of the sizer.

        Returns the automaticaly created label and info badge (wx.StaticText for now).
        """
        label = wx.StaticText(self.form, label=label_str)
        label.SetFont(self._label_font)
        rows = sizer.GetRows()
        sizer.Add(label, wx.GBPosition(rows, 1), wx.GBSpan(1, 1),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        sizer.Add(ctrl, wx.GBPosition(rows, 2), wx.GBSpan(1, 1),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        sizer.Add(0, self._info_length, wx.GBPosition(rows, 4), wx.GBSpan(1, 1))

        info_badge = wx.StaticBitmap(self.form, bitmap=self._info_bitmap)
        sizer.Add(info_badge, wx.GBPosition(rows, 3), wx.GBSpan(1, 1),
                  flag=wx.ALIGN_CENTER)
        info_badge.Show(False)
        self.labels[ctrl.GetId()] = label
        self.badges[ctrl.GetId()] = info_badge

    def AppendSpacer(self, sizer: wx.Sizer, height: int):
        rows = sizer.GetRows()
        sizer.Add(0, height, wx.GBPosition(rows, 0), wx.GBSpan(1, 5))

    def CreateColorControl(self, label: str, alpha_label: str,
                           color_callback: ColorCallback, alpha_callback: FloatCallback,
                           sizer: wx.Sizer, alpha_range: Tuple[float, float] = (0, 1)) \
            -> Tuple[wx.ColourPickerCtrl, wx.TextCtrl]:
        ctrl = wx.ColourPickerCtrl(self.form)
        ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, color_callback)
        self.AppendControl(sizer, label, ctrl)

        alpha_ctrl = None

        if on_msw():
            # Windows does not support picking alpha in color picker. So we add an additional
            # field for that
            alpha_ctrl = wx.TextCtrl(self.form)
            self.AppendControl(sizer, alpha_label, alpha_ctrl)
            callback = self.MakeFloatCtrlFunction(alpha_ctrl.GetId(), alpha_callback, alpha_range)
            self.Bind(wx.EVT_TEXT, callback)

        return ctrl, alpha_ctrl

    def FillAlphaCallback(self, alpha: float):
        nodes = get_nodes_by_ids(self._nodes, self._selected_ids)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            self.controller.try_set_node_fill_alpha(node.id_, alpha)
        self.controller.try_end_group()

    def BorderAlphaCallback(self, alpha: float):
        nodes = get_nodes_by_ids(self._nodes, self._selected_ids)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            self.controller.try_set_node_border_alpha(node.id_, alpha)
        self.controller.try_end_group()

    def BorderWidthCallback(self, width: float):
        nodes = get_nodes_by_ids(self._nodes, self._selected_ids)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            self.controller.try_set_node_border_width(node.id_, width)
        self.controller.try_end_group()

    def MakeFloatCtrlFunction(self, ctrl_id: str,
                              callback: FloatCallback, range_: Tuple[float, float]):
        lo, hi = range_
        assert lo <= hi

        def float_ctrl_fn(evt):
            text = evt.GetString()
            value: float
            try:
                value = float(text)
            except ValueError:
                self.SetValidationState(False, ctrl_id, "Value must be a number")
                return

            if value < lo or value > hi:
                self.SetValidationState(
                    False, ctrl_id, "Value must be in range [{}, {}]".format(lo, hi))
                return

            callback(value)
            self.SetValidationState(True, ctrl_id)

        return float_ctrl_fn

    def OnIdText(self, evt):
        new_id = evt.GetString()
        assert len(self._selected_ids) == 1
        [old_id] = self._selected_ids
        ctrl_id = self.id_textctrl.GetId()
        if new_id != old_id:
            if len(new_id) == 0:
                self.SetValidationState(False, ctrl_id, "ID cannot be empty")
                return
            else:
                for node in self._nodes:
                    if node.id_ == new_id:
                        self.SetValidationState(False, ctrl_id, "Not saved: Duplicate ID")
                        return
                else:
                    # loop terminated fine. There is no duplicate ID
                    self._selected_ids.remove(old_id)
                    self._selected_ids.add(new_id)
                    self.canvas.UpdateSelectedIds(self._selected_ids)
                    self._dirty = True
                    if not self.controller.try_rename_node(old_id, new_id):
                        # this should not happen!
                        assert False
        self.SetValidationState(True, self.id_textctrl.GetId())

    def OnPosText(self, evt):
        text = evt.GetString()
        xy = self.ParseNumPair(text)
        ctrl_id = self.pos_ctrl.GetId()
        if xy is None:
            self.SetValidationState(False, ctrl_id, 'Should be in the form "X, Y"')
            return

        pos = Vec2(xy)
        if pos.x < 0 or pos.y < 0:
            self.SetValidationState(False, ctrl_id, 'Position coordinates should be non-negative')
            return
        nodes = get_nodes_by_ids(self._nodes, self._selected_ids)
        bounds = Rect(Vec2(), self.canvas.realsize)
        clamped = None
        if len(nodes) == 1:
            [node] = nodes

            clamped = clamp_rect_pos(Rect(pos, node.size), bounds)
            if node.position != clamped or pos != clamped:
                self._dirty = True
                self.controller.try_move_node(node.id_, Vec2(clamped.x, clamped.y))
        else:
            clamped = clamp_rect_pos(Rect(pos, self._bounding_rect.size), bounds)
            if self._bounding_rect.position != pos or pos != clamped:
                offset = clamped - self._bounding_rect.position
                self._dirty = True
                self.controller.try_start_group()
                for node in nodes:
                    self.controller.try_move_node(node.id_, node.position + offset)
                self.controller.try_end_group()
        self.SetValidationState(True, self.pos_ctrl.GetId())

    def OnSizeText(self, evt):
        ctrl_id = self.size_ctrl.GetId()
        text = evt.GetString()
        wh = self.ParseNumPair(text)
        if wh is None:
            self.SetValidationState(False, ctrl_id, 'Should be in the form "width, height"')
            return

        nodes = get_nodes_by_ids(self._nodes, self._selected_ids)
        min_width = self.theme['min_node_width']
        min_height = self.theme['min_node_height']
        size = Vec2(wh)
        if len(nodes) == 1:
            [node] = nodes

            if size.x < min_width or size.y < min_height:
                message = 'Node size needs to be at least ({}, {})'.format(min_width, min_height)
                self.SetValidationState(False, ctrl_id, message)
                return

            clamped = clamp_rect_size(Rect(node.position, size), self.canvas.realsize)
            if node.size != clamped or size != clamped:
                self._dirty = True
                self.controller.try_set_node_size(node.id_, Vec2(clamped.x, clamped.y))
        else:
            min_nw = min(n.size.x for n in nodes)
            min_nh = min(n.size.y for n in nodes)
            min_ratio = Vec2(min_width / min_nw, min_height / min_nh)
            limit = self._bounding_rect.size.elem_mul(min_ratio)

            if size.x < limit.x or size.y < limit.y:
                message = 'Size of bounding box needs to be at least ({}, {})'.format(
                    no_rzeros(limit.x, 2), no_rzeros(limit.y, 2))
                self.SetValidationState(False, ctrl_id, message)
                return

            clamped = clamp_rect_size(Rect(self._bounding_rect.position, size),
                                      self.canvas.realsize)
            if self._bounding_rect.size != clamped or size != clamped:
                ratio = clamped.elem_div(self._bounding_rect.size)
                self._dirty = True
                self.controller.try_start_group()
                for node in nodes:
                    rel_pos = node.position - self._bounding_rect.position
                    self.controller.try_move_node(
                        node.id_, self._bounding_rect.position + rel_pos.elem_mul(ratio))
                    self.controller.try_set_node_size(node.id_, node.size.elem_mul(ratio))
                self.controller.try_end_group()
        self.SetValidationState(True, self.size_ctrl.GetId())

    def OnFillColorChanged(self, evt: wx.Event):
        fill = evt.GetColour()
        nodes = get_nodes_by_ids(self._nodes, self._selected_ids)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            if on_msw():
                self.controller.try_set_node_fill_rgb(node.id_, fill)
            else:
                # we can set both the RGB and the alpha at the same time
                self.controller.try_set_node_fill_rgb(node.id_, fill)
                self.controller.try_set_node_fill_alpha(node.id_, fill.Alpha())
        self.controller.try_end_group()

    def OnBorderColorChanged(self, evt: wx.Event):
        border = evt.GetColour()
        nodes = get_nodes_by_ids(self._nodes, self._selected_ids)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            if on_msw():
                self.controller.try_set_node_border_rgb(node.id_, border)
            else:
                # we can set both the RGB and the alpha at the same time
                self.controller.try_set_node_border_rgb(node.id_, border)
                self.controller.try_set_node_border_alpha(node.id_, border.Alpha())
        self.controller.try_end_group()

    def _SetBestInsertion(self, ctrl: wx.TextCtrl, orig_text: str, orig_insertion: int):
        """Set the most natural insertion point for a paired-number text control.

        The format of the text control must be "X,Y" where X, Y are numbers, allowing whitespace.
        This should be called after the text control is manually changed by View during user's
        editing. Normally if the text changes the caret will be reset to the 0th position, but this
        calculates a smarter position to place the caret to produce a more natural behavior.

        Args:
            ctrl: The text control, whose value is already programmatically changed.
            orig_text: The value of the text control before it was changed.
            orig_insertion: The original caret position from GetInsertionPoint().
        """
        new_text = ctrl.GetValue()
        mid = orig_text.index(',')

        if orig_insertion > mid:
            ctrl.SetInsertionPoint(len(new_text))
        else:
            tokens = new_text.split(',')
            assert len(tokens) == 2

            left = tokens[0].strip()
            lstart = new_text.index(left)
            lend = lstart + len(left)
            ctrl.SetInsertionPoint(lend)

    def ParseNumPair(self, text: str) -> Optional[Tuple[float, float]]:
        """Parse a pair of floats from a string with form "X,Y" and return a tuple.

        Returns None if failed to parse.
        """
        nums = text.split(",")
        if len(nums) != 2:
            return None

        xstr, ystr = nums
        x = None
        y = None
        try:
            x = float(xstr)
            y = float(ystr)
        except ValueError:
            return None

        return (x, y)

    def ParsePrecisions(self, text: str) -> Tuple[int, int]:
        nums = text.split(",")
        assert len(nums) == 2

        xstr = nums[0].strip()
        ystr = nums[1].strip()
        x_prec = None
        try:
            x_prec = len(xstr) - xstr.index('.') - 1
        except ValueError:
            x_prec = 0

        y_prec = None
        try:
            y_prec = len(xstr) - ystr.index('.') - 1
        except ValueError:
            y_prec = 0

        return (x_prec, y_prec)

    def SetValidationState(self, good: bool, ctrl_id: str, message: str = ""):
        badge = self.badges[ctrl_id]
        if good:
            badge.Show(False)
        else:
            badge.Show(True)
            badge.SetToolTip(message)
        self.form.GetSizer().Layout()

    def OnDidUpdateNodes(self, evt):
        self._nodes = evt.nodes
        if len(self._selected_ids) != 0 and not self._dirty:
            self.UpdateAllFields()

        self._dirty = False

        # clear validation errors
        for id_ in self.badges.keys():
            self.SetValidationState(True, id_)

    def OnDidSelectNodes(self, evt):
        self._selected_ids = evt.node_ids
        if len(evt.node_ids) == 0:
            self.form.Show(False)
            self.null_message.Show(True)
        else:
            self.pos_ctrl.ChangeValue('')
            self.UpdateAllFields()

            title_label = 'Edit Node' if len(evt.node_ids) == 1 else 'Edit Multiple Nodes'
            self._title.SetLabel(title_label)

            id_text = 'identifier' if len(evt.node_ids) == 1 else 'identifiers'
            self.labels[self.id_textctrl.GetId()].SetLabel(id_text)

            size_text = 'size' if len(evt.node_ids) == 1 else 'total span'
            self.labels[self.size_ctrl.GetId()].SetLabel(size_text)

            self.null_message.Show(False)
            self.form.Show(True)
        self.GetSizer().Layout()

    def OnDidDragMoveNodes(self, evt):
        # HACK only need to update position field here
        self.UpdateAllFields()

    def OnDidDragResizeNodes(self, evt):
        # HACK only need to update size field here
        self.UpdateAllFields()

    def UpdateAllFields(self):
        assert len(self._selected_ids) != 0
        nodes = get_nodes_by_ids(self._nodes, self._selected_ids)
        prec = self.settings['decimal_precision']
        id_text: str
        pos: Vec2
        size: Vec2
        fill: wx.Colour
        fill_alpha: Optional[int]
        border: wx.Colour
        border_alpha: Optional[int]
        if len(self._selected_ids) == 1:
            [node] = nodes
            self.id_textctrl.Enable(True)
            id_text = next(iter(self._selected_ids))
            '''
            pos_text = '{}, {}'.format(no_trailing_zeros(node.position.x, prec),
                                       no_trailing_zeros(node.position.y, prec))
            '''
            pos = node.position
            size = node.size
            fill = node.fill_color
            fill_alpha = node.fill_color.Alpha()
            border = node.border_color
            border_alpha = node.border_color.Alpha()
        else:
            self.id_textctrl.Enable(False)
            id_text = '; '.join(sorted(list(self._selected_ids)))

            self._bounding_rect = get_bounding_rect([n.rect for n in nodes])
            pos = self._bounding_rect.position
            size = self._bounding_rect.size

            fill, fill_alpha = self.GetMultiColor(list(n.fill_color for n in nodes))
            border, border_alpha = self.GetMultiColor(list(n.border_color for n in nodes))

        border_width = self.GetMultiFloatText(set(n.border_width for n in nodes), prec)

        self.id_textctrl.ChangeValue(id_text)
        self.ChangePairValue(self.pos_ctrl, pos, prec)
        self.ChangePairValue(self.size_ctrl, size, prec)
        self.fill_ctrl.SetColour(fill)
        self.border_ctrl.SetColour(border)

        # set fill alpha if on windows
        if on_msw():
            self.fill_alpha_ctrl.ChangeValue(self._AlphaToText(fill_alpha, prec))
            self.border_alpha_ctrl.ChangeValue(self._AlphaToText(border_alpha, prec))

        self.border_width_ctrl.ChangeValue(border_width)

    def GetMultiColor(self, colors: List[wx.Colour]) -> Tuple[wx.Colour, Optional[int]]:
        if on_msw():
            rgbset = set(c.GetRGB() for c in colors)
            rgb = copy.copy(wx.BLACK)
            if len(rgbset) == 1:
                rgb.SetRGB(next(iter(rgbset)))

            alphaset = set(c.Alpha() for c in colors)
            alpha = next(iter(alphaset)) if len(alphaset) == 1 else None
            return rgb, alpha
        else:
            rgbaset = set(c.GetRGBA() for c in colors)
            rgba = copy.copy(wx.BLACK)
            if len(rgbaset) == 1:
                rgba.SetRGBA(next(iter(rgbaset)))

            return rgba, None

    def GetMultiFloatText(self, values: Set[float], precision: int) -> str:
        return no_rzeros(next(iter(values)), precision) if len(values) == 1 else '?'

    def _AlphaToText(self, alpha: Optional[int], prec: int) -> str:
        if alpha is None:
            return '?'
        else:
            return no_rzeros(alpha / 255, prec)

    def ChangePairValue(self, ctrl: wx.TextCtrl, new_val: Vec2, prec: int):
        old_text = ctrl.GetValue()
        old_val = Vec2(self.ParseNumPair(old_text))

        # round old_val to desired precision. We don't want to refresh value when user is typing,
        # even if their value exceeded our precision
        if old_val != new_val:
            if ctrl.HasFocus():
                orig_insertion = ctrl.GetInsertionPoint()
                wx.CallAfter(
                    lambda: self._SetBestInsertion(ctrl, old_text, orig_insertion))
            ctrl.ChangeValue('{}, {}'.format(
                no_rzeros(new_val.x, prec), no_rzeros(new_val.y, prec)))


class TopToolbar(wx.Panel):
    """Toolbar at the top of the app."""

    def __init__(self, parent, controller: IController, zoom_callback, edit_panel_callback, **kw):
        super().__init__(parent, **kw)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        zoom_in_btn = wx.Button(self, label="Zoom In")
        # TODO make this a method
        sizer.Add(zoom_in_btn, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        zoom_in_btn.Bind(wx.EVT_BUTTON, lambda _: zoom_callback(True))

        zoom_out_btn = wx.Button(self, label="Zoom Out")
        sizer.Add(zoom_out_btn, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        zoom_out_btn.Bind(wx.EVT_BUTTON, lambda _: zoom_callback(False))

        undo_button = wx.Button(self, label="Undo")
        sizer.Add(undo_button, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        undo_button.Bind(wx.EVT_BUTTON, lambda _: controller.try_undo())

        redo_button = wx.Button(self, label="Redo")
        sizer.Add(redo_button, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.LEFT, 10))
        redo_button.Bind(wx.EVT_BUTTON, lambda _: controller.try_redo())

        # Note: Right align after this
        sizer.Add((0, 0), proportion=1, flag=wx.EXPAND)

        toggle_panel_button = wx.Button(self, label="Details")
        sizer.Add(toggle_panel_button, wx.SizerFlags().Align(wx.ALIGN_CENTER_VERTICAL).Border(wx.RIGHT, 10))
        toggle_panel_button.Bind(wx.EVT_BUTTON, edit_panel_callback)

        self.SetSizer(sizer)


class Toolbar(wx.Panel):
    """Toolbar at the left of the app."""

    def __init__(self, *args, toggle_callback, **kw):
        super().__init__(*args, **kw)
        sizer = wx.BoxSizer(wx.VERTICAL)
        select_btn = wx.ToggleButton(
            self, label='&Select')
        sizer.Add(select_btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER).Border(wx.TOP, 10))
        add_btn = wx.ToggleButton(
            self, label='&Add')
        sizer.Add(add_btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER).Border(wx.TOP, 10))
        zoom_btn = wx.ToggleButton(
            self, label='&Zoom')
        sizer.Add(zoom_btn, wx.SizerFlags().Align(
            wx.ALIGN_CENTER).Border(wx.TOP, 10))

        btn_group = ButtonGroup(toggle_callback)
        btn_group.AddButton(select_btn, InputMode.SELECT)
        btn_group.AddButton(add_btn, InputMode.ADD)
        btn_group.AddButton(zoom_btn, InputMode.ZOOM)

        self.SetSizer(sizer)


class MainPanel(wx.Panel):
    """The main panel, which is the only chlid of the root Frame."""
    controller: IController
    theme: Dict[str, Any]

    def __init__(self, parent, controller: IController, theme: Dict[str, Any],
                 settings: Dict[str, Any]):
        # ensure the parent's __init__ is called
        super().__init__(parent, style=wx.CLIP_CHILDREN)
        self.SetBackgroundColour(theme['overall_bg'])
        self.controller = controller
        self.theme = theme

        self.canvas = Canvas(self.controller, self,
                             size=(theme['canvas_width'], theme['canvas_height']),
                             realsize=(4 * theme['canvas_width'], 4 * theme['canvas_height']),
                             theme=theme,
                             settings=settings,)
        self.canvas.SetScrollRate(10, 10)

        # The bg of the available canvas will be drawn by canvas in OnPaint()
        self.canvas.SetBackgroundColour(theme['canvas_outside_bg'])

        def set_input_mode(ident):
            self.canvas.input_mode = ident

        # create a panel in the frame
        self.toolbar = Toolbar(self,
                               size=(theme['left_toolbar_width'],
                                     theme['canvas_height']),
                               toggle_callback=set_input_mode)
        self.toolbar.SetBackgroundColour(theme['toolbar_bg'])

        top_toolbar_width = theme['canvas_width'] + theme['edit_panel_width'] + theme['vgap']
        self.top_toolbar = TopToolbar(self, controller,
                                      size=(top_toolbar_width, theme['top_toolbar_height']),
                                      zoom_callback=self.canvas.ZoomCenter,
                                      edit_panel_callback=self.ToggleEditPanel)
        self.top_toolbar.SetBackgroundColour(theme['toolbar_bg'])

        self.edit_panel = EditPanel(self, self.canvas, self.controller, self.theme, settings,
                                    size=(theme['edit_panel_width'],
                                          theme['canvas_height']))
        self.edit_panel.SetBackgroundColour(theme['toolbar_bg'])

        self.buffer = None

        # and create a sizer to manage the layout of child widgets
        sizer = wx.GridBagSizer(vgap=theme['vgap'], hgap=theme['hgap'])

        sizer.Add(self.top_toolbar, wx.GBPosition(0, 1), wx.GBSpan(1, 2), flag=wx.EXPAND)
        sizer.Add(self.toolbar, wx.GBPosition(1, 0), flag=wx.EXPAND)
        sizer.Add(self.canvas, wx.GBPosition(1, 1),  flag=wx.EXPAND)
        sizer.Add(self.edit_panel, wx.GBPosition(1, 2), flag=wx.EXPAND)

        # allow the canvas to grow
        sizer.AddGrowableCol(1, 1)
        sizer.AddGrowableRow(1, 1)

        # Set the sizer and *prevent the user from resizing it to a smaller size*
        # TODO are we sure we want this behavior?
        self.SetSizer(sizer)

    def OnNodeDrop(self, obj: wx.Window, pos: wx.Point):
        if obj == self.canvas:
            self.canvas.OnNodeDrop(pos)

    def ToggleEditPanel(self, evt):
        sizer = self.GetSizer()
        if self.edit_panel.IsShown():
            self.edit_panel.Hide()
            sizer.Detach(self.edit_panel)
            sizer.SetItemSpan(self.canvas, wx.GBSpan(1, 2))
        else:
            sizer.SetItemSpan(self.canvas, wx.GBSpan(1, 1))
            sizer.Add(self.edit_panel, wx.GBPosition(1, 2), flag=wx.EXPAND)
            self.edit_panel.Show()

        self.Layout()


class MyFrame(wx.Frame):
    """The main frame."""

    def __init__(self, controller: IController, theme, settings, **kw):
        super().__init__(None, **kw)
        status_fields = settings['status_fields']
        assert status_fields is not None
        self.CreateStatusBar(len(DEFAULT_SETTINGS['status_fields']))
        self.SetStatusWidths([width for _, width in status_fields])
        self.main_panel = MainPanel(self, controller, theme=theme, settings=settings)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.main_panel, 1, wx.EXPAND)
        self.SetSizerAndFit(sizer)


class View(IView):
    """Implementation of the view class."""

    def __init__(self, theme=DEFAULT_THEME, settings=DEFAULT_SETTINGS):
        self.controller = None
        self.theme = copy.copy(theme)
        self.settings = copy.copy(settings)

    def bind_controller(self, controller: IController):
        self.controller = controller

    def main_loop(self):
        assert self.controller is not None
        app = wx.App()
        frm = MyFrame(self.controller, self.theme, self.settings, title='RK Network Viewer')
        self.canvas_panel = frm.main_panel.canvas
        self.canvas_panel.RegisterAllChildren(frm)
        frm.Show()
        app.MainLoop()

    def update_all(self, nodes: List[Node]):
        """Update the list of nodes.

        Note that View takes ownership of the list of nodes and may modify it.
        """
        self.canvas_panel.ResetNodes(nodes)
        self.canvas_panel.Refresh()
