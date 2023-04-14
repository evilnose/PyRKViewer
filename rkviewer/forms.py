"""All sorts of form widgets, mainly those used in EditPanel.
"""
# from __future__ import annotations
# pylint: disable=maybe-no-member
import wx
from wx.lib.scrolledpanel import ScrolledPanel
from abc import abstractmethod
import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, cast
from .config import get_theme, get_setting, Color
from .events import (DidModifyCompartmentsEvent, DidModifyNodesEvent, DidModifyReactionEvent,
                     DidMoveCompartmentsEvent, DidMoveNodesEvent, DidMoveReactionCenterEvent, DidResizeCompartmentsEvent,
                     DidResizeNodesEvent, post_event)
from .mvc import IController, ModifierTipStyle
from .utils import change_opacity, gchain, no_rzeros, on_msw, resource_path
from .canvas.canvas import Canvas, Node
from .canvas.data import ChoiceItem, Compartment, FONT_FAMILY_CHOICES, FONT_STYLE_CHOICES, FONT_WEIGHT_CHOICES, Reaction, TEXT_ALIGNMENT_CHOICES, LinePrim, PolygonPrim, Primitive, TEXT_POSITION_CHOICES, compute_centroid
from .canvas.geometry import Rect, Vec2, clamp_rect_pos, clamp_rect_size, get_bounding_rect, calc_node_dimensions
from .canvas.utils import get_nodes_by_idx, get_rxns_by_idx
from .canvas.data import CirclePrim, RectanglePrim, CompositeShape
from rkviewer.plugin import api


ColorCallback = Callable[[wx.Colour], None]
FloatCallback = Callable[[float], None]


def GetMultiEnum(entries: List[Any], fallback):
    """Similar to _GetMultiColor, but for enums.

    Need to specify a fallback value in case the entries are different.
    """
    entries_set = set(entries)
    if len(entries_set) == 1:
        return next(iter(entries_set))
    else:
        return fallback


def GetMultiFloatText(values: Set[float], precision: int) -> str:
    """Returns the common float value if the set has only one element, otherwise return "?".

    See _GetMultiColor for more detail.
    """
    return no_rzeros(next(iter(values)), precision) if len(values) == 1 else '?'


def GetMultiInt(values: Set[int]) -> Optional[int]:
    """Returns the common float value if the set has only one element, otherwise return "?".

    See _GetMultiColor for more detail.
    """
    return next(iter(values)) if len(values) == 1 else None


def GetMultiColor(colors: List[wx.Colour]) -> Tuple[wx.Colour, Optional[int]]:
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
        rgb = copy.copy(wx.Colour(127, 127, 127))
        if len(rgbset) == 1:
            rgb.SetRGB(next(iter(rgbset)))

        alphaset = set(c.Alpha() for c in colors)
        alpha = next(iter(alphaset)) if len(alphaset) == 1 else None
        return rgb, alpha
    else:
        rgbaset = set(c.GetRGBA() for c in colors)
        rgba = copy.copy(wx.Colour(127, 127, 127))
        if len(rgbaset) == 1:
            rgba.SetRGBA(next(iter(rgbaset)))

        return rgba, None


def AlphaToText(alpha: Optional[int], prec: int) -> str:
    """Simple helper for converting an alpha value ~[0, 255] to the range [0, 1].

    Args:
        alpha: The alpha value in range 0-255. If None, "?" will be returned.
        precision: The precision of the float string returned.
    """
    if alpha is None:
        return '?'
    else:
        return no_rzeros(alpha / 255, prec)


def _SetBestInsertion(ctrl: wx.TextCtrl, orig_text: str, orig_insertion: int):
    """Set the most natural insertion point for a paired-number text control.

    The format of the text control must be "X,Y" where X, Y are numbers, allowing whitespace.
    This should be called after the text control is autoly changed by View during user's
    editing. Normally if the text changes the caret will be reset to the 0th position, but this
    calculates a smarter position to place the caret to produce a more natural behavior.

    Args:
        ctrl: The text control, whose value is already programmatically changed.
        orig_text: The value of the text control before it was changed.
        orig_insertion: The original caret position from GetInsertionPoint().
    """
    new_text = ctrl.GetValue()
    try:
        mid = orig_text.index(',')
    except ValueError:
        # can't find comma; directly return
        return

    if orig_insertion > mid:
        ctrl.SetInsertionPoint(len(new_text))
    else:
        tokens = new_text.split(',')
        assert len(tokens) == 2

        left = tokens[0].strip()
        lstart = new_text.index(left)
        lend = lstart + len(left)
        ctrl.SetInsertionPoint(lend)


def ChangePairValue(ctrl: wx.TextCtrl, new_val: Vec2, prec: int):
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
                lambda: _SetBestInsertion(ctrl, old_text, orig_insertion))
        ctrl.ChangeValue('{} , {}'.format(
            no_rzeros(new_val.x, prec), no_rzeros(new_val.y, prec)))


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


