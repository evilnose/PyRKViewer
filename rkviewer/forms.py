"""All sorts of form widgets, mainly those used in EditPanel.
"""
# pylint: disable=maybe-no-member
from rkviewer.mvc import IController
import wx
from abc import abstractmethod
import copy
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from .canvas.canvas import Canvas
from .canvas.reactions import Reaction
from .canvas.utils import get_bounding_rect
from .utils import Node, Rect, Vec2, clamp_rect_pos, clamp_rect_size, get_nodes_by_idx, \
    no_rzeros, on_msw, resource_path
from .config import theme, settings


def parse_num_pair(text: str) -> Optional[Tuple[float, float]]:
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


def parse_precisions(text: str) -> Tuple[int, int]:
    """Given a string in format 'X, Y' of floats, return the decimal precisions of X and Y."""
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


class EditPanelForm(wx.Panel):
    """Base class for a form to be displayed on the edit panel.

    Attributes:
        ColorCallback: Callback type for when a color input is changed.
        FloatCallback: Callback type for when a float input is changed.
        canvas: The associated canvas.
        controller: The associated controller.
        net_index: The current network index. For now it is 0 since there is only one tab.
    """
    ColorCallback = Callable[[wx.Colour], None]
    FloatCallback = Callable[[float], None]

    canvas: Canvas
    controller: IController
    net_index: int
    labels: Dict[str, wx.Window]
    badges: Dict[str, wx.Window]
    _label_font: wx.Font  #: font for the form input label.
    _info_bitmap: wx.Image  # :  bitmap for the info badge (icon), for when an input is invalid.
    _info_length: int  #: length of the square reserved for _info_bitmap
    _title: wx.StaticText  #: title of the form
    _dirty: bool  #: flag for if edits were made but the controller hasn't updated the view yet

    def __init__(self, parent, canvas: Canvas, controller: IController):
        super().__init__(parent)
        self.canvas = canvas
        self.controller = controller
        self.net_index = 0
        self.labels = dict()
        self.badges = dict()
        self._label_font = wx.Font(wx.FontInfo().Bold())
        info_image = wx.Image(resource_path('info-2-16.png'), wx.BITMAP_TYPE_PNG)
        self._info_bitmap = wx.Bitmap(info_image)
        self._info_length = 16
        self._title = wx.StaticText(self)  # only displayed when node(s) are selected
        title_font = wx.Font(wx.FontInfo(10))
        self._title.SetFont(title_font)
        self._dirty = False

    @abstractmethod
    def UpdateAllFields(self):
        pass

    def InitAndGetSizer(self) -> wx.Sizer:
        VGAP = 8
        HGAP = 5
        MORE_LEFT_PADDING = 0  # Left padding in addition to vgap
        MORE_TOP_PADDING = 2  # Top padding in addition to hgap
        MORE_RIGHT_PADDING = 0

        sizer = wx.GridBagSizer(vgap=VGAP, hgap=HGAP)

        # Set paddings
        # Add spacer of width w on the 0th column; add spacer of height h on the 0th row.
        # This results in a left padding of w + hgap and a top padding of h + vgap
        sizer.Add(MORE_LEFT_PADDING, MORE_TOP_PADDING, wx.GBPosition(0, 0), wx.GBSpan(1, 1))
        # Add spacer on column 3 to reserve space for info badge
        sizer.Add(self._info_length, 0, wx.GBPosition(0, 3), wx.GBSpan(1, 1))
        # Add spacer of width 5 on the 3rd column. This results in a right padding of 5 + hgap
        sizer.Add(MORE_RIGHT_PADDING, 0, wx.GBPosition(0, 4), wx.GBSpan(1, 1))

        # Ensure the input field takes up some percentage of width
        width = self.GetSize()[0]
        right_width = (width - VGAP * 3 - MORE_LEFT_PADDING - MORE_RIGHT_PADDING -
                       self._info_length) * 0.7
        sizer.Add(right_width, 0, wx.GBPosition(0, 2), wx.GBSpan(1, 1))
        sizer.AddGrowableCol(0, 0.3)
        sizer.AddGrowableCol(1, 0.7)

        sizer.Add(self._title, wx.GBPosition(1, 0), wx.GBSpan(1, 5), flag=wx.ALIGN_CENTER)
        self._AppendSpacer(sizer, 0)
        return sizer

    def _AppendControl(self, sizer: wx.Sizer, label_str: str, ctrl: wx.Control):
        """Append a control, its label, and its info badge to the last row of the sizer.

        Returns the automaticaly created label and info badge (wx.StaticText for now).
        """
        label = wx.StaticText(self, label=label_str)
        label.SetFont(self._label_font)
        rows = sizer.GetRows()
        sizer.Add(label, wx.GBPosition(rows, 1), wx.GBSpan(1, 1),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        sizer.Add(ctrl, wx.GBPosition(rows, 2), wx.GBSpan(1, 1),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        sizer.Add(0, self._info_length, wx.GBPosition(rows, 4), wx.GBSpan(1, 1))

        info_badge = wx.StaticBitmap(self, bitmap=self._info_bitmap)
        sizer.Add(info_badge, wx.GBPosition(rows, 3), wx.GBSpan(1, 1),
                  flag=wx.ALIGN_CENTER)
        info_badge.Show(False)
        self.labels[ctrl.GetId()] = label
        self.badges[ctrl.GetId()] = info_badge

    def _AppendSpacer(self, sizer: wx.Sizer, height: int):
        """Append a horizontal spacer with the given height.

        Note:
            The VGAP value still applies, i.e. there is an additional gap between the spacer and
            the next row.
        """
        rows = sizer.GetRows()
        sizer.Add(0, height, wx.GBPosition(rows, 0), wx.GBSpan(1, 5))

    @classmethod
    def _SetBestInsertion(cls, ctrl: wx.TextCtrl, orig_text: str, orig_insertion: int):
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

    def _SetValidationState(self, good: bool, ctrl_id: str, message: str = ""):
        """Set the validation state for a control.

        Args:
            good: Whether the control is currently valid.
            ctrl_id: The ID of the control.
            message: The message displayed, if the control is not valid.
        """
        badge = self.badges[ctrl_id]
        if good:
            badge.Show(False)
        else:
            badge.Show(True)
            badge.SetToolTip(message)
        self.GetSizer().Layout()

    def _CreateColorControl(self, label: str, alpha_label: str,
                            color_callback: ColorCallback, alpha_callback: FloatCallback,
                            sizer: wx.Sizer, alpha_range: Tuple[float, float] = (0, 1)) \
            -> Tuple[wx.ColourPickerCtrl, wx.TextCtrl]:
        """Helper method for creating a color control and adding it to the form.

        Args:
            label: The label text for the color control.
            alpha_label: The label text for the alpha control. Relevant only on Windows.
            color_callback: Callback called when the color changes.
            alpha_callback: Callback called when the alpha changes. Relevant only on Windows.
            sizer: The sizer to which widgets should be added.
            alpha_range: The inclusive range for the alpha value.

        Returns:
            A tuple of the color control and the alpha control.
        """
        ctrl = wx.ColourPickerCtrl(self)
        ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, color_callback)
        self._AppendControl(sizer, label, ctrl)

        alpha_ctrl = None

        if on_msw():
            # Windows does not support picking alpha in color picker. So we add an additional
            # field for that
            alpha_ctrl = wx.TextCtrl(self)
            self._AppendControl(sizer, alpha_label, alpha_ctrl)
            callback = self._MakeFloatCtrlFunction(alpha_ctrl.GetId(), alpha_callback, alpha_range)
            alpha_ctrl.Bind(wx.EVT_TEXT, callback)

        return ctrl, alpha_ctrl

    def _MakeFloatCtrlFunction(self, ctrl_id: str,
                               callback: FloatCallback, range_: Tuple[float, float]):
        """Helper method that creates a validation function for a TextCtrl that only allows floats.

        Args:
            ctrl_id: ID of the TextCtrl, for which this validation function is created.
            callback: Callback for when the float is changed and passes the validation tests.
            range_: Inclusive range for the allowed floats.

        Returns:
            The validation function.
        """
        lo, hi = range_
        assert lo <= hi

        def float_ctrl_fn(evt):
            text = evt.GetString()
            value: float
            try:
                value = float(text)
            except ValueError:
                self._SetValidationState(False, ctrl_id, "Value must be a number")
                return

            if value < lo or value > hi:
                self._SetValidationState(
                    False, ctrl_id, "Value must be in range [{}, {}]".format(lo, hi))
                return

            callback(value)
            self._SetValidationState(True, ctrl_id)

        return float_ctrl_fn

    @classmethod
    def _GetMultiColor(cls, colors: List[wx.Colour]) -> Tuple[wx.Colour, Optional[int]]:
        """Helper method for producing one single color from a list of colors.

        Editing programs that allows selection of multiple entities usually support editing all of
        the selected entities at once. When a property of all the selected entities are the same,
        the displayed value of that property is that single value precisely. However, if they are
        not the same, usually a "null" or default value is shown on the form. Following this scheme,
        this helper returns the common color/alpha if all values are the same, or a default value
        if not.

        Note:
            On Windows the RGB and the alpha are treated as different fields due to the lack of
            alpha field in the color picker screen. Therefore, the RGB and the alpha fields are
            considered different fields as far as uniqueness is considered.
        """
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

    @classmethod
    def _GetMultiFloatText(cls, values: Set[float], precision: int) -> str:
        """Returns the common float value if the set has only one element, otherwise return "?".

        See _GetMultiColor for more detail.
        """
        # TODO should precision be considered as far as uniqueness goes? i.e. should 1.234 be the
        # same as 1.23 when the precision if 2?
        return no_rzeros(next(iter(values)), precision) if len(values) == 1 else '?'

    @classmethod
    def _AlphaToText(cls, alpha: Optional[int], prec: int) -> str:
        """Simple helper for converting an alpha value ~[0, 255] to the range [0, 1].

        Args:
            alpha: The alpha value in range 0-255. If None, "?" will be returned.
            precision: The precision of the float string returned.
        """
        if alpha is None:
            return '?'
        else:
            return no_rzeros(alpha / 255, prec)

    def _ChangePairValue(self, ctrl: wx.TextCtrl, new_val: Vec2, prec: int):
        """Helper for updating the value of a paired number TextCtrl.

        The TextCtrl accepts text in the format "X, Y" where X and Y are floats. The control is
        not updated if the new and old values are identical (considering precision).

        Args:
            ctrl: The TextCtrl widget.
            new_val: The new pair of floats to update the control with.
            prec: The precision of the numbers. The new value is rounded to this precision.
        """
        old_text = ctrl.GetValue()
        old_val = Vec2(parse_num_pair(old_text))

        # round old_val to desired precision. We don't want to refresh value when user is typing,
        # even if their value exceeded our precision
        if old_val != new_val:
            if ctrl.HasFocus():
                orig_insertion = ctrl.GetInsertionPoint()
                wx.CallAfter(
                    lambda: self._SetBestInsertion(ctrl, old_text, orig_insertion))
            ctrl.ChangeValue('{} , {}'.format(
                no_rzeros(new_val.x, prec), no_rzeros(new_val.y, prec)))


class NodeForm(EditPanelForm):
    """Form for editing one or multiple nodes.

    Attributes:
        _nodes: List[Node]  #: current list of nodes in canvas.
        _selected_idx: Set[int]  #: current list of selected indices in canvas.
        _bounding_rect: Optional[Rect]  #: the exact bounding rectangle of the selected nodes
        id_ctrl: wx.TextCtrl
        pos_ctrl: wx.TextCtrl
        size_ctrl: wx.TextCtrl
        fill_ctrl: wx.ColourPickerCtrl
        fill_alpha_ctrl: Optional[wx.TextCtrl]
        border_ctrl: wx.ColourPickerCtrl
        border_alpha_ctrl: Optional[wx.TextCtrl]
        border_width_ctrl: wx.TextCtrl
    """

    def __init__(self, parent, canvas: Canvas, controller: IController):
        super().__init__(parent, canvas, controller)
        self._nodes = list()
        self._selected_idx = set()
        self._bounding_rect = None  # No padding
        sizer = self.InitAndGetSizer()
        self.CreateControls(sizer)
        self.SetSizer(sizer)

    def UpdateNodes(self, nodes: List[Node]):
        """Function called after the list of nodes have been updated."""
        self._nodes = nodes
        if len(self._selected_idx) != 0 and not self._dirty:
            self.UpdateAllFields()

        # clear validation errors
        for id_ in self.badges.keys():
            self._SetValidationState(True, id_)

    def UpdateNodeSelection(self, selected_idx: List[int]):
        """Function called after the list of selected nodes have been updated."""
        self._selected_idx = selected_idx
        if len(self._selected_idx) != 0:
            # clear position value
            self.pos_ctrl.ChangeValue('')
            self.UpdateAllFields()

            title_label = 'Edit Node' if len(self._selected_idx) == 1 else 'Edit Multiple Nodes'
            self._title.SetLabel(title_label)

            id_text = 'identifier' if len(self._selected_idx) == 1 else 'identifiers'
            self.labels[self.id_ctrl.GetId()].SetLabel(id_text)

            size_text = 'size' if len(self._selected_idx) == 1 else 'total span'
            self.labels[self.size_ctrl.GetId()].SetLabel(size_text)


    def UpdateDidDragMoveNodes(self):
        """Function called after the selected nodes were moved by dragging."""
        # HACK only need to update position field here.
        # HACK also note that we don't update anything since we're keeping a reference to the list
        # of nodes.
        self.UpdateAllFields()

    def UpdateDidDragResizeNodes(self):
        """Function called after the selected nodes were resized by dragging."""
        # HACK only need to update size field here
        self.UpdateAllFields()

    def CreateControls(self, sizer):
        # ID form control
        self.id_ctrl = wx.TextCtrl(self)
        self.id_ctrl.Bind(wx.EVT_TEXT, self._OnIdText)
        self._AppendControl(sizer, 'identifier', self.id_ctrl)

        self.pos_ctrl = wx.TextCtrl(self)
        self.pos_ctrl.Bind(wx.EVT_TEXT, self._OnPosText)
        self._AppendControl(sizer, 'position', self.pos_ctrl)

        self.size_ctrl = wx.TextCtrl(self)
        self.size_ctrl.Bind(wx.EVT_TEXT, self._OnSizeText)
        self._AppendControl(sizer, 'size', self.size_ctrl)

        self.fill_ctrl, self.fill_alpha_ctrl = self._CreateColorControl(
            'fill color', 'fill opacity',
            self._OnFillColorChanged, self._FillAlphaCallback,
            sizer)

        self.border_ctrl, self.border_alpha_ctrl = self._CreateColorControl(
            'border color', 'border opacity',
            self._OnBorderColorChanged, self._BorderAlphaCallback,
            sizer)

        self.border_width_ctrl = wx.TextCtrl(self)
        self._AppendControl(sizer, 'border width', self.border_width_ctrl)
        border_callback = self._MakeFloatCtrlFunction(self.border_width_ctrl.GetId(),
                                                      self._BorderWidthCallback, (1, 100))
        self.border_width_ctrl.Bind(wx.EVT_TEXT, border_callback)

    def _OnIdText(self, evt):
        """Callback for the ID control."""
        new_id = evt.GetString()
        assert len(self._selected_idx) == 1
        [nodei] = self._selected_idx
        ctrl_id = self.id_ctrl.GetId()
        if len(new_id) == 0:
            self._SetValidationState(False, ctrl_id, "ID cannot be empty")
            return
        else:
            for node in self._nodes:
                if node.id_ == new_id:
                    self._SetValidationState(False, ctrl_id, "Not saved: Duplicate ID")
                    return
            else:
                # loop terminated fine. There is no duplicate ID
                self._dirty = True
                if not self.controller.try_rename_node(self.net_index, nodei, new_id):
                    # this should not happen!
                    assert False
        self._SetValidationState(True, self.id_ctrl.GetId())

    def _OnPosText(self, evt):
        """Callback for the position control."""
        text = evt.GetString()
        xy = parse_num_pair(text)
        ctrl_id = self.pos_ctrl.GetId()
        if xy is None:
            self._SetValidationState(False, ctrl_id, 'Should be in the form "X, Y"')
            return

        pos = Vec2(xy)
        if pos.x < 0 or pos.y < 0:
            self._SetValidationState(False, ctrl_id, 'Position coordinates should be non-negative')
            return
        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        bounds = Rect(Vec2(), self.canvas.realsize)
        clamped = None
        if len(nodes) == 1:
            [node] = nodes

            clamped = clamp_rect_pos(Rect(pos, node.size), bounds)
            if node.position != clamped or pos != clamped:
                self._dirty = True
                self.controller.try_move_node(self.net_index, node.index,
                                              Vec2(clamped.x, clamped.y))
        else:
            clamped = clamp_rect_pos(Rect(pos, self._bounding_rect.size), bounds)
            if self._bounding_rect.position != pos or pos != clamped:
                offset = clamped - self._bounding_rect.position
                self._dirty = True
                self.controller.try_start_group()
                for node in nodes:
                    self.controller.try_move_node(self.net_index, node.index,
                                                  node.position + offset)
                self.controller.try_end_group()
        self._SetValidationState(True, self.pos_ctrl.GetId())

    def _OnSizeText(self, evt):
        """Callback for the size control."""
        ctrl_id = self.size_ctrl.GetId()
        text = evt.GetString()
        wh = parse_num_pair(text)
        if wh is None:
            self._SetValidationState(False, ctrl_id, 'Should be in the form "width, height"')
            return

        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        min_width = theme['min_node_width']
        min_height = theme['min_node_height']
        size = Vec2(wh)
        if len(nodes) == 1:
            [node] = nodes

            if size.x < min_width or size.y < min_height:
                message = 'Node size needs to be at least ({}, {})'.format(min_width, min_height)
                self._SetValidationState(False, ctrl_id, message)
                return

            clamped = clamp_rect_size(Rect(node.position, size), self.canvas.realsize)
            if node.size != clamped or size != clamped:
                self._dirty = True
                self.controller.try_set_node_size(self.net_index, node.index,
                                                  Vec2(clamped.x, clamped.y))
        else:
            min_nw = min(n.size.x for n in nodes)
            min_nh = min(n.size.y for n in nodes)
            min_ratio = Vec2(min_width / min_nw, min_height / min_nh)
            limit = self._bounding_rect.size.elem_mul(min_ratio)

            if size.x < limit.x or size.y < limit.y:
                message = 'Size of bounding box needs to be at least ({}, {})'.format(
                    no_rzeros(limit.x, 2), no_rzeros(limit.y, 2))
                self._SetValidationState(False, ctrl_id, message)
                return

            clamped = clamp_rect_size(Rect(self._bounding_rect.position, size),
                                      self.canvas.realsize)
            if self._bounding_rect.size != clamped or size != clamped:
                ratio = clamped.elem_div(self._bounding_rect.size)
                self._dirty = True
                self.controller.try_start_group()
                for node in nodes:
                    rel_pos = node.position - self._bounding_rect.position
                    new_pos = self._bounding_rect.position + rel_pos.elem_mul(ratio)
                    self.controller.try_move_node(self.net_index, node.index, new_pos)
                    self.controller.try_set_node_size(self.net_index, node.index,
                                                      node.size.elem_mul(ratio))
                self.controller.try_end_group()
        self._SetValidationState(True, self.size_ctrl.GetId())

    def _OnFillColorChanged(self, evt: wx.Event):
        """Callback for the fill color control."""
        fill = evt.GetColour()
        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            if on_msw():
                self.controller.try_set_node_fill_rgb(self.net_index, node.index, fill)
            else:
                # we can set both the RGB and the alpha at the same time
                self.controller.try_set_node_fill_rgb(self.net_index, node.index, fill)
                self.controller.try_set_node_fill_alpha(self.net_index, node.index, fill.Alpha())
        self.controller.try_end_group()

    def _OnBorderColorChanged(self, evt: wx.Event):
        """Callback for the border color control."""
        border = evt.GetColour()
        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            if on_msw():
                self.controller.try_set_node_border_rgb(self.net_index, node.index, border)
            else:
                # we can set both the RGB and the alpha at the same time
                self.controller.try_set_node_border_rgb(self.net_idnex, node.index, border)
                self.controller.try_set_node_border_alpha(
                    self.net_index, node.index, border.Alpha())
        self.controller.try_end_group()

    def _FillAlphaCallback(self, alpha: float):
        """Callback for when the fill alpha changes."""
        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            self.controller.try_set_node_fill_alpha(self.net_index, node.index, alpha)
        self.controller.try_end_group()

    def _BorderAlphaCallback(self, alpha: float):
        """Callback for when the border alpha changes."""
        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            self.controller.try_set_node_border_alpha(self.net_index, node.index, alpha)
        self.controller.try_end_group()

    def _BorderWidthCallback(self, width: float):
        """Callback for when the border width changes."""
        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        self._dirty = True
        self.controller.try_start_group()
        for node in nodes:
            self.controller.try_set_node_border_width(self.net_index, node.index, width)
        self.controller.try_end_group()

    def UpdateAllFields(self):
        """Update the form field values based on current data."""
        self._dirty = False
        assert len(self._selected_idx) != 0
        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        prec = settings['decimal_precision']
        id_text: str
        pos: Vec2
        size: Vec2
        fill: wx.Colour
        fill_alpha: Optional[int]
        border: wx.Colour
        border_alpha: Optional[int]
        if len(self._selected_idx) == 1:
            [node] = nodes
            self.id_ctrl.Enable(True)
            id_text = node.id_
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
            self.id_ctrl.Enable(False)
            id_text = '; '.join(sorted(list(n.id_ for n in nodes)))

            self._bounding_rect = get_bounding_rect([n.rect for n in nodes])
            pos = self._bounding_rect.position
            size = self._bounding_rect.size

            fill, fill_alpha = self._GetMultiColor(list(n.fill_color for n in nodes))
            border, border_alpha = self._GetMultiColor(list(n.border_color for n in nodes))

        border_width = self._GetMultiFloatText(set(n.border_width for n in nodes), prec)

        self.id_ctrl.ChangeValue(id_text)
        self._ChangePairValue(self.pos_ctrl, pos, prec)
        self._ChangePairValue(self.size_ctrl, size, prec)
        self.fill_ctrl.SetColour(fill)
        self.border_ctrl.SetColour(border)

        # set fill alpha if on windows
        if on_msw():
            self.fill_alpha_ctrl.ChangeValue(self._AlphaToText(fill_alpha, prec))
            self.border_alpha_ctrl.ChangeValue(self._AlphaToText(border_alpha, prec))

        self.border_width_ctrl.ChangeValue(border_width)


class ReactionForm(EditPanelForm):

    def __init__(self, parent, canvas: Canvas, controller: IController):
        super().__init__(parent, canvas, controller)

        self._reactions = list()
        self._selected_idx = set()

        sizer = self.InitAndGetSizer()
        self.CreateControls(sizer)
        self.SetSizer(sizer)

    def CreateControls(self, sizer: wx.Sizer):
        self.id_ctrl = wx.TextCtrl(self)
        self.id_ctrl.Bind(wx.EVT_TEXT, self._OnIdText)
        self._AppendControl(sizer, 'identifier', self.id_ctrl)

        self.ratelaw_ctrl = wx.TextCtrl(self)
        self.ratelaw_ctrl.Bind(wx.EVT_TEXT, self._OnRateLawText)
        self._AppendControl(sizer, 'rate law', self.ratelaw_ctrl)

        self.fill_ctrl, self.fill_alpha_ctrl = self._CreateColorControl(
            'fill color', 'fill opacity',
            self._OnFillColorChanged, self._FillAlphaCallback, sizer)

    def _OnIdText(self, evt):
        """Callback for the ID control."""
        new_id = evt.GetString()
        assert len(self._selected_idx) == 1, 'Reaction ID field should be disabled when ' + \
            'multiple are selected'
        [reai] = self._selected_idx
        ctrl_id = self.id_ctrl.GetId()
        if len(new_id) == 0:
            self._SetValidationState(False, ctrl_id, "ID cannot be empty")
            return
        else:
            for rxn in self._reactions:
                if rxn.id_ == new_id:
                    self._SetValidationState(False, ctrl_id, "Not saved: Duplicate ID")
                    return

            # loop terminated fine. There is no duplicate ID
            self._dirty = True
            self.controller.try_rename_reaction(self.net_index, reai, new_id)
            self._SetValidationState(True, ctrl_id)

    def _OnFillColorChanged(self, evt: wx.Event):
        """Callback for the fill color control."""
        fill = evt.GetColour()
        reactions = [r for r in self._reactions if r.index in self._selected_idx]
        self._dirty = True
        self.controller.try_start_group()
        for rxn in reactions:
            if on_msw():
                self.controller.try_set_reaction_fill_rgb(self.net_index, rxn.index, fill)
            else:
                # we can set both the RGB and the alpha at the same time
                self.controller.try_set_reaction_fill_rgb(self.net_index, rxn.index, fill)
                self.controller.try_set_reaction_fill_alpha(self.net_index, rxn.index, fill.Alpha())
        self.controller.try_end_group()

    def _FillAlphaCallback(self, alpha: float):
        """Callback for when the fill alpha changes."""
        reactions = (r for r in self._reactions if r.index in self._selected_idx)
        self._dirty = True
        self.controller.try_start_group()
        for rxn in reactions:
            self.controller.try_set_reaction_fill_alpha(self.net_index, rxn.index, alpha)
        self.controller.try_end_group()

    def _OnRateLawText(self, evt: wx.Event):
        ratelaw = evt.GetString()
        assert len(self._selected_idx) == 1, 'Reaction rate law field should be disabled when ' + \
            'multiple are selected'
        [reai] = self._selected_idx
        self._dirty = True
        self.controller.try_set_reaction_ratelaw(self.net_index, reai, ratelaw)

    def UpdateReactions(self, reactions: List[Reaction]):
        """Function called after the list of nodes have been updated."""
        self._reactions = reactions
        if len(self._selected_idx) != 0 and not self._dirty:
            self.UpdateAllFields()

        self._dirty = False

        # clear validation errors
        for id_ in self.badges.keys():
            self._SetValidationState(True, id_)

    def UpdateReactionSelection(self, selected_idx: List[int]):
        """Function called after the list of selected nodes have been updated."""
        self._selected_idx = selected_idx
        if len(self._selected_idx) != 0:
            title_label = 'Edit Reaction' if len(self._selected_idx) == 1 \
                else 'Edit Multiple Reactions'
            self._title.SetLabel(title_label)

            id_text = 'identifier' if len(self._selected_idx) == 1 else 'identifiers'
            self.labels[self.id_ctrl.GetId()].SetLabel(id_text)
            self.UpdateAllFields()

    def UpdateAllFields(self):
        assert len(self._selected_idx) != 0
        reactions = [r for r in self._reactions if r.index in self._selected_idx]
        id_text = '; '.join(sorted(list(r.id_ for r in reactions)))
        fill: wx.Colour
        fill_alpha: Optional[int]
        ratelaw_text: str
        prec = settings['decimal_precision']

        if len(self._selected_idx) == 1:
            [reaction] = reactions
            self.id_ctrl.Enable()
            fill = reaction.fill_color
            fill_alpha = reaction.fill_color.Alpha()
            ratelaw_text = reaction.rate_law
            self.ratelaw_ctrl.Enable()
        else:
            self.id_ctrl.Disable()
            fill, fill_alpha = self._GetMultiColor(list(r.fill_color for r in reactions))
            ratelaw_text = 'multiple'
            self.ratelaw_ctrl.Disable()

        self.id_ctrl.ChangeValue(id_text)
        self.fill_ctrl.SetColour(fill)
        self.ratelaw_ctrl.ChangeValue(ratelaw_text)

        if on_msw():
            self.fill_alpha_ctrl.ChangeValue(self._AlphaToText(fill_alpha, prec))