class FieldGrid(wx.Window):
    def __init__(self, parent, form: 'EditPanelForm'):
        super().__init__(parent)
        self.SetForegroundColour(get_theme('toolbar_fg'))
        self.SetBackgroundColour(get_theme('toolbar_bg'))
        self.form = form
        self.labels = dict()
        self.badges = dict()
        self._label_font = wx.Font(wx.FontInfo().Bold())
        info_image = wx.Image(resource_path('info-2-16.png'), wx.BITMAP_TYPE_PNG)
        self._info_bitmap = wx.Bitmap(info_image)
        self._info_length = 16
        sizer = self.InitAndGetSizer(self.GetParent().GetParent().GetSize()[0])
        self.SetSizer(sizer)

    def InitAndGetSizer(self, edit_panel_width) -> wx.GridSizer:
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
        # Note that we might want to adjust this when scrollbars are displayed, but only in case
        # there is not enough width to display everything
        right_width = (edit_panel_width - VGAP * 3 - MORE_LEFT_PADDING - MORE_RIGHT_PADDING -
                       self._info_length) * .7
        sizer.Add(int(right_width), 0, wx.GBPosition(0, 2), wx.GBSpan(1, 1))
        sizer.AddGrowableCol(0, 3)
        sizer.AddGrowableCol(1, 7)
        return sizer

    def AppendControl(self, label_str: str, ctrl: wx.Control):
        """Append a control, its label, and its info badge to the last row of the sizer.

        Returns the automaticaly created label and info badge (wx.StaticText for now).
        """
        sizer = self.GetSizer()

        label = wx.StaticText(self, label=label_str)
        label.SetFont(self._label_font)
        rows = sizer.GetRows()
        sizer.Add(label, wx.GBPosition(rows, 1), wx.GBSpan(1, 1),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        sizer.Add(ctrl, wx.GBPosition(rows, 2), wx.GBSpan(1, 1),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
        sizer.Add(0, self._info_length, wx.GBPosition(rows, 4), wx.GBSpan(1, 1))

        info_badge = wx.StaticBitmap(self, bitmap=self._info_bitmap)
        info_badge.Show(False)
        sizer.Add(info_badge, wx.GBPosition(rows, 3), wx.GBSpan(1, 1), flag=wx.ALIGN_CENTER)
        self.labels[ctrl.GetId()] = label
        self.badges[ctrl.GetId()] = info_badge

    def AppendSpacer(self, height: int, sizer=None):
        """Append a horizontal spacer with the given height.

        Note:
            The VGAP value still applies, i.e. there is an additional gap between the spacer and
            the next row.
        """
        if sizer is None:
            sizer = self.GetSizer()
        rows = sizer.GetRows()
        sizer.Add(0, height, wx.GBPosition(rows, 0), wx.GBSpan(1, 5))

    def AppendLine(self):
        """Append a horizontal spacer with the given height.

        Note:
            The VGAP value still applies, i.e. there is an additional gap between the spacer and
            the next row.
        """
        sizer = self.GetSizer()
        rows = sizer.GetRows()
        line = wx.StaticLine(self)
        sizer.Add(line, wx.GBPosition(rows, 0), wx.GBSpan(1, 5))

    def AppendSubtitle(self, text: str, add_spacers: bool = True) -> wx.StaticText:
        sizer = self.GetSizer()
        if add_spacers:
            self.AppendSpacer(3)
        sizer.Add(0, 0, wx.GBPosition(sizer.GetRows(), 0))
        statictext = wx.StaticText(self, label=text)
        font = wx.Font(wx.FontInfo(9))
        statictext.SetFont(font)
        sizer.Add(statictext, wx.GBPosition(sizer.GetRows(), 0),
                  wx.GBSpan(1, 5), flag=wx.ALIGN_CENTER)
        if add_spacers:
            self.AppendSpacer(0)
        return statictext

    def SetValidationState(self, good: bool, ctrl_id: str, message: str = ""):
        """Set the validation state for a control.

        Args:
            good: Whether the control is currently valid.
            ctrl_id: The ID of the control.
            message: The message displayed, if the control is not valid.
        """
        # self.Freeze()
        badge = self.badges[ctrl_id]
        if good:
            badge.Show(False)
        else:
            badge.Show(True)
            badge.SetToolTip(message)
        self.Layout()
        # self.Thaw()

    def CreateTextCtrl(self, **kwargs):
        """Create a text control that confirms to the theme."""
        if get_theme('text_field_border'):
            style = 0
        else:
            style = wx.BORDER_NONE
        ctrl = wx.TextCtrl(self, style=style, **kwargs)
        ctrl.SetBackgroundColour(get_theme('text_field_bg'))
        ctrl.SetForegroundColour(get_theme('text_field_fg'))
        return ctrl

    def CreateSpinCtrl(self, **kwargs):
        """Create a text control that confirms to the theme."""
        if get_theme('text_field_border'):
            style = 0
        else:
            style = wx.BORDER_NONE
        ctrl = wx.SpinCtrl(self, style=style, **kwargs)
        ctrl.SetBackgroundColour(get_theme('text_field_bg'))
        ctrl.SetForegroundColour(get_theme('text_field_fg'))
        return ctrl

    def CreateColorControl(self, label: str, alpha_label: str,
                           color_callback: ColorCallback, alpha_callback: FloatCallback,
                           alpha_range: Tuple[float, float] = (0, 1),
                           placeholder: wx.Colour = wx.Colour(127, 127, 127), placeholder_alpha=None) \
            -> Tuple[wx.ColourPickerCtrl, Optional[wx.TextCtrl]]:
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
        # Update placeholder to include alpha
        if placeholder_alpha:
            placeholder = wx.Colour(placeholder.Red(), placeholder.Green(), placeholder.Blue(),
                                    placeholder_alpha)

        ctrl = wx.ColourPickerCtrl(self)
        ctrl.SetColour(placeholder)
        ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, lambda e: color_callback(e.GetColour()))
        self.AppendControl(label, ctrl)

        alpha_ctrl = None

        if on_msw():
            # Windows does not support picking alpha in color picker. So we add an additional
            # field for that
            alpha_text = AlphaToText(placeholder_alpha, 2)
            alpha_ctrl = self.CreateTextCtrl(value=alpha_text)
            self.AppendControl(alpha_label, alpha_ctrl)
            callback = self.MakeFloatCtrlFunction(alpha_ctrl.GetId(), alpha_callback, alpha_range)
            alpha_ctrl.Bind(wx.EVT_TEXT, callback)

        return ctrl, alpha_ctrl

    def MakeFloatCtrlFunction(self, ctrl_id: str, callback: FloatCallback,
                              range_: Tuple[Optional[float], Optional[float]],
                              left_incl: bool = True, right_incl: bool = True):
        """Helper method that creates a validation function for a TextCtrl that only allows floats.

        Args:
            ctrl_id: ID of the TextCtrl, for which this validation function is created.
            callback: Callback for when the float is changed and passes the validation tests.
            range_: Inclusive range for the allowed floats.

        Returns:
            The validation function.
        """
        lo, hi = range_

        def float_ctrl_fn(evt):
            text = evt.GetString()
            value: float
            try:
                value = float(text)
            except ValueError:
                self.SetValidationState(False, ctrl_id, "Value must be a number")
                return

            good = True
            if left_incl:
                if lo is not None and value < lo:
                    good = False
            else:
                if lo is not None and value <= lo:
                    good = False

            if right_incl:
                if hi is not None and value > hi:
                    good = False
            else:
                if hi is not None and value >= hi:
                    good = False

            if not good:
                err_msg: str
                if lo is not None and hi is not None:
                    left = '[' if left_incl else '('
                    right = ']' if right_incl else ')'
                    err_msg = "Value must be in range {}{}, {}{}".format(left, lo, hi, right)
                else:
                    if lo is not None:
                        incl_text = 'or equal to ' if left_incl else ''
                        err_msg = "Value must greater than {}{}".format(incl_text, lo)
                    else:
                        incl_text = 'or equal to' if right_incl else ''
                        err_msg = "Value must less than {} {}".format(incl_text, hi)
                self.SetValidationState(False, ctrl_id, err_msg)
                return

            callback(value)
            self.SetValidationState(True, ctrl_id)

        return float_ctrl_fn

class PrimitiveGrid(FieldGrid):
    form: 'NodeForm'
    def __init__(self, parent, form: 'NodeForm'):
        super().__init__(parent, form)
        self.update_callbacks = list()
        # need another GetParent() in addition to FieldGrid's call
        sizer = self.InitAndGetSizer(self.GetParent().GetParent().GetParent().GetSize()[0])
        self.SetSizer(sizer)

    def UpdateValues(self, nodes):
        '''Update the values in the primitive fields.

        Requires:
            The FieldGrid contains the up-to-date field widgets for the given composite shape.
        '''
        for callback in self.update_callbacks:
            callback(nodes)


    def ColorPrimitiveControl(self, label: str, alpha_label: str, prop_name: str,
                              prim_index: int):
        '''Create a control for a color property.

        If prim_index is -1, then update the text primitive instead.
        '''

        def color_callback(value: wx.Colour):
            node_indices = self.form.selected_idx
            nodes = self.form.selected_nodes
            prims = self._GetPrimitives(nodes, prim_index)
            old_colors = [getattr(p, prop_name).to_wxcolour() for p in prims]

            self.form.self_changes = True
            with self.form.controller.group_action():
                for i, nodei in enumerate(node_indices):
                    # only update the RGB, not alpha
                    old_color = old_colors[i]
                    new_color = Color(value.Red(), value.Green(), value.Blue(), old_color.Alpha())
                    self.form.controller.set_node_primitive_property(self.form.net_index, nodei, prim_index,
                                                                    prop_name, new_color)

        def alpha_callback(value: float):
            node_indices = self.form.selected_idx
            prims = self._GetPrimitives(self.form.selected_nodes, prim_index)
            old_colors = [getattr(p, prop_name).to_wxcolour() for p in prims]

            self.form.self_changes = True
            with self.form.controller.group_action():
                for i, nodei in enumerate(node_indices):
                    old_color = old_colors[i]
                    new_color = Color(old_color.Red(), old_color.Green(),
                                    old_color.Blue(), int(255 * value))
                    self.form.controller.set_node_primitive_property(self.form.net_index, nodei, prim_index,
                                                                    prop_name, new_color)

        ctrl, alpha_ctrl = self.CreateColorControl(label, alpha_label, color_callback, alpha_callback)

        # callback for when the canvs is upated by user input
        def update_cb(nodes: List[Node]):
            prims = self._GetPrimitives(nodes, prim_index)
            old_colors = [getattr(p, prop_name).to_wxcolour() for p in prims]
            color_union, alpha_union = GetMultiColor(old_colors)
            self.form.self_changes = True
            ctrl.SetColour(color_union)
            if alpha_ctrl:
                alpha_ctrl.ChangeValue(AlphaToText(alpha_union, 2))

        self.update_callbacks.append(update_cb)


    def FloatPrimitiveControl(self, label: str, prop_name: str, prim_index: int):
        '''Create a control for a floating point property.

        If prim_index is -1, then update the text primitive instead.
        '''

        def callback(value: float):
            node_indices = self.form.selected_idx

            self.form.self_changes = True
            with self.form.controller.group_action():
                for nodei in node_indices:
                    # only update the RGB, not alpha
                    self.form.controller.set_node_primitive_property(self.form.net_index, nodei, prim_index,
                                                                    prop_name, value)

        # TODO update values not here
        text_ctrl = self.CreateTextCtrl()
        outer_callback = self.MakeFloatCtrlFunction(text_ctrl.GetId(),
                                                    callback, (0, None), left_incl=False)
        text_ctrl.Bind(wx.EVT_TEXT, outer_callback)
        self.AppendControl(label, text_ctrl)

        def update_cb(nodes: List[Node]):
            prims = self._GetPrimitives(nodes, prim_index)
            old_values = [getattr(p, prop_name) for p in prims]
            update_value = GetMultiFloatText(set(old_values), 2)
            text_ctrl.ChangeValue(update_value)

        self.update_callbacks.append(update_cb)

    def IntPrimitiveControl(self, label: str, prop_name: str,
                            prim_index: int, min_=0, max_=100):
        '''Create a control for a floating point property.

        If prim_index is -1, then update the text primitive instead.
        '''
        def spin_callback(value: int):
            node_indices = self.form.selected_idx
            self.form.self_changes = True
            with self.form.controller.group_action():
                for nodei in node_indices:
                    # only update the RGB, not alpha
                    self.form.controller.set_node_primitive_property(self.form.net_index, nodei, prim_index,
                                                                    prop_name, value)

        def text_callback(value: str):
            if value:
                spin_callback(int(value))


        int_ctrl = self.CreateSpinCtrl(min=min_, max=max_)
        int_ctrl.Bind(wx.EVT_SPINCTRL, lambda e: spin_callback(e.GetInt()))
        int_ctrl.Bind(wx.EVT_TEXT, lambda e: text_callback(e.GetString()))

        self.AppendControl(label, int_ctrl)

        def update_cb(nodes: List[Node]):
            prims = self._GetPrimitives(self.form.selected_nodes, prim_index)
            old_values = [getattr(p, prop_name) for p in prims]
            updated_value = GetMultiInt(set(old_values)) or 0
            int_ctrl.SetValue(updated_value)

        self.update_callbacks.append(update_cb)

    def ChoicePrimitiveControl(self, label: str, prop_name: str, prim_index: int,
                               choice_items: List[ChoiceItem]):
        # TODO set original value
        def callback(e):
            node_indices = self.form.selected_idx
            index = e.GetInt()
            value = choice_items[index].value
            self.form.self_changes = True
            with self.form.controller.group_action():
                for nodei in node_indices:
                    self.form.controller.set_node_primitive_property(self.form.net_index, nodei, prim_index,
                                                                    prop_name, value)
        texts = [item.text for item in choice_items]
        choice_ctrl = wx.Choice(self, choices=texts)

        choice_ctrl.Bind(wx.EVT_CHOICE, callback)
        self.AppendControl(label, choice_ctrl)

        def update_cb(nodes):
            prims = self._GetPrimitives(nodes, prim_index)
            old_values = set(getattr(prim, prop_name) for prim in prims)

            # Set commonly selected item
            if len(old_values) == 1:
                # Find choice item with given value
                sel_ind = None
                old_value = next(iter(old_values))
                for index, item in enumerate(choice_items):
                    if item.value == old_value:
                        sel_ind = index
                        break
                else:
                    assert False, "This should never happen"
                choice_ctrl.SetSelection(sel_ind)
            else:
                # Different values; set dropdown to none
                choice_ctrl.SetSelection(wx.NOT_FOUND)
        self.update_callbacks.append(update_cb)

    def _GetPrimitives(self, nodes, prim_index):
        if prim_index == -1:
            return [n.composite_shape.text_item[0] for n in nodes]
        return [n.composite_shape.items[prim_index][0] for n in nodes]


class PrimitiveSection(wx.Window):
    subsections: List[PrimitiveGrid]

    def __init__(self, node_form: 'NodeForm', com_shape: CompositeShape):
        super().__init__(node_form)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizerflags = wx.SizerFlags().Expand()
        self.update_callbacks = list()
        self.form = node_form

        self.subsections = list()
        # self._primitives_heading = self.main_section.AppendSubtitle('Shape properties')
        # self.main_section.AppendSpacer(0)
        # node_indices = [n.index for n in nodes]
        for prim_index in range(len(com_shape.items)):
            # primitives = [cs.items[prim_index][0] for cs in com_shapes]
            one_prim = com_shape.items[prim_index][0]
            subtitle_text = '{name} ({idx})'.format(idx=prim_index + 1, name=one_prim.name)
            subsection = PrimitiveGrid(self, node_form)
            self.subsections.append(subsection)
            subsection.AppendSubtitle(subtitle_text)
            if isinstance(one_prim, RectanglePrim):
                subsection.ColorPrimitiveControl('fill color', 'fill opacity', 'fill_color',
                                                 prim_index)
                subsection.ColorPrimitiveControl('border color', 'border opacity', 'border_color',
                                                 prim_index)
                subsection.FloatPrimitiveControl('border width', 'border_width',
                                                 prim_index)
                subsection.FloatPrimitiveControl('corner radius', 'corner_radius',
                                                 prim_index)
            elif isinstance(one_prim, LinePrim):
                subsection.ColorPrimitiveControl('line color', 'line opacity', 'border_color',
                                                 prim_index)
                subsection.FloatPrimitiveControl('line width', 'border_width',
                                                 prim_index)
            elif isinstance(one_prim, CirclePrim) or isinstance(one_prim, PolygonPrim):
                subsection.ColorPrimitiveControl('fill color', 'fill opacity', 'fill_color',
                                                 prim_index)
                subsection.ColorPrimitiveControl('border color', 'border opacity', 'border_color',
                                                 prim_index)
                subsection.FloatPrimitiveControl('border width', 'border_width',
                                                 prim_index)

        subtitle_text = 'Text'
        subsection = PrimitiveGrid(self, node_form)
        self.subsections.append(subsection)
        subsection.AppendSubtitle(subtitle_text)
        # Create text primitive
        subsection.IntPrimitiveControl('font size', 'font_size', -1, min_=1, max_=100)
        subsection.ColorPrimitiveControl('font color', 'font opacity', 'font_color',
                                         -1)
        subsection.ColorPrimitiveControl('highlight color', 'highlight opacity', 'bg_color',
                                         -1)
        subsection.ChoicePrimitiveControl('font family', 'font_family', -1, FONT_FAMILY_CHOICES)
        subsection.ChoicePrimitiveControl('font style', 'font_style', -1, FONT_STYLE_CHOICES)
        subsection.ChoicePrimitiveControl('font weight', 'font_weight', -1, FONT_WEIGHT_CHOICES)
        subsection.ChoicePrimitiveControl('alignment', 'alignment', -1, TEXT_ALIGNMENT_CHOICES)
        subsection.ChoicePrimitiveControl('text position', 'position', -1, TEXT_POSITION_CHOICES)

        for subsection in self.subsections:
            sizer.Add(subsection, sizerflags)
        self.SetSizer(sizer)

    def UpdatePrimitiveValues(self):
        selected_nodes = self.form.selected_nodes
        for subsection in self.subsections:
            subsection.UpdateValues(selected_nodes)


class EditPanelForm(ScrolledPanel):
    """Base class for a form to be displayed on the edit panel.

    Attributes:
        ColorCallback: Callback type for when a color input is changed.
        FloatCallback: Callback type for when a float input is changed.
        canvas: The associated canvas.
        controller: The associated controller.
        net_index: The current network index. For now it is 0 since there is only one tab.
    """

    canvas: Canvas
    controller: IController
    net_index: int
    labels: Dict[str, wx.Window]
    badges: Dict[str, wx.Window]
    sections: List[FieldGrid]
    _label_font: wx.Font  #: font for the form input label.
    _info_bitmap: wx.Bitmap  # :  bitmap for the info badge (icon), for when an input is invalid.
    _info_length: int  #: length of the square reserved for _info_bitmap
    _title: wx.StaticText  #: title of the form
    self_changes: bool  #: flag for if edits were made but the controller hasn't updated the view yet

    def __init__(self, parent, canvas: Canvas, controller: IController):
        #super().__init__(parent, style=wx.VSCROLL)
        super().__init__(parent, style = wx.ALWAYS_SHOW_SB)
        self.SetForegroundColour(get_theme('toolbar_fg'))
        self.SetBackgroundColour(get_theme('toolbar_bg'))
        self.canvas = canvas
        self.controller = controller
        self.net_index = 0
        self._title = wx.StaticText(self, style=wx.ALIGN_CENTER)  # only displayed when node(s) are selected
        title_font = wx.Font(wx.FontInfo(10))
        self._title.SetFont(title_font)
        self.self_changes = False
        self._selected_idx = set()

    # OVerride the ScrolledPanel behavior of jumping to the child that has the focus
    def OnChildFocus(self, evt):
        pass

    @property
    def selected_idx(self):
        return self._selected_idx

    def CreateChildren(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizerflags = wx.SizerFlags().Expand()

        sizer.Add(self._title, sizerflags.Border(wx.BOTTOM, 5))
        sizer.Add(wx.StaticLine(self), sizerflags)

        for section in self.sections:
            sizer.Add(section, sizerflags)
        self.CreateControls()

        self.SetSizer(sizer)
        self.SetupScrolling()

    @abstractmethod
    def UpdateAllFields(self):
        pass

    @abstractmethod
    def CreateControls(self):
        pass

    def ExternalUpdate(self):
        if len(self._selected_idx) != 0 and not self.self_changes:
            self.UpdateAllFields()

        # clear validation errors
        # TODO
        for section in self.sections:
            for id in section.badges.keys():
                section.SetValidationState(True, id)
        self.self_changes = False


class NodeForm(EditPanelForm):
    """Form for editing one or multiple nodes.

    Attributes:
    """
    #_compartments: List[Compartment]
    contiguous: bool
    id_ctrl: wx.TextCtrl
    conc_ctrl: wx.TextCtrl
    pos_ctrl: wx.TextCtrl
    size_ctrl: wx.TextCtrl
    nodeStatusDropDown: wx.Choice
    compositeShapesDropDown: wx.Choice
    lockNodeCheckBox: wx.CheckBox

    _nodes: List[Node]  #: current list of nodes in canvas.
    _selected_idx: Set[int]  #: current list of selected indices in canvas.
    _bounding_rect: Optional[Rect]  #: the exact bounding rectangle of the selected nodes

    def __init__(self, parent, canvas: Canvas, controller: IController):
        super().__init__(parent, canvas, controller)
        self.all_nodes = list()
        #self.compartments = list()
        self.main_section = FieldGrid(self, self)
        self.sections = [self.main_section]
        self._bounding_rect = None  # No padding
        # boolean to indicate whether only nodes are selected, and only nodes from the same
        # compartment are selected
        self.contiguous = True
        self.last_prim_section = None
        self.prim_section_cache = dict()

        self.CreateChildren()

    @property
    def selected_nodes(self):
        return [n for n in self.all_nodes if n.index in self.selected_idx]

    def UpdateNodes(self, nodes: List[Node]):
        """Function called after the list of nodes have been updated."""
        self.all_nodes = nodes
        self._UpdateBoundingRect()
        self.ExternalUpdate()

    def NodesMovedOrResized(self, evt):
        """Called when nodes are moved or resized by dragging"""
        if not evt.dragged:
            return
        # Possibly no nodes are selected because they are moved along with the compartments
        if len(self._selected_idx) != 0:
            self._UpdateBoundingRect()
            prec = 2
            ChangePairValue(self.pos_ctrl, self._bounding_rect.position, prec)
            ChangePairValue(self.size_ctrl, self._bounding_rect.size, prec)

    def _UpdateBoundingRect(self):
        """Update bounding rectangle; mixed indicates whether both nodes and comps are selected.
        """
        rects = [n.rect for n in self.all_nodes if n.index in self._selected_idx]
        # It could be that compartments have been updated but selected indices have not.
        # In that case rects can be empty
        if len(rects) != 0:
            self._bounding_rect = get_bounding_rect(rects)

    
    # def UpdateCompartments(self, comps: List[Compartment]):
    #     self.compartments = comps
    #     self._UpdateBoundingRect()
    #     self.ExternalUpdate()

    def UpdateSelection(self, selected_idx: Set[int], comps_selected: bool):
        """Function called after the list of selected nodes have been updated."""
        self._selected_idx = selected_idx
        if len(selected_idx) != 0:
            self._UpdateBoundingRect()

        if comps_selected:
            self.contiguous = False
        else:
            nodes = self.selected_nodes
            self.contiguous = len(set(n.comp_idx for n in nodes)) <= 1

        if len(self._selected_idx) != 0:
            # clear position value
            self.pos_ctrl.ChangeValue('')
            self.UpdateAllFields()

            title_label = 'Edit Node' if len(self._selected_idx) == 1 else 'Edit Multiple Nodes'
            self._title.SetLabel(title_label)

            id_text = 'identifier' if len(self._selected_idx) == 1 else 'identifiers'
            self.main_section.labels[self.id_ctrl.GetId()].SetLabel(id_text)

            comp_text = 'compartment' if len(self._selected_idx) == 1 else 'compartment'
            self.main_section.labels[self.comp_ctrl.GetId()].SetLabel(comp_text)

            name_text = 'name' if len(self._selected_idx) == 1 else 'name'
            self.main_section.labels[self.name_ctrl.GetId()].SetLabel(name_text)

            SBO_text = 'SBO' if len(self._selected_idx) == 1 else 'SBO'
            self.main_section.labels[self.SBO_ctrl.GetId()].SetLabel(SBO_text)

            concentration_text = 'concentration' if len(self._selected_idx) == 1 else 'concentrations'
            self.main_section.labels[self.conc_ctrl.GetId()].SetLabel(concentration_text)

            size_text = 'size' if len(self._selected_idx) == 1 else 'size'
            self.main_section.labels[self.size_ctrl.GetId()].SetLabel(size_text)

        self.ExternalUpdate()

    def CreateControls(self):
        self.id_ctrl = self.main_section.CreateTextCtrl()
        self.id_ctrl.Bind(wx.EVT_TEXT, self._OnIdText)
        self.main_section.AppendControl('identifier', self.id_ctrl)

        self.comp_ctrl = self.main_section.CreateTextCtrl()
        #self.comp_ctrl.Bind(wx.EVT_TEXT, self._OnCompText)
        self.main_section.AppendControl('compartment', self.comp_ctrl)

        self.name_ctrl = self.main_section.CreateTextCtrl()
        self.name_ctrl.Bind(wx.EVT_TEXT, self._OnNameText)
        self.main_section.AppendControl('name', self.name_ctrl)

        self.SBO_ctrl = self.main_section.CreateTextCtrl()
        self.SBO_ctrl.Bind(wx.EVT_TEXT, self._OnSBOText)
        self.main_section.AppendControl('SBO', self.SBO_ctrl)
        
        self.conc_ctrl = self.main_section.CreateTextCtrl()
        self.conc_ctrl.Bind(wx.EVT_TEXT, self._OnConcText)
        self.main_section.AppendControl('concentration', self.conc_ctrl)

        self.pos_ctrl = self.main_section.CreateTextCtrl()
        self.pos_ctrl.Bind(wx.EVT_TEXT, self._OnPosText)
        self.main_section.AppendControl('position', self.pos_ctrl)

        self.size_ctrl = self.main_section.CreateTextCtrl()
        #self.size_ctrl.Bind(wx.EVT_TEXT, self._OnSizeText)
        self.size_ctrl.Bind(wx.EVT_TEXT, self._OnNodeSizeText)
        self.main_section.AppendControl('size', self.size_ctrl)

        self.nodeStates = ['Floating Node', 'Boundary Node']
        self.nodeStatusDropDown = wx.Choice(self.main_section, choices=self.nodeStates)
        self.main_section.AppendControl('node status', self.nodeStatusDropDown)
        self.nodeStatusDropDown.Bind(wx.EVT_CHOICE, self.OnNodeStatusChoice)

        self.lockNodeCheckBox = wx.CheckBox(self.main_section, label='')
        self.main_section.AppendControl('lock node', self.lockNodeCheckBox)
        self.lockNodeCheckBox.Bind(wx.EVT_CHECKBOX, self.OnNodeLockCheckBox)

        self.compShapeNames = [
            x.name for x in self.controller.get_composite_shape_list(self.net_index)]
        self.compositeShapesDropDown = wx.Choice(self.main_section, choices=self.compShapeNames)
        self.main_section.AppendControl('shape', self.compositeShapesDropDown)
        self.compositeShapesDropDown.Bind(wx.EVT_CHOICE, self.OnCompositeShapes)

    def _OnIdText(self, evt):
        """Callback for the ID control."""
        new_id = evt.GetString()
        assert len(self._selected_idx) == 1
        [nodei] = self._selected_idx
        ctrl_id = self.id_ctrl.GetId()
        if len(new_id) == 0:
            self.main_section.SetValidationState(False, ctrl_id, "ID cannot be empty")
            return
        else:
            for node in self.all_nodes:
                if node.id == new_id:
                    self.main_section.SetValidationState(False, ctrl_id, "Not saved: Duplicate ID")
                    return
            else:
                # loop terminated fine. There is no duplicate ID
                self.self_changes = True
                with self.controller.group_action():
                    self.controller.rename_node(self.net_index, nodei, new_id)
                    post_event(DidModifyNodesEvent([nodei]))
        self.main_section.SetValidationState(True, self.id_ctrl.GetId())

    def _OnNameText(self, evt):
        """Callback for the name control."""
        new_name = evt.GetString()
        assert len(self._selected_idx) == 1
        [nodei] = self._selected_idx
        ctrl_name = self.name_ctrl.GetId()

        if len(new_name) != 0:
            self.self_changes = True
            with self.controller.group_action():
                self.controller.set_node_name(self.net_index, nodei, new_name)
                post_event(DidModifyNodesEvent([nodei]))
        self.main_section.SetValidationState(True, self.id_ctrl.GetId())

    def _OnSBOText(self, evt):
        """Callback for the SBO control."""
        new_SBO = evt.GetString()
        assert len(self._selected_idx) == 1
        [nodei] = self._selected_idx
        ctrl_SBO = self.SBO_ctrl.GetId()

        if len(new_SBO) != 0:
            if new_SBO[:8] == "SBO:0000" and new_SBO[8:11].isdigit():
                self.self_changes = True
                with self.controller.group_action():
                    self.controller.set_node_SBO(self.net_index, nodei, new_SBO)
                    post_event(DidModifyNodesEvent([nodei]))
            else:
                self.main_section.SetValidationState(False, ctrl_SBO, "Not saved: Invalid SBO Term ID (Example: SBO:0000247)")
                return
         
        self.main_section.SetValidationState(True, self.SBO_ctrl.GetId())

    # def _OnCompText(self, evt):
    #     """Callback for the compartment control."""
    #     #needs to double check especially comp_idx vs comp_id
    #     new_comp = evt.GetString()
    #     assert len(self._selected_idx) == 1
    #     [nodei] = self._selected_idx
    #     ctrl_comp = self.comp_ctrl.GetId()

    #     flag_comp_exist = 0
    #     allCompartments = api.get_compartments(self.net_index)
    #     for comp in allCompartments:
    #         if comp.index == new_comp:
    #             flag_comp_exist = 1
    #     if flag_comp_exist == 0:
    #         self.main_section.SetValidationState(False, ctrl_comp, "Not saved: Compartment ID does not exist.")
    #         return

    #     self.self_changes = True
    #     with self.controller.group_action():
    #         self.controller.set_compartment_of_node(self.net_index, nodei, new_comp)
    #         post_event(DidModifyNodesEvent([nodei]))
    #     self.main_section.SetValidationState(True, self.comp_ctrl.GetId())

    def _OnConcText(self, evt):
        """ Callback for the concentration control. """
        new_conc = evt.GetString()
        assert len(self._selected_idx) == 1 # TODO should work for multiple nodes
        [nodei] = self._selected_idx
        ctrl_conc = self.conc_ctrl.GetId()
        if len(new_conc) == 0:
            self.main_section.SetValidationState(False, ctrl_conc, "Concentration cannot be empty")
            return
        try:
            new_conc_float = float(new_conc)
        except ValueError:
            self.main_section.SetValidationState(False, ctrl_conc, "Concentration must be a numerical value") # TODO good message?
            return
        if new_conc_float < 0.0:
            self.main_section.SetValidationState(False, ctrl_conc, "Concentration cannot be negative")
            return
        self.self_changes = True
        with self.controller.group_action():
            self.controller.set_node_concentration(self.net_index, nodei, new_conc_float)
            post_event(DidModifyNodesEvent([nodei]))
            # TODO should have an event for this
        self.main_section.SetValidationState(True, self.conc_ctrl.GetId())

    def _OnPosText(self, evt):
        """Callback for the position control."""
        assert self.contiguous
        text = evt.GetString()
        xy = parse_num_pair(text)
        ctrl_id = self.pos_ctrl.GetId()
        if xy is None:
            self.main_section.SetValidationState(False, ctrl_id, 'Should be in the form "X, Y"')
            return

        pos = Vec2(xy)
        if pos.x < 0 or pos.y < 0:
            self.main_section.SetValidationState(
                False, ctrl_id, 'Position coordinates should be non-negative')
            return
        nodes = get_nodes_by_idx(self.all_nodes, self._selected_idx)
        # limit position to within the compartment
        compi = nodes[0].comp_idx
        if compi == -1:
            bounds = Rect(Vec2(), self.canvas.realsize)
        else:
            comp = self.canvas.comp_idx_map[compi]
            bounds = Rect(comp.position, comp.size)
        clamped = None
        index_list = list(self._selected_idx)
        if len(nodes) == 1:
            [node] = nodes
            clamped = clamp_rect_pos(Rect(pos, node.size), bounds)
            if node.position != clamped or pos != clamped:
                self.self_changes = True
                node.position = clamped
                with self.controller.group_action():
                    post_event(DidMoveNodesEvent(index_list, clamped - node.position, dragged=False))
                    self.controller.move_node(self.net_index, node.index, node.position)
        else:
            clamped = clamp_rect_pos(Rect(pos, self._bounding_rect.size), bounds)
            if self._bounding_rect.position != pos or pos != clamped:
                offset = clamped - self._bounding_rect.position
                self.self_changes = True
                with self.controller.group_action():
                    for node in nodes:
                        node.position += offset
                    post_event(DidMoveNodesEvent(index_list, offset, dragged=False))
                    for node in nodes:
                        self.controller.move_node(self.net_index, node.index, node.position)
        self.main_section.SetValidationState(True, self.pos_ctrl.GetId())

    def _OnSizeText(self, evt):
        """Callback for the size control."""
        assert self.contiguous
        ctrl_id = self.size_ctrl.GetId()
        text = evt.GetString()
        wh = parse_num_pair(text)
        if wh is None:
            self.main_section.SetValidationState(
                False, ctrl_id, 'Should be in the form "width, height"')
            return

        nodes = get_nodes_by_idx(self.all_nodes, self._selected_idx)
        min_width = get_setting('min_node_width')
        min_height = get_setting('min_node_height')
        size = Vec2(wh)
        # limit size to be smaller than the compartment
        compi = nodes[0].comp_idx
        bounds: Rect
        if compi == -1:
            bounds = Rect(Vec2(), self.canvas.realsize)
        else:
            comp = self.canvas.comp_idx_map[compi]
            bounds = comp.rect

        min_nw = min(n.size.x for n in nodes)
        min_nh = min(n.size.y for n in nodes)
        min_ratio = Vec2(min_width / min_nw, min_height / min_nh)
        min_size = self._bounding_rect.size.elem_mul(min_ratio)

        if size.x < min_size.x or size.y < min_size.y:
            message = 'The size of {} needs to be at least ({}, {})'.format(
                'bounding box' if len(nodes) > 1 else 'node',
                no_rzeros(min_size.x, 2), no_rzeros(min_size.y, 2))
            self.main_section.SetValidationState(False, ctrl_id, message)
            return

        # if size.x > max_size.x or size.y > max_size.y:
        #     message = 'The size of bounding box cannot exceed ({}, {})'.format(
        #         no_rzeros(max_size.x, 2), no_rzeros(max_size.y, 2))
        #     self.main_section.SetValidationState(False, ctrl_id, message)
        #     return

        # NOTE clamp max size automatically rather than show error
        clamped = size.reduce2(min, bounds.size)
        if self._bounding_rect.size != clamped or size != clamped:
            ratio = clamped.elem_div(self._bounding_rect.size)
            self.self_changes = True
            with self.controller.group_action():
                offsets = list()
                for node in nodes:
                    rel_pos = node.position - self._bounding_rect.position
                    new_pos = self._bounding_rect.position + rel_pos.elem_mul(ratio)
                    offsets.append(new_pos - node.position)
                    node.position = new_pos
                    node.size = node.size.elem_mul(ratio)
                    # clamp so that nodes are always within compartment/bounds
                    node.position = clamp_rect_pos(node.rect, bounds)

                idx_list = list(self._selected_idx)
                post_event(DidMoveNodesEvent(idx_list, offsets, dragged=False))
                post_event(DidResizeNodesEvent(idx_list, ratio=ratio, dragged=False))
                for node in nodes:
                    self.controller.move_node(self.net_index, node.index, node.position)
                    self.controller.set_node_size(self.net_index, node.index, node.size)
        self.main_section.SetValidationState(True, self.size_ctrl.GetId())

    def _OnNodeSizeText(self, evt):
        """Callback for the node size control."""
        # new_SBO = evt.GetString()
        # assert len(self._selected_idx) == 1
        # [nodei] = self._selected_idx
        # ctrl_SBO = self.SBO_ctrl.GetId()

        # if len(new_SBO) != 0:
        #     if new_SBO[:8] == "SBO:0000" and new_SBO[8:11].isdigit():
        #         self.self_changes = True
        #         with self.controller.group_action():
        #             self.controller.set_node_SBO(self.net_index, nodei, new_SBO)
        #             post_event(DidModifyNodesEvent([nodei]))
        #     else:
        #         self.main_section.SetValidationState(False, ctrl_SBO, "Not saved: Invalid SBO Term ID (Example: SBO:0000247)")
        #         return
         
        # self.main_section.SetValidationState(True, self.SBO_ctrl.GetId())

        assert self.contiguous
        ctrl_id = self.size_ctrl.GetId()
        text = evt.GetString()
        wh = parse_num_pair(text)

        if wh is not None: #single node selected
            nodes = get_nodes_by_idx(self.all_nodes, self._selected_idx)
            min_width = get_setting('min_node_width')
            min_height = get_setting('min_node_height')
            size = Vec2(wh)
            # limit size to be smaller than the compartment
            compi = nodes[0].comp_idx
            bounds: Rect
            if compi == -1:
                bounds = Rect(Vec2(), self.canvas.realsize)
            else:
                comp = self.canvas.comp_idx_map[compi]
                bounds = comp.rect

            min_nw = min(n.size.x for n in nodes)
            min_nh = min(n.size.y for n in nodes)
            min_ratio = Vec2(min_width / min_nw, min_height / min_nh)
            min_size = self._bounding_rect.size.elem_mul(min_ratio)

            if size.x < min_size.x or size.y < min_size.y:
                message = 'The size of {} needs to be at least ({}, {})'.format(
                    'bounding box' if len(nodes) > 1 else 'node',
                    no_rzeros(min_size.x, 2), no_rzeros(min_size.y, 2))
                self.main_section.SetValidationState(False, ctrl_id, message)
                return

            # if size.x > max_size.x or size.y > max_size.y:
            #     message = 'The size of bounding box cannot exceed ({}, {})'.format(
            #         no_rzeros(max_size.x, 2), no_rzeros(max_size.y, 2))
            #     self.main_section.SetValidationState(False, ctrl_id, message)
            #     return

            # NOTE clamp max size automatically rather than show error
            clamped = size.reduce2(min, bounds.size)
            if self._bounding_rect.size != clamped or size != clamped:
                ratio = clamped.elem_div(self._bounding_rect.size)
                self.self_changes = True
                with self.controller.group_action():
                    offsets = list()
                    for node in nodes:
                        rel_pos = node.position - self._bounding_rect.position
                        new_pos = self._bounding_rect.position + rel_pos.elem_mul(ratio)
                        offsets.append(new_pos - node.position)
                        node.position = new_pos
                        node.size = node.size.elem_mul(ratio)
                        # clamp so that nodes are always within compartment/bounds
                        node.position = clamp_rect_pos(node.rect, bounds)

                    idx_list = list(self._selected_idx)
                    post_event(DidMoveNodesEvent(idx_list, offsets, dragged=False))
                    post_event(DidResizeNodesEvent(idx_list, ratio=ratio, dragged=False))
                    for node in nodes:
                        self.controller.move_node(self.net_index, node.index, node.position)
                        self.controller.set_node_size(self.net_index, node.index, node.size)
        else: #hw is none
            nodes = get_nodes_by_idx(self.all_nodes, self._selected_idx)
            self.self_changes = True
            with self.controller.group_action():
                hws = text.split("; ")
                for i in range(len(hws)):
                    hw = hws[i][1:-1].split(", ")
                    if len(hw) != 2: #not in the format of "(w1, h1);(w2, h2)" either
                        self.main_section.SetValidationState(
                        False, ctrl_id, 'Should be in the form of "width, height" or "(w1, h1); (w2, h2)"')   
                        return
                    try:
                        self.controller.set_node_size(self.net_index, i, Vec2(float(hw[0]), float(hw[1])))
                    except:
                        self.main_section.SetValidationState(
                        False, ctrl_id, 'Should be in the form of "width, height" or "(w1, h1); (w2, h2)"')   
                        return

        self.main_section.SetValidationState(True, self.size_ctrl.GetId())

    def OnNodeStatusChoice(self, evt):
        """Callback for the change node status, floating or boundary."""
        selected = self.nodeStatusDropDown.GetSelection()
        if selected == 0:
            floatingStatus = True
        else:
            floatingStatus = False

        nodes = get_nodes_by_idx(self.all_nodes, self._selected_idx)
        self.self_changes = True
        with self.controller.group_action():
            for node in nodes:
                self.controller.set_node_floating_status(self.net_index, node.index, floatingStatus)
            post_event(DidModifyNodesEvent(list(self._selected_idx)))

    def OnCompositeShapes(self, evt):
        selected = self.compositeShapesDropDown.GetStringSelection()
        nodes = get_nodes_by_idx(self.all_nodes, self._selected_idx)
        self.self_changes = True
        with self.controller.group_action():
            shapei = self.compShapeNames.index(selected)

            for node in nodes:
                if shapei != 1 and node.shape_index != 1:
                    self.controller.set_node_shape_index(self.net_index, node.index, shapei)
                else:
                    if shapei == 1: # changing node to circle
                    # if shape is being changed to circle, make bounding box sides equal
                        dim = calc_node_dimensions(node.size.x, node.size.y, 1)
                    elif node.shape_index == 1:
                        # if node was a circle previously, but not anymore, restore to default ratio
                        default_ratio = get_theme('node_height')/get_theme('node_width')
                        dim = calc_node_dimensions(node.size.x, node.size.y, default_ratio)
                    if len(nodes) == 1:
                        self.size_ctrl.SetValue(str(dim.x) + ", " + str(dim.y))
                    else:
                        self.controller.set_node_size(self.net_index, node.index, dim)
                    self.controller.set_node_shape_index(self.net_index, node.index, shapei)

            post_event(DidModifyNodesEvent(list(self._selected_idx)))

        self._UpdatePrimitiveFields()

    def OnNodeLockCheckBox(self, evt):
        """Callback for the change node lock or not."""
        cb = evt.GetEventObject()
        if cb.GetValue():
            nodeLocked = True
        else:
            nodeLocked = False

        nodes = get_nodes_by_idx(self.all_nodes, self._selected_idx)
        self.self_changes = True
        with self.controller.group_action():
            for node in nodes:
                self.controller.set_node_locked_status(self.net_index, node.index, nodeLocked)
            post_event(DidModifyNodesEvent(list(self._selected_idx)))

    def _UpdatePrimitiveFields(self):
        sizer: wx.Sizer = self.GetSizer()
        sizerflags = wx.SizerFlags().Expand()

        self.Freeze()

        nodes = self.selected_nodes
        shape_names = set(n.composite_shape.name for n in nodes)

        if self.last_prim_section is not None:
            sizer.Detach(self.last_prim_section)
            self.last_prim_section.Hide()

        if len(shape_names) == 1:
            shape_index = nodes[0].shape_index

            if shape_index in self.prim_section_cache:
                # already created form for this shape before; restore the cached one
                prim_section = self.prim_section_cache[shape_index]
                prim_section.Show()
                # self.AddChild(prim_section)
                sizer.Add(prim_section, sizerflags)
            else:
                # need to create new one
                assert nodes[0].composite_shape is not None
                prim_section = PrimitiveSection(self, nodes[0].composite_shape)
                sizer.Add(prim_section, sizerflags)
                self.prim_section_cache[shape_index] = prim_section

            self.last_prim_section = prim_section

            prim_section.UpdatePrimitiveValues()
        else:
            pass  # don't need to do anything since this whole section is hidden

        # need to tell parent to adjust height as well
        self.GetParent().Layout()
        self.Thaw()

    def UpdateAllFields(self):
        """Update the form field values based on current data."""
        self.self_changes = False
        assert len(self._selected_idx) != 0
        nodes = get_nodes_by_idx(self.all_nodes, self._selected_idx)
        prec = get_setting('decimal_precision')
        id_text: str
        conc_text: str
        floatingNode: bool
        lockNode: bool
        shape_name: str

        if not self.contiguous:
            self.pos_ctrl.ChangeValue('?')
            #self.size_ctrl.ChangeValue('?')
        else:
            ChangePairValue(self.pos_ctrl, self._bounding_rect.position, prec)
            #ChangePairValue(self.size_ctrl, self._bounding_rect.size, prec)

        if not self.contiguous:
            self.size_ctrl.ChangeValue('?')

        if len(self._selected_idx) == 1:
            [node] = nodes
            self.id_ctrl.Enable(True)
            id_text = node.id
            self.comp_ctrl.Enable(False)
            #comp_text = str(node.comp_idx)
            allCompartments = api.get_compartments(self.net_index)
            comp_id = ''
            for comp in allCompartments:
                if comp.index == node.comp_idx:
                    comp_id = comp.id
            comp_text = str(comp_id)
            self.name_ctrl.Enable(True)
            name_text = str(node.node_name)
            self.SBO_ctrl.Enable(True)
            SBO_text = str(node.node_SBO)
            self.conc_ctrl.Enable(True)
            conc_text = str(node.concentration)
            self.size_ctrl.Enable(True)
            size_text = str(node.size[0]) + ", " + str(node.size[1])
            floatingNode = node.floatingNode
            lockNode = node.lockNode
            assert node.composite_shape is not None
            shape_name = node.composite_shape.name
        else:
            self.id_ctrl.Enable(False)
            id_text = '; '.join(sorted(list(n.id for n in nodes)))
            self.comp_ctrl.Enable(False)
            allCompartments = api.get_compartments(self.net_index)
            comp_list = []
            for n in nodes:
                comp_id = ''
                for comp in allCompartments:
                    if comp.index == n.comp_idx:
                        comp_id = comp.id
                comp_list.append(str(comp_id))
            comp_text = '; '.join(sorted(comp_list))
            self.name_ctrl.Enable(False)
            name_text = '; '.join(sorted(list(str(n.node_name) for n in nodes)))
            self.SBO_ctrl.Enable(False)
            SBO_text = '; '.join(sorted(list(str(n.node_SBO) for n in nodes)))
            self.conc_ctrl.Enable(False)
            conc_text = '; '.join(sorted(list(str(n.concentration) for n in nodes)))
            self.size_ctrl.Enable(True)
            size_text = '; '.join(sorted(list(str(n.size) for n in nodes)))
            floatingNode = all(n.floatingNode for n in nodes)
            lockNode = all(n.lockNode for n in nodes)
            shape_name_set = set(n.composite_shape.name for n in nodes)
            if len(shape_name_set) == 1:
                shape_name = next(iter(shape_name_set))
            else:
                shape_name = ''

        self._UpdatePrimitiveFields()
        self.pos_ctrl.Enable(self.contiguous)
        self.size_ctrl.Enable(self.contiguous)

        self.id_ctrl.ChangeValue(id_text)
        self.comp_ctrl.ChangeValue(comp_text)
        self.name_ctrl.ChangeValue(name_text)
        self.SBO_ctrl.ChangeValue(SBO_text)
        self.conc_ctrl.ChangeValue(conc_text)
        self.size_ctrl.ChangeValue(size_text)

        if floatingNode:
            self.nodeStatusDropDown.SetSelection(0)
        else:
            self.nodeStatusDropDown.SetSelection(1)

        if lockNode:
            self.lockNodeCheckBox.SetValue(True)
        else:
            self.lockNodeCheckBox.SetValue(False)

        if shape_name:
            self.compositeShapesDropDown.SetStringSelection(shape_name)
        else:
            self.compositeShapesDropDown.SetSelection(wx.NOT_FOUND)


@dataclass
class StoichInfo:
    """Helper class that stores node stoichiometry info for reaction form"""
    nodei: int
    stoich: float


'''Section for editing stoichiometry, includes only reactants or only products,
so there are two of this.'''
class StoichSection(FieldGrid):
    def __init__(self, parent, form: 'ReactionForm', stoichs: List[StoichInfo], reai: int,
                 is_reactants: bool):
        super().__init__(parent, form)

        self._reactant_subtitle = self.AppendSubtitle('Reactants' if is_reactants else 'Products')
        for stoich in stoichs:
            stoich_ctrl = self.CreateTextCtrl(value=no_rzeros(stoich.stoich, precision=2))
            node_id = self.form.controller.get_node_id(self.form.net_index, stoich.nodei)
            self.AppendControl(node_id, stoich_ctrl)
            if is_reactants:
                inner_callback = self.MakeSetSrcStoichFunction(reai, stoich.nodei)
            else:
                inner_callback = self.MakeSetDestStoichFunction(reai, stoich.nodei)
            callback = self.MakeFloatCtrlFunction(stoich_ctrl.GetId(), inner_callback, (0, None),
                                                    left_incl=False)
            stoich_ctrl.Bind(wx.EVT_TEXT, callback)

    def MakeSetSrcStoichFunction(self, reai: int, nodei: int):
        def ret(val: float):
            self.form.self_changes = True
            with self.form.controller.group_action():
                self.form.controller.set_src_node_stoich(self.form.net_index, reai, nodei, val)
                post_event(DidModifyReactionEvent(list(self.form.selected_idx)))

        return ret

    def MakeSetDestStoichFunction(self, reai: int, nodei: int):
        def ret(val: float):
            with self.form.controller.group_action():
                self.form.self_changes = True
                self.form.controller.set_dest_node_stoich(self.form.net_index, reai, nodei, val)
                post_event(DidModifyReactionEvent(list(self.form.selected_idx)))

        return ret


class ReactionForm(EditPanelForm):
    auto_center_ctrl: wx.CheckBox

    def __init__(self, parent, canvas: Canvas, controller: IController):
        super().__init__(parent, canvas, controller)

        self.reactions = list()
        self.main_section = FieldGrid(self, self)
        self.sections = [self.main_section]

        self.CreateChildren()

    def CreateControls(self):
        self.id_ctrl = self.main_section.CreateTextCtrl()
        self.id_ctrl.Bind(wx.EVT_TEXT, self._OnIdText)
        self.main_section.AppendControl('identifier', self.id_ctrl)

        self.ratelaw_ctrl = self.main_section.CreateTextCtrl()
        #self.ratelaw_ctrl.Bind(wx.EVT_TEXT, self._OnRateLawText)
        self.main_section.AppendControl('rate law', self.ratelaw_ctrl)

        self.fill_ctrl, self.fill_alpha_ctrl = self.main_section.CreateColorControl(
            'fill color', 'fill opacity',
            self._OnFillColorChanged, self._FillAlphaCallback)

        self.stroke_width_ctrl = self.main_section.CreateTextCtrl()
        stroke_cb = self.main_section.MakeFloatCtrlFunction(self.stroke_width_ctrl.GetId(),
                                                            self._StrokeWidthCallback, (0.1, 100))
        self.stroke_width_ctrl.Bind(wx.EVT_TEXT, stroke_cb)
        self.main_section.AppendControl('line width', self.stroke_width_ctrl)

        # Whether the center position should be autoly set?
        #self.auto_center_ctrl = wx.CheckBox(self.main_section)
        #self.auto_center_ctrl.SetValue(True)
        #self.auto_center_ctrl = wx.CheckBox(self.main_section, label = '')


        # self.auto_center_ctrl = wx.CheckBox(self.main_section, label = '')
        # self.auto_center_ctrl.SetValue(False)
        # self.auto_center_ctrl.Bind(wx.EVT_CHECKBOX, self._AutoCenterCallback)
        # self.main_section.AppendControl('auto center pos', self.auto_center_ctrl)


        #self.auto_center_ctrl = wx.CheckBox(self.main_section, label = '')
        self.auto_center_ctrl = wx.ToggleButton(self.main_section, -1, '')
        self.auto_center_ctrl.SetValue(False)
        self.auto_center_ctrl.SetLabel("Off")
        self.auto_center_ctrl.Bind(wx.EVT_TOGGLEBUTTON, self._AutoCenterCallback)
        self.main_section.AppendControl('auto center', self.auto_center_ctrl)


        self.center_pos_ctrl = self.main_section.CreateTextCtrl()
        self.center_pos_ctrl.Disable()
        self.center_pos_ctrl.Bind(wx.EVT_TEXT, self._CenterPosCallback)
        self.main_section.AppendControl('center position', self.center_pos_ctrl)

        self._reactant_subtitle = None
        self._product_subtitle = None
        self.reactant_stoich_ctrls = list()
        self.product_stoich_ctrls = list()

        states = ['bezier curve', 'straight line']
        self.rxnStatusDropDown = wx.Choice(self.main_section, choices=states)
        self.main_section.AppendControl('reaction status', self.rxnStatusDropDown)
        self.rxnStatusDropDown.Bind(wx.EVT_CHOICE, self.OnRxnStatusChoice)

        self.mod_tip_dropdown = wx.ComboBox(
            self.main_section, choices=[e.value for e in ModifierTipStyle], style=wx.CB_READONLY)
        self.main_section.AppendControl('modifier tip', self.mod_tip_dropdown)
        self.mod_tip_dropdown.Bind(wx.EVT_COMBOBOX, self.ModifierTipCallback)

        self._modifiers = set()
        self.all_nodes = list()
        self.node_indices = set()
        self.modifiers_ctrl = wx.CheckListBox(
            self.main_section, style=wx.LB_NEEDED_SB, size=(-1, 100))
        self.main_section.AppendControl('modifiers', self.modifiers_ctrl)
        self.modifiers_ctrl.Bind(wx.EVT_CHECKLISTBOX, self.OnModifierCheck)
        self.reactants_section = None
        self.products_section = None

    def _OnIdText(self, evt):
        """Callback for the ID control."""
        new_id = evt.GetString()
        assert len(self._selected_idx) == 1, 'Reaction ID field should be disabled when ' + \
            'multiple are selected'
        [reai] = self._selected_idx
        ctrl_id = self.id_ctrl.GetId()
        if len(new_id) == 0:
            self.main_section.SetValidationState(False, ctrl_id, "ID cannot be empty")
            return
        else:
            for rxn in self.reactions:
                if rxn.id == new_id:
                    self.main_section.SetValidationState(False, ctrl_id, "Not saved: Duplicate ID")
                    return

            # loop terminated fine. There is no duplicate ID
            self.self_changes = True
            with self.controller.group_action():
                self.controller.rename_reaction(self.net_index, reai, new_id)
                post_event(DidModifyReactionEvent(list(self._selected_idx)))
            self.main_section.SetValidationState(True, ctrl_id)

    def _StrokeWidthCallback(self, width: float):
        reactions = [r for r in self.reactions if r.index in self._selected_idx]
        self.self_changes = True
        with self.controller.group_action():
            for rxn in reactions:
                self.controller.set_reaction_line_thickness(self.net_index, rxn.index, width)
            post_event(DidModifyReactionEvent(list(self._selected_idx)))

    def OnRxnStatusChoice(self, evt):
        """Callback for the change reaction status, bezier curve or straight line."""
        selection = self.rxnStatusDropDown.GetSelection()
        # TODO this is hardcoded. If the text changes this wouldn't work
        if selection == 0:
            bezierCurves = True
        else:
            bezierCurves = False

        rxns = get_rxns_by_idx(self.reactions, self._selected_idx)
        self.self_changes = True
        with self.controller.group_action():
            for rxn in rxns:
                self.controller.set_reaction_bezier_curves(self.net_index, rxn.index, bezierCurves)
            post_event(DidModifyReactionEvent(list(self._selected_idx)))

    def ModifierTipCallback(self, evt):
        """Callback for the change reaction status, bezier curve or straight line."""
        status = self.mod_tip_dropdown.GetValue()
        entry: ModifierTipStyle
        for e in ModifierTipStyle:
            if e.value == status:
                entry = e
                break
        else:
            assert False, ('Unable to find corresponding enum entry to dropdown selection. ' +
                           'This is not supposed to happen.')

        rxns = get_rxns_by_idx(self.reactions, self._selected_idx)
        self.self_changes = True
        with self.controller.group_action():
            for rxn in rxns:
                self.controller.set_modifier_tip_style(self.net_index, rxn.index, entry)
            post_event(DidModifyReactionEvent(list(self._selected_idx)))

    def _AutoCenterCallback(self, evt):

        checked = evt.GetInt()

        assert len(self._selected_idx) == 1
        prec = 2
        reaction = self.canvas.reaction_idx_map[next(iter(self._selected_idx))]
        centroid_map = self.canvas.GetReactionCentroids(self.net_index)
        centroid = centroid_map[reaction.index]
        if checked:
            self.auto_center_ctrl.Enable()
            self.auto_center_ctrl.SetValue(True)
            self.auto_center_ctrl.SetLabel("On")
            self.center_pos_ctrl.ChangeValue('')
            self.center_pos_ctrl.Disable()
            with self.controller.group_action():
                self.controller.set_reaction_center(self.net_index, reaction.index, None)
                # Move centroid handle along if centroid changed.
                if reaction.center_pos is not None:
                    offset = centroid - reaction.center_pos
                    if offset != Vec2():
                        self.controller.set_center_handle(
                            self.net_index, reaction.index, reaction.src_c_handle.tip + offset)
            self.center_pos_ctrl.Disable()
        else:
            self.auto_center_ctrl.Enable()
            self.auto_center_ctrl.SetValue(False)
            self.auto_center_ctrl.SetLabel("Off")
            self.center_pos_ctrl.Enable()
            self.center_pos_ctrl.ChangeValue('{}, {}'.format(
                no_rzeros(centroid.x, prec), no_rzeros(centroid.y, prec)
            ))
            self.controller.set_reaction_center(self.net_index, reaction.index, centroid)
        

    def _CenterPosCallback(self, evt):
        text = evt.GetString()
        xy = parse_num_pair(text)
        ctrl_id = self.center_pos_ctrl.GetId()
        if xy is None:
            self.main_section.SetValidationState(False, ctrl_id, 'Should be in the form "X, Y"')
            return

        pos = Vec2(xy)
        if pos.x < 0 or pos.y < 0:
            self.main_section.SetValidationState(
                False, ctrl_id, 'Position coordinates should be non-negative')
            return

        assert len(self._selected_idx) == 1
        reaction = self.canvas.reaction_idx_map[next(iter(self._selected_idx))]
        if reaction.center_pos != pos:
            offset = pos - reaction.center_pos
            self.self_changes = True
            with self.controller.group_action():
                self.controller.set_reaction_center(self.net_index, reaction.index, pos)
                post_event(DidMoveReactionCenterEvent(self.net_index, reaction.index, offset, False))
        self.main_section.SetValidationState(True, ctrl_id)

    def _OnFillColorChanged(self, fill: wx.Colour):
        """Callback for the fill color control."""
        reactions = [r for r in self.reactions if r.index in self._selected_idx]
        self.self_changes = True
        with self.controller.group_action():
            for rxn in reactions:
                if on_msw():
                    self.controller.set_reaction_fill_rgb(self.net_index, rxn.index, fill)
                else:
                    # we can set both the RGB and the alpha at the same time
                    self.controller.set_reaction_fill_rgb(self.net_index, rxn.index, fill)
                    self.controller.set_reaction_fill_alpha(self.net_index, rxn.index, fill.Alpha())
            post_event(DidModifyReactionEvent(list(self._selected_idx)))

    def _FillAlphaCallback(self, alpha: float):
        """Callback for when the fill alpha changes."""
        reactions = (r for r in self.reactions if r.index in self._selected_idx)
        self.self_changes = True
        with self.controller.group_action():
            for rxn in reactions:
                self.controller.set_reaction_fill_alpha(self.net_index, rxn.index, int(alpha * 255))
            post_event(DidModifyReactionEvent(list(self._selected_idx)))

    def _OnRateLawText(self, evt: wx.CommandEvent):
        ratelaw = evt.GetString()
        assert len(self._selected_idx) == 1, 'Reaction rate law field should be disabled when ' + \
            'multiple are selected'
        [reai] = self._selected_idx
        self.self_changes = True
        post_event(DidModifyReactionEvent(list(self._selected_idx)))
        self.controller.set_reaction_ratelaw(self.net_index, reai, ratelaw)

    def OnModifierCheck(self, evt: wx.CommandEvent):
        evt.Skip()
        assert len(self._selected_idx) == 1
        reactions = [r for r in self.reactions if r.index in self._selected_idx]
        assert len(reactions) == 1
        reaction = reactions[0]
        new_modifiers = [self.all_nodes[i].index for i in self.modifiers_ctrl.GetCheckedItems()]
        self.controller.set_reaction_modifiers(self.net_index, reaction.index, new_modifiers)

    def CanvasUpdated(self, reactions: List[Reaction], nodes: List[Node]):
        """Function called after the canvas has been updated."""
        self.reactions = reactions
        self.all_nodes = nodes
        new_node_indices = set(n.index for n in nodes)
        # if new_node_indices != self.node_indices:
        self.node_indices = new_node_indices
        self._UpdateModifierList()
        self.ExternalUpdate()

    def UpdateSelection(self, selected_idx: List[int]):
        """Function called after the list of selected reactions have been updated."""
        self._selected_idx = selected_idx
        if len(self._selected_idx) != 0:
            title_label = 'Edit Reaction' if len(self._selected_idx) == 1 \
                else 'Edit Multiple Reactions'
            self._title.SetLabel(title_label)

            id_text = 'identifier' if len(self._selected_idx) == 1 else 'identifiers'
            self.main_section.labels[self.id_ctrl.GetId()].SetLabel(id_text)
            self.UpdateAllFields()
        self.ExternalUpdate()

    def _UpdateModifierList(self):
        # NOTE if slightly better performance is wanted, we don't have to update this widget
        # immediately. Rather we can have a dirty flag and update only when displaying
        node_names = list()
        for n in self.all_nodes:
            name = n.id
            if n.original_index != -1:
                name += ' (alias)'
            node_names.append(name)

        self.modifiers_ctrl.Set(node_names)
        self._UpdateModifierSelection()

    def _UpdateModifierSelection(self):
        checked_indices = set(i for i, n in enumerate(self.all_nodes) if n.index in self._modifiers)
        self.modifiers_ctrl.SetCheckedItems(checked_indices)

    def _UpdateStoichFields(self, reai: int, reactants: List[StoichInfo], products: List[StoichInfo]):
        sizer = self.GetSizer()
        sizerflags = wx.SizerFlags().Expand()

        self.Freeze()
        if self.reactants_section is not None:
            sizer.Detach(self.reactants_section)
            sizer.Detach(self.products_section)
            self.reactants_section.Destroy()
            self.products_section.Destroy()

        if len(reactants) != 0:
            assert len(products) != 0
            self.reactants_section = StoichSection(self, self, reactants, reai, True)
            self.products_section = StoichSection(self, self, products, reai, False)
            sizer.Add(self.reactants_section, sizerflags)
            sizer.Add(self.products_section, sizerflags)
        else:
            self.reactants_section = None
            self.products_section = None
            # Both reactants and products are empty; don't add
            assert len(products) == 0

        self.Layout()
        self.Thaw()

    def _GetSrcStoichs(self, reai: int):
        ids = self.controller.get_list_of_src_indices(self.net_index, reai)
        return [StoichInfo(id, self.controller.get_src_node_stoich(self.net_index, reai, id))
                for id in ids]

    def _GetDestStoichs(self, reai: int):
        ids = self.controller.get_list_of_dest_indices(self.net_index, reai)
        return [StoichInfo(id, self.controller.get_dest_node_stoich(self.net_index, reai, id))
                for id in ids]

    def UpdateAllFields(self):
        """Update all reaction fields from current data."""
        self.self_changes = False
        assert len(self._selected_idx) != 0
        reactions = [r for r in self.reactions if r.index in self._selected_idx]
        id_text = '; '.join(sorted(list(r.id for r in reactions)))
        fill: wx.Colour
        fill_alpha: Optional[int]
        ratelaw_text: str

        prec = get_setting('decimal_precision')

        if len(self._selected_idx) == 1:
            [reaction] = reactions
            reai = reaction.index
            self.id_ctrl.Enable()
            fill = reaction.fill_color
            fill_alpha = reaction.fill_color.Alpha()
            ratelaw_text = reaction.rate_law
            #self.ratelaw_ctrl.Enable()
            self.ratelaw_ctrl.Disable()
            
            self.auto_center_ctrl.Enable()
            auto_set = reaction.center_pos is None
            self.auto_center_ctrl.SetValue(auto_set)
            if auto_set:
                self.auto_center_ctrl.SetLabel("On")
                self.center_pos_ctrl.ChangeValue(' ')
            else:
                self.auto_center_ctrl.SetLabel("Off")
            self.center_pos_ctrl.Enable(not auto_set)
            if reaction.center_pos is not None:
                centroid = reaction.center_pos
                self.center_pos_ctrl.ChangeValue('{}, {}'.format(
                    no_rzeros(centroid.x, prec), no_rzeros(centroid.y, prec)
                ))

            self._UpdateStoichFields(reai, self._GetSrcStoichs(reai), self._GetDestStoichs(reai))
            self.modifiers_ctrl.Enable()
            self._modifiers = reaction.modifiers
            self._UpdateModifierSelection()
        else:

            self.id_ctrl.Disable()
            fill, fill_alpha = GetMultiColor(list(r.fill_color for r in reactions))
            ratelaw_text = 'multiple'
            self.ratelaw_ctrl.Disable()
            self.auto_center_ctrl.SetValue(False)
            self.auto_center_ctrl.SetLabel("Off")
            self.auto_center_ctrl.Disable()
            self.center_pos_ctrl.ChangeValue(' ')
            self.center_pos_ctrl.Disable()

            self._UpdateStoichFields(0, [], [])
            self.modifiers_ctrl.Disable()
            self._modifiers = set()
            self._UpdateModifierSelection()

        bezierCurves = all(r.bezierCurves for r in reactions)
        mod_tip_style = GetMultiEnum(
            list(r.modifier_tip_style for r in reactions), ModifierTipStyle.CIRCLE)
        stroke_width = GetMultiFloatText(set(r.thickness for r in reactions), prec)

        self.id_ctrl.ChangeValue(id_text)
        self.fill_ctrl.SetColour(fill)
        self.ratelaw_ctrl.ChangeValue(ratelaw_text)
        self.stroke_width_ctrl.ChangeValue(stroke_width)
        self.mod_tip_dropdown.SetValue(mod_tip_style.value)

        if on_msw():
            self.fill_alpha_ctrl.ChangeValue(AlphaToText(fill_alpha, prec))

        # HMS Replaced stings with contants
        if bezierCurves:
            self.rxnStatusDropDown.SetSelection(0)
        else:
            self.rxnStatusDropDown.SetSelection(1)


class CompartmentForm(EditPanelForm):
    _compartments: List[Compartment]
    contiguous: bool

    def __init__(self, parent, canvas: Canvas, controller: IController):
        super().__init__(parent, canvas, controller)
        self.compartments = list()
        self.contiguous = True

        self.main_section = FieldGrid(self, self)
        self.sections = [self.main_section]

        self.CreateChildren()

    def CreateControls(self):
        self.id_ctrl = self.main_section.CreateTextCtrl()
        self.id_ctrl.Bind(wx.EVT_TEXT, self._OnIdText)
        self.main_section.AppendControl('identifier', self.id_ctrl)

        self.pos_ctrl = self.main_section.CreateTextCtrl()
        self.pos_ctrl.Bind(wx.EVT_TEXT, self._OnPosText)
        self.main_section.AppendControl('position', self.pos_ctrl)

        self.size_ctrl = self.main_section.CreateTextCtrl()
        self.size_ctrl.Bind(wx.EVT_TEXT, self._OnSizeText)
        self.main_section.AppendControl('size', self.size_ctrl)

        self.volume_ctrl = self.main_section.CreateTextCtrl()
        self.main_section.AppendControl('volume', self.volume_ctrl)
        volume_callback = self.main_section.MakeFloatCtrlFunction(self.volume_ctrl.GetId(),
                                                                  self._VolumeCallback, (0, None), left_incl=False)
        self.volume_ctrl.Bind(wx.EVT_TEXT, volume_callback)

        self.fill_ctrl, self.fill_alpha_ctrl = self.main_section.CreateColorControl(
            'fill color', 'fill opacity',
            self._OnFillColorChanged, self._FillAlphaCallback,)

        self.border_ctrl, self.border_alpha_ctrl = self.main_section.CreateColorControl(
            'border color', 'border opacity',
            self._OnBorderColorChanged, self._BorderAlphaCallback)

        self.border_width_ctrl = self.main_section.CreateTextCtrl()
        self.main_section.AppendControl('border width', self.border_width_ctrl)
        border_callback = self.main_section.MakeFloatCtrlFunction(self.border_width_ctrl.GetId(),
                                                                  self._BorderWidthCallback, (1, 100))
        self.border_width_ctrl.Bind(wx.EVT_TEXT, border_callback)

    def _OnIdText(self, evt):
        """Callback for the ID control."""
        new_id = evt.GetString()
        assert len(self._selected_idx) == 1, 'Compartment ID field should be disabled when ' + \
            'multiple are selected'
        [compi] = self._selected_idx
        ctrl_id = self.id_ctrl.GetId()
        if len(new_id) == 0:
            self.main_section.SetValidationState(False, ctrl_id, "ID cannot be empty")
            return
        else:
            for comp in self.compartments:
                if comp.id == new_id:
                    self.main_section.SetValidationState(False, ctrl_id, "Not saved: Duplicate ID")
                    return

            # loop terminated fine. There is no duplicate ID
            self.self_changes = True
            with self.controller.group_action():
                self.controller.rename_compartment(self.net_index, compi, new_id)
                post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))
            self.main_section.SetValidationState(True, ctrl_id)

    def _OnPosText(self, evt):
        """Callback for the position control."""
        assert self.contiguous
        text = evt.GetString()
        xy = parse_num_pair(text)
        ctrl_id = self.pos_ctrl.GetId()
        if xy is None:
            self.main_section.SetValidationState(False, ctrl_id, 'Should be in the form "X, Y"')
            return

        pos = Vec2(xy)
        if pos.x < 0 or pos.y < 0:
            self.main_section.SetValidationState(
                False, ctrl_id, 'Position coordinates should be non-negative')
            return
        comps = [c for c in self.compartments if c.index in self._selected_idx]
        bounds = Rect(Vec2(), self.canvas.realsize)
        clamped = clamp_rect_pos(Rect(pos, self._bounding_rect.size), bounds)
        if self._bounding_rect.position != pos or pos != clamped:
            offset = clamped - self._bounding_rect.position
            self.self_changes = True
            with self.controller.group_action():
                for comp in comps:
                    comp.position += offset
                post_event(DidMoveCompartmentsEvent(list(self._selected_idx), offset, dragged=False))
                for comp in comps:
                    self.controller.move_node(self.net_index, comp.index, comp.position)
        self.main_section.SetValidationState(True, self.pos_ctrl.GetId())

    def _OnSizeText(self, evt):
        """Callback for the size control."""
        ctrl_id = self.size_ctrl.GetId()
        text = evt.GetString()
        wh = parse_num_pair(text)
        if wh is None:
            self.main_section.SetValidationState(
                False, ctrl_id, 'Should be in the form "width, height"')
            return

        comps = [c for c in self.compartments if c.index in self._selected_idx]
        size = Vec2(wh)
        _, comp_min_ratio = self.canvas.select_box.compute_min_ratio()
        assert comp_min_ratio is not None
        limit = self._bounding_rect.size.elem_mul(comp_min_ratio)

        if size.x < limit.x or size.y < limit.y:
            message = 'Size of {} needs to be at least ({}, {})'.format(
                'bounding box' if len(comps) > 1 else 'compartment',
                no_rzeros(limit.x, 2), no_rzeros(limit.y, 2))
            self.main_section.SetValidationState(False, ctrl_id, message)
            return

        clamped = clamp_rect_size(Rect(self._bounding_rect.position, size), self.canvas.realsize)
        if self._bounding_rect.size != clamped or size != clamped:
            ratio = clamped.elem_div(self._bounding_rect.size)
            self.self_changes = True
            with self.controller.group_action():
                offsets = list()
                peripheral_nodes = list()
                peripheral_offsets = list()
                for comp in comps:
                    rel_pos = comp.position - self._bounding_rect.position
                    new_pos = self._bounding_rect.position + rel_pos.elem_mul(ratio)
                    offsets.append(new_pos - comp.position)
                    comp.position = new_pos
                    comp.size = comp.size.elem_mul(ratio)

                    pnodes = [self.canvas.node_idx_map[i] for i in comp.nodes]
                    for node in pnodes:
                        new_pos = clamp_rect_pos(node.rect, comp.rect)
                        if new_pos != node.position:
                            node.position = new_pos
                            peripheral_nodes.append(node)
                            peripheral_offsets.append(new_pos - node.position)

                idx_list = list(self._selected_idx)
                post_event(DidMoveCompartmentsEvent(idx_list, offsets, dragged=False))
                post_event(DidResizeCompartmentsEvent(idx_list, ratio, dragged=False))
                if len(peripheral_nodes) != 0:
                    post_event(DidMoveNodesEvent(peripheral_nodes, peripheral_offsets, dragged=False))
                for comp in comps:
                    self.controller.move_compartment(self.net_index, comp.index, comp.position)
                    self.controller.set_compartment_size(self.net_index, comp.index, comp.size)

                for node in peripheral_nodes:
                    self.controller.move_node(self.net_index, node.index, node.position)
        self.main_section.SetValidationState(True, self.size_ctrl.GetId())

    def _VolumeCallback(self, volume: float):
        """Callback for when the border width changes."""
        comps = [c for c in self.compartments if c.index in self._selected_idx]
        self.self_changes = True
        with self.controller.group_action():
            for comp in comps:
                self.controller.set_compartment_volume(self.net_index, comp.index, volume)
            post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))

    def _OnFillColorChanged(self, fill: wx.Colour):
        """Callback for the fill color control."""
        comps = [c for c in self.compartments if c.index in self._selected_idx]
        self.self_changes = True
        with self.controller.group_action():
            for comp in comps:
                if on_msw():
                    fill = wx.Colour(fill.GetRGB())  # remove alpha channel
                self.controller.set_compartment_fill(self.net_index, comp.index, fill)
            post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))

    def _OnBorderColorChanged(self, border: wx.Colour):
        """Callback for the border color control."""
        comps = [c for c in self.compartments if c.index in self._selected_idx]
        self.self_changes = True
        with self.controller.group_action():
            for comp in comps:
                if on_msw():
                    border = wx.Colour(border.GetRGB())  # remove alpha channel
                self.controller.set_compartment_border(self.net_index, comp.index, border)
            post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))

    def _FillAlphaCallback(self, alpha: float):
        """Callback for when the fill alpha changes."""
        comps = [c for c in self.compartments if c.index in self._selected_idx]
        self.self_changes = True
        with self.controller.group_action():
            for comp in comps:
                new_fill = change_opacity(comp.fill, int(alpha * 255))
                self.controller.set_compartment_fill(self.net_index, comp.index, new_fill)
            post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))

    def _BorderAlphaCallback(self, alpha: float):
        """Callback for when the border alpha changes."""
        comps = [c for c in self.compartments if c.index in self._selected_idx]
        self.self_changes = True
        with self.controller.group_action():
            for comp in comps:
                new_border = change_opacity(comp.border, int(alpha * 255))
                self.controller.set_compartment_border(self.net_index, comp.index, new_border)
            post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))

    def _BorderWidthCallback(self, width: float):
        """Callback for when the border width changes."""
        comps = [c for c in self.compartments if c.index in self._selected_idx]
        self.self_changes = True
        with self.controller.group_action():
            for comp in comps:
                self.controller.set_compartment_border_width(self.net_index, comp.index, width)
            post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))

    def UpdateCompartments(self, comps: List[Compartment]):
        self.compartments = comps
        self._UpdateBoundingRect()
        self.ExternalUpdate()

    def UpdateSelection(self, selected_idx: List[int], nodes_selected: bool):
        self._selected_idx = selected_idx
        if len(selected_idx) != 0:
            self._UpdateBoundingRect()

        self.contiguous = not nodes_selected

        if len(self._selected_idx) != 0:
            # clear position value
            # self.pos_ctrl.ChangeValue('')
            self.UpdateAllFields()

            title_label = 'Edit Compartment' if len(
                self._selected_idx) == 1 else 'Edit Multiple Compartments'
            self._title.SetLabel(title_label)

            id_text = 'identifier' if len(self._selected_idx) == 1 else 'identifiers'
            self.main_section.labels[self.id_ctrl.GetId()].SetLabel(id_text)
        self.ExternalUpdate()

    def UpdateAllFields(self):
        self.self_changes = False
        comps = [c for c in self.compartments if c.index in self._selected_idx]
        assert len(comps) == len(self._selected_idx)
        prec = 2

        id_text = '; '.join([c.id for c in comps])
        fill: wx.Colour
        fill_alpha: Optional[int]
        border: wx.Colour

        self.pos_ctrl.Enable(self.contiguous)
        self.size_ctrl.Enable(self.contiguous)
        border_width = GetMultiFloatText(set(c.border_width for c in comps), prec)
        volume = GetMultiFloatText(set(c.volume for c in comps), prec)

        if not self.contiguous:
            self.pos_ctrl.ChangeValue('?')
            self.size_ctrl.ChangeValue('?')
        else:
            ChangePairValue(self.pos_ctrl, self._bounding_rect.position, prec)
            ChangePairValue(self.size_ctrl, self._bounding_rect.size, prec)

        if len(self._selected_idx) == 1:
            [comp] = comps
            self.id_ctrl.Enable()
            fill = comp.fill
            fill_alpha = comp.fill.Alpha()
            border = comp.border
            border_alpha = comp.border.Alpha()
        else:
            self.id_ctrl.Disable()
            fill, fill_alpha = GetMultiColor(list(c.fill for c in comps))
            border, border_alpha = GetMultiColor(list(c.border for c in comps))

        self.id_ctrl.ChangeValue(id_text)
        self.fill_ctrl.SetColour(fill)
        self.border_ctrl.SetColour(border)
        self.volume_ctrl.ChangeValue(volume)

        # set fill alpha if on windows
        if on_msw():
            self.fill_alpha_ctrl.ChangeValue(AlphaToText(fill_alpha, prec))
            self.border_alpha_ctrl.ChangeValue(AlphaToText(border_alpha, prec))

        self.border_width_ctrl.ChangeValue(border_width)

    def CompsMovedOrResized(self, evt):
        """Called when nodes are moved or resized by dragging"""
        if not evt.dragged:
            return
        self._UpdateBoundingRect()
        prec = 2
        ChangePairValue(self.pos_ctrl, self._bounding_rect.position, prec)
        ChangePairValue(self.size_ctrl, self._bounding_rect.size, prec)

    def _UpdateBoundingRect(self):
        """Update bounding rectangle; mixed indicates whether both nodes and comps are selected.
        """
        rects = [c.rect for c in self.compartments if c.index in self._selected_idx]
        # It could be that compartments have been updated but selected indices have not.
        # In that case rects can be empty
        if len(rects) != 0:
            self._bounding_rect = get_bounding_rect(rects)
