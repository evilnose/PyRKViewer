"""All sorts of form widgets, mainly those used in EditPanel.
"""
# pylint: disable=maybe-no-member
from itertools import chain, compress
import wx
from wx.core import EVT_CHOICE, NOT_FOUND
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
from .canvas.data import ChoiceItem, Compartment, FONT_FAMILY_CHOICES, Reaction, TPrimitive, compute_centroid
from .canvas.geometry import Rect, Vec2, clamp_rect_pos, clamp_rect_size, get_bounding_rect
from .canvas.utils import get_nodes_by_idx, get_rxns_by_idx
from .canvas.data import TCirclePrim, TRectanglePrim, TCompositeShape


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


class EditPanelForm(ScrolledPanel):
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
    _info_bitmap: wx.Bitmap  # :  bitmap for the info badge (icon), for when an input is invalid.
    _info_length: int  #: length of the square reserved for _info_bitmap
    _title: wx.StaticText  #: title of the form
    _self_changes: bool  #: flag for if edits were made but the controller hasn't updated the view yet

    def __init__(self, parent, canvas: Canvas, controller: IController):
        super().__init__(parent, style=wx.VSCROLL)
        self.SetForegroundColour(get_theme('toolbar_fg'))
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
        self._self_changes = False
        self._selected_idx = set()

    @property
    def selected_idx(self):
        return self._selected_idx

    @abstractmethod
    def UpdateAllFields(self):
        pass

    @abstractmethod
    def CreateControls(self, sizer: wx.GridSizer):
        pass

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

    def ExternalUpdate(self):
        if len(self._selected_idx) != 0 and not self._self_changes:
            self.UpdateAllFields()

        # clear validation errors
        for id in self.badges.keys():
            self._SetValidationState(True, id)
        self._self_changes = False

    def InitLayout(self):
        sizer = self.InitAndGetSizer()
        self.CreateControls(sizer)
        self.SetSizer(sizer)
        self.SetupScrolling()

    def InitAndGetSizer(self) -> wx.GridSizer:
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
        width = self.GetSize()[0]
        right_width = (width - VGAP * 3 - MORE_LEFT_PADDING - MORE_RIGHT_PADDING -
                       self._info_length) * 0.7
        sizer.Add(int(right_width), 0, wx.GBPosition(0, 2), wx.GBSpan(1, 1))
        sizer.AddGrowableCol(0, 3)
        sizer.AddGrowableCol(1, 7)

        sizer.Add(self._title, wx.GBPosition(1, 0), wx.GBSpan(1, 5), flag=wx.ALIGN_CENTER)
        self._AppendSpacer(sizer, 0)
        return sizer

    def _AppendControl(self, sizer: wx.GridSizer, label_str: str, ctrl: wx.Control):
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
        info_badge.Show(False)
        sizer.Add(info_badge, wx.GBPosition(rows, 3), wx.GBSpan(1, 1),
                  flag=wx.ALIGN_CENTER)
        self.labels[ctrl.GetId()] = label
        self.badges[ctrl.GetId()] = info_badge

    def _AppendSpacer(self, sizer: wx.GridSizer, height: int):
        """Append a horizontal spacer with the given height.

        Note:
            The VGAP value still applies, i.e. there is an additional gap between the spacer and
            the next row.
        """
        rows = sizer.GetRows()
        sizer.Add(0, height, wx.GBPosition(rows, 0), wx.GBSpan(1, 5))

    def _AppendLine(self, sizer: wx.GridSizer):
        """Append a horizontal spacer with the given height.

        Note:
            The VGAP value still applies, i.e. there is an additional gap between the spacer and
            the next row.
        """
        rows = sizer.GetRows()
        line = wx.StaticLine(self)
        sizer.Add(line, wx.GBPosition(rows, 0), wx.GBSpan(1, 5))

    def _AppendSubtitle(self, sizer: wx.GridSizer, text: str) -> wx.StaticText:
        self._AppendSpacer(sizer, 3)
        sizer.Add(0, 0, wx.GBPosition(sizer.GetRows(), 0))
        statictext = wx.StaticText(self, label=text)
        font = wx.Font(wx.FontInfo(9))
        statictext.SetFont(font)
        sizer.Add(statictext, wx.GBPosition(sizer.GetRows(), 0),
                  wx.GBSpan(1, 5), flag=wx.ALIGN_CENTER)
        self._AppendSpacer(sizer, 0)
        return statictext

    @classmethod
    def _SetBestInsertion(cls, ctrl: wx.TextCtrl, orig_text: str, orig_insertion: int):
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

    def _SetValidationState(self, good: bool, ctrl_id: str, message: str = ""):
        """Set the validation state for a control.

        Args:
            good: Whether the control is currently valid.
            ctrl_id: The ID of the control.
            message: The message displayed, if the control is not valid.
        """
        self.Freeze()
        badge = self.badges[ctrl_id]
        if good:
            badge.Show(False)
        else:
            badge.Show(True)
            badge.SetToolTip(message)
        self.Layout()
        self.Thaw()

    def _CreateColorControl(self, label: str, alpha_label: str,
                            color_callback: ColorCallback, alpha_callback: FloatCallback,
                            sizer: wx.GridSizer, alpha_range: Tuple[float, float] = (0, 1),
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
        self._AppendControl(sizer, label, ctrl)

        alpha_ctrl = None

        if on_msw():
            # Windows does not support picking alpha in color picker. So we add an additional
            # field for that
            alpha_text = self._AlphaToText(placeholder_alpha, 2)
            alpha_ctrl = self.CreateTextCtrl(value=alpha_text)
            self._AppendControl(sizer, alpha_label, alpha_ctrl)
            callback = self._MakeFloatCtrlFunction(alpha_ctrl.GetId(), alpha_callback, alpha_range)
            alpha_ctrl.Bind(wx.EVT_TEXT, callback)

        return ctrl, alpha_ctrl

    def _MakeFloatCtrlFunction(self, ctrl_id: str, callback: FloatCallback,
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
                self._SetValidationState(False, ctrl_id, "Value must be a number")
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
                self._SetValidationState(False, ctrl_id, err_msg)
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

    @classmethod
    def _GetMultiEnum(cls, entries: List[Any], fallback):
        """Similar to _GetMultiColor, but for enums.
        
        Need to specify a fallback value in case the entries are different.
        """
        entries_set = set(entries)
        if len(entries_set) == 1:
            return next(iter(entries_set))
        else:
            return fallback

    @classmethod
    def _GetMultiFloatText(cls, values: Set[float], precision: int) -> str:
        """Returns the common float value if the set has only one element, otherwise return "?".

        See _GetMultiColor for more detail.
        """
        return no_rzeros(next(iter(values)), precision) if len(values) == 1 else '?'

    @classmethod
    def _GetMultiInt(cls, values: Set[int]) -> Optional[int]:
        """Returns the common float value if the set has only one element, otherwise return "?".

        See _GetMultiColor for more detail.
        """
        return next(iter(values)) if len(values) == 1 else None

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
    """
    contiguous: bool
    id_ctrl: wx.TextCtrl
    pos_ctrl: wx.TextCtrl
    size_ctrl: wx.TextCtrl
    nodeStatusDropDown : wx.Choice
    compositeShapesDropDown: wx.Choice
    lockNodeCheckBox : wx.CheckBox

    _nodes: List[Node]  #: current list of nodes in canvas.
    _selected_idx: Set[int]  #: current list of selected indices in canvas.
    _bounding_rect: Optional[Rect]  #: the exact bounding rectangle of the selected nodes

    def __init__(self, parent, canvas: Canvas, controller: IController):
        super().__init__(parent, canvas, controller)
        self._nodes = list()
        self._bounding_rect = None  # No padding
        # boolean to indicate whether only nodes are selected, and only nodes from the same
        # compartment are selected
        self.contiguous = True
        self.primitives_start_row = None
        self.InitLayout()

    def UpdateNodes(self, nodes: List[Node]):
        """Function called after the list of nodes have been updated."""
        self._nodes = nodes
        self._UpdateBoundingRect()
        self.ExternalUpdate()

    def NodesMovedOrResized(self, evt):
        """Called when nodes are moved or resized by dragging"""
        if not evt.dragged:
            return
        # Possibly no nodes are selected because they are moved along with the compartments
        if len(self.selected_idx) != 0:
            self._UpdateBoundingRect()
            prec = 2
            self._ChangePairValue(self.pos_ctrl, self._bounding_rect.position, prec)
            self._ChangePairValue(self.size_ctrl, self._bounding_rect.size, prec)

    def _UpdateBoundingRect(self):
        """Update bounding rectangle; mixed indicates whether both nodes and comps are selected.
        """
        rects = [n.rect for n in self._nodes if n.index in self.selected_idx]
        # It could be that compartments have been updated but selected indices have not.
        # In that case rects can be empty
        if len(rects) != 0:
            self._bounding_rect = get_bounding_rect(rects)

    def UpdateSelection(self, selected_idx: Set[int], comps_selected: bool):
        """Function called after the list of selected nodes have been updated."""
        self._selected_idx = selected_idx
        if len(selected_idx) != 0:
            self._UpdateBoundingRect()

        if comps_selected:
            self.contiguous = False
        else:
            nodes = [n for n in self._nodes if n.index in selected_idx]
            self.contiguous = len(set(n.comp_idx for n in nodes)) <= 1

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
        self.ExternalUpdate()

    def CreateControls(self, sizer: wx.GridSizer):
        self.id_ctrl = self.CreateTextCtrl()
        self.id_ctrl.Bind(wx.EVT_TEXT, self._OnIdText)
        self._AppendControl(sizer, 'identifier', self.id_ctrl)

        self.pos_ctrl = self.CreateTextCtrl()
        self.pos_ctrl.Bind(wx.EVT_TEXT, self._OnPosText)
        self._AppendControl(sizer, 'position', self.pos_ctrl)

        self.size_ctrl = self.CreateTextCtrl()
        self.size_ctrl.Bind(wx.EVT_TEXT, self._OnSizeText)
        self._AppendControl(sizer, 'size', self.size_ctrl)

        self.nodeStates = ['Floating Node', 'Boundary Node'] 
        self.nodeStatusDropDown = wx.Choice(self, choices=self.nodeStates)
        self._AppendControl(sizer, 'node status', self.nodeStatusDropDown)
        self.nodeStatusDropDown.Bind(wx.EVT_CHOICE, self.OnNodeStatusChoice)

        self.lockNodeCheckBox = wx.CheckBox(self, label = '') 
        self._AppendControl(sizer, 'lock node', self.lockNodeCheckBox)
        self.lockNodeCheckBox.Bind(wx.EVT_CHECKBOX, self.OnNodeLockCheckBox)

        self.compositeShapes = [_.name for _ in self.controller.get_composite_shape_list(self.net_index)]
        self.compositeShapesDropDown = wx.Choice(self, choices=self.compositeShapes)
        self._AppendControl(sizer, 'shape', self.compositeShapesDropDown)
        self.compositeShapesDropDown.Bind(wx.EVT_CHOICE, self.OnCompositeShapes)
 
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
                if node.id == new_id:
                    self._SetValidationState(False, ctrl_id, "Not saved: Duplicate ID")
                    return
            else:
                # loop terminated fine. There is no duplicate ID
                self._self_changes = True
                self.controller.start_group()
                self.controller.rename_node(self.net_index, nodei, new_id)
                post_event(DidModifyNodesEvent([nodei]))
                self.controller.end_group()
        self._SetValidationState(True, self.id_ctrl.GetId())

    def _OnPosText(self, evt):
        """Callback for the position control."""
        assert self.contiguous
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
        # limit position to within the compartment
        compi = nodes[0].comp_idx
        if compi == -1:
            bounds = Rect(Vec2(), self.canvas.realsize)
        else:
            comp = self.canvas.comp_idx_map[compi]
            bounds = Rect(comp.position, comp.size)
        clamped = None
        index_list = list(self.selected_idx)
        if len(nodes) == 1:
            [node] = nodes
            clamped = clamp_rect_pos(Rect(pos, node.size), bounds)
            if node.position != clamped or pos != clamped:
                self._self_changes = True
                node.position = clamped
                self.controller.start_group()
                post_event(DidMoveNodesEvent(index_list, clamped - node.position, dragged=False))
                self.controller.move_node(self.net_index, node.index, node.position)
                self.controller.end_group()
        else:
            clamped = clamp_rect_pos(Rect(pos, self._bounding_rect.size), bounds)
            if self._bounding_rect.position != pos or pos != clamped:
                offset = clamped - self._bounding_rect.position
                self._self_changes = True
                self.controller.start_group()
                for node in nodes:
                    node.position += offset
                post_event(DidMoveNodesEvent(index_list, offset, dragged=False))
                for node in nodes:
                    self.controller.move_node(self.net_index, node.index, node.position)
                self.controller.end_group()
        self._SetValidationState(True, self.pos_ctrl.GetId())

    def _OnSizeText(self, evt):
        """Callback for the size control."""
        assert self.contiguous
        ctrl_id = self.size_ctrl.GetId()
        text = evt.GetString()
        wh = parse_num_pair(text)
        if wh is None:
            self._SetValidationState(False, ctrl_id, 'Should be in the form "width, height"')
            return

        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
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
            self._SetValidationState(False, ctrl_id, message)
            return

        # if size.x > max_size.x or size.y > max_size.y:
        #     message = 'The size of bounding box cannot exceed ({}, {})'.format(
        #         no_rzeros(max_size.x, 2), no_rzeros(max_size.y, 2))
        #     self._SetValidationState(False, ctrl_id, message)
        #     return

        # NOTE clamp max size automatically rather than show error
        clamped = size.reduce2(min, bounds.size)
        if self._bounding_rect.size != clamped or size != clamped:
            ratio = clamped.elem_div(self._bounding_rect.size)
            self._self_changes = True
            self.controller.start_group()
            offsets = list()
            for node in nodes:
                rel_pos = node.position - self._bounding_rect.position
                new_pos = self._bounding_rect.position + rel_pos.elem_mul(ratio)
                offsets.append(new_pos - node.position)
                node.position = new_pos
                node.size = node.size.elem_mul(ratio)
                # clamp so that nodes are always within compartment/bounds
                node.position = clamp_rect_pos(node.rect, bounds)

            idx_list = list(self.selected_idx)
            post_event(DidMoveNodesEvent(idx_list, offsets, dragged=False))
            post_event(DidResizeNodesEvent(idx_list, ratio=ratio, dragged=False))
            for node in nodes:
                self.controller.move_node(self.net_index, node.index, node.position)
                self.controller.set_node_size(self.net_index, node.index, node.size)
            self.controller.end_group()
        self._SetValidationState(True, self.size_ctrl.GetId())

    def OnNodeStatusChoice(self, evt):    
        """Callback for the change node status, floating or boundary."""
        selected = self.nodeStatusDropDown.GetSelection()
        if selected == 0:
           floatingStatus = True
        else:
           floatingStatus = False 

        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        self._self_changes = True
        self.controller.start_group()
        for node in nodes:
            self.controller.set_node_floating_status(self.net_index, node.index, floatingStatus)
        post_event(DidModifyNodesEvent(list(self._selected_idx)))
        self.controller.end_group()

    def OnCompositeShapes(self, evt):
        selected = self.compositeShapesDropDown.GetStringSelection()

        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        shapes = self.controller.get_composite_shape_list(self.net_index)
        self._self_changes = True
        self.controller.start_group()
        for node in nodes:
            for shapei, shape in enumerate(self.compositeShapes):
                if selected == shape:
                    self.controller.set_node_shape_index(self.net_index, node.index, shapei)
            
        post_event(DidModifyNodesEvent(list(self._selected_idx)))
        self.controller.end_group()

        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        shapes = [n.composite_shape for n in nodes]
        self._UpdatePrimitiveFields(shapes, nodes)

    def OnNodeLockCheckBox(self, evt):
        """Callback for the change node status, floating or boundary."""
        cb = evt.GetEventObject() 
        if cb.GetValue():
             nodeLocked = True
        else:
             nodeLocked= False

        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        self._self_changes = True
        self.controller.start_group()
        for node in nodes:
            self.controller.set_node_locked_status(self.net_index, node.index, nodeLocked)
        post_event(DidModifyNodesEvent(list(self._selected_idx)))
        self.controller.end_group()  

    def _ColorPrimitiveControl(self, label: str, alpha_label: str, prop_name: str,
                                prims: List[TPrimitive], prim_index: int, node_indices: List[int]):
        '''Create a control for a color property.

        If prim_index is -1, then update the text primitive instead.
        '''
        old_colors = [getattr(p, prop_name).to_wxcolour() for p in prims]

        def color_callback(value: wx.Colour):
            self._self_changes = True
            self.controller.start_group()
            for i, nodei in enumerate(node_indices):
                # only update the RGB, not alpha
                old_color = old_colors[i]
                new_color = Color(value.Red(), value.Green(), value.Blue(), old_color.Alpha())
                self.controller.set_node_primitive_property(self.net_index, nodei, prim_index,
                                                            prop_name, new_color)
            self.controller.end_group()

        def alpha_callback(value: float):
            self._self_changes = True
            self.controller.start_group()
            for i, nodei in enumerate(node_indices):
                old_color = old_colors[i]
                new_color = Color(old_color.Red(), old_color.Green(), old_color.Blue(), int(255 * value))
                self.controller.set_node_primitive_property(self.net_index, nodei, prim_index,
                                                            prop_name, new_color)
            self.controller.end_group()

        color_union, alpha_union = self._GetMultiColor(old_colors)
        self._CreateColorControl(label, alpha_label, color_callback, alpha_callback, 
                                 self.GetSizer(), placeholder=color_union,
                                 placeholder_alpha=alpha_union)

    def _FloatPrimitiveControl(self, label: str, prop_name: str, prims: List[TPrimitive],
                               prim_index: int, node_indices: List[int]):
        '''Create a control for a floating point property.

        If prim_index is -1, then update the text primitive instead.
        '''
        old_values = [getattr(p, prop_name) for p in prims]
        for val in old_values:
            assert isinstance(val, float) or isinstance(val, int)

        placeholder_value = self._GetMultiFloatText(set(old_values), 2)

        def callback(value: float):
            self._self_changes = True
            self.controller.start_group()
            for nodei in node_indices:
                # only update the RGB, not alpha
                self.controller.set_node_primitive_property(self.net_index, nodei, prim_index,
                                                            prop_name, value)
            self.controller.end_group()
            
        sizer = self.GetSizer()
        text_ctrl = self.CreateTextCtrl()
        outer_callback = self._MakeFloatCtrlFunction(text_ctrl.GetId(),
                                                     callback, (0, None), left_incl=False)
        text_ctrl.ChangeValue(placeholder_value)
        text_ctrl.Bind(wx.EVT_TEXT, outer_callback)
        self._AppendControl(sizer, label, text_ctrl)

    def _IntPrimitiveControl(self, label: str, prop_name: str, prims: List[TPrimitive],
                             prim_index: int, node_indices: List[int], min_=0, max_=100):
        '''Create a control for a floating point property.

        If prim_index is -1, then update the text primitive instead.
        '''
        old_values = [getattr(p, prop_name) for p in prims]
        for val in old_values:
            assert isinstance(val, float) or isinstance(val, int)

        def callback(e):
            value = e.GetPosition()
            self._self_changes = True
            self.controller.start_group()
            for nodei in node_indices:
                # only update the RGB, not alpha
                self.controller.set_node_primitive_property(self.net_index, nodei, prim_index,
                                                            prop_name, value)
            self.controller.end_group()
            
        initial_value = self._GetMultiInt(set(old_values)) or 0
        sizer = self.GetSizer()
        int_ctrl = self.CreateSpinCtrl(min=min_, max=max_, initial=initial_value)
        int_ctrl.Bind(wx.EVT_SPINCTRL, callback)
        self._AppendControl(sizer, label, int_ctrl)

    def _ChoicePrimitiveControl(self, label: str, prop_name: str, prims: List[TPrimitive],
                                prim_index: int, node_indices: List[int],
                                choice_items: List[ChoiceItem]):
        # TODO set original value
        def callback(e):
            index = e.GetInt()
            value = choice_items[index].value
            self._self_changes = True
            self.controller.start_group()
            for nodei in node_indices:
                self.controller.set_node_primitive_property(self.net_index, nodei, prim_index,
                                                            prop_name, value)
            self.controller.end_group()

        old_values = set(getattr(prim, prop_name) for prim in prims)

        sizer = self.GetSizer()
        texts = [item.text for item in choice_items]
        choice_ctrl = wx.Choice(self, choices=texts)

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

        choice_ctrl.Bind(wx.EVT_CHOICE, callback)
        self._AppendControl(sizer, label, choice_ctrl)

    def _UpdatePrimitiveFields(self, com_shapes: List[TCompositeShape], nodes: List[Node]):
        sizer = self.GetSizer()

        self.Freeze()

        if self.primitives_start_row:
            start_row = self.primitives_start_row - 1

            index = 0
            while index < sizer.GetItemCount():
                pos = sizer.GetItemPosition(index)
                if pos.GetRow() >= start_row:
                    item = sizer.GetItem(index)
                    if item.IsWindow():
                        window = item.GetWindow()
                        winid = window.GetId()
                        if winid in self.badges:
                            del self.badges[winid]
                            del self.labels[winid]
                        item.GetWindow().Destroy()
                    else:
                        sizer.Remove(index)
                else:
                    index += 1

            # reset rows
            sizer.SetRows(start_row)

        if len(com_shapes) != 0:
            # self._primitives_heading = self._AppendSubtitle(sizer, 'Shape properties')
            self._AppendSpacer(sizer, 0)
            self.primitives_start_row = self.GetSizer().GetRows()
            node_indices = [n.index for n in nodes]
            for prim_index in range(len(com_shapes[0].items)):
                primitives = [cs.items[prim_index][0] for cs in com_shapes]
                one_prim = primitives[0]
                subtitle_text = '{name} ({idx})'.format(idx=prim_index + 1, name=one_prim.name)
                self._AppendSubtitle(sizer, subtitle_text)
                if isinstance(one_prim, TRectanglePrim):
                    self._ColorPrimitiveControl('fill color', 'fill opacity', 'fill_color',
                                                primitives, prim_index, node_indices)
                    self._ColorPrimitiveControl('border color', 'border opacity', 'border_color',
                                                primitives, prim_index, node_indices)
                    self._FloatPrimitiveControl('border width', 'border_width',
                                                primitives, prim_index, node_indices)
                    self._FloatPrimitiveControl('corner radius', 'corner_radius',
                                                primitives, prim_index, node_indices)
                elif isinstance(one_prim, TCirclePrim):
                    self._ColorPrimitiveControl('fill color', 'fill opacity', 'fill_color',
                                                primitives, prim_index, node_indices)
                    self._ColorPrimitiveControl('border color', 'border opacity', 'border_color',
                                                primitives, prim_index, node_indices)
                    self._FloatPrimitiveControl('border width', 'border_width',
                                                primitives, prim_index, node_indices)
            subtitle_text = 'Text'
            self._AppendSubtitle(sizer, subtitle_text)
            # Create text primitive
            primitives = [cast(TPrimitive, cs.text_item[0]) for cs in com_shapes]
            self._IntPrimitiveControl('font size', 'font_size', primitives, -1, node_indices, min_=1, max_=100)
            self._ColorPrimitiveControl('font color', 'font opacity', 'font_color',
                                        primitives, -1, node_indices)
            self._ColorPrimitiveControl('highlight color', 'highlight opacity', 'bg_color',
                                        primitives, -1, node_indices)
            self._ChoicePrimitiveControl('font family', 'font_family', primitives, -1,
                                         node_indices, FONT_FAMILY_CHOICES)

        else:
            self.primitives_start_row = None

        self.Layout()
        self.Thaw()

    def UpdateAllFields(self):
        """Update the form field values based on current data."""
        self._self_changes = False
        assert len(self._selected_idx) != 0
        nodes = get_nodes_by_idx(self._nodes, self._selected_idx)
        prec = get_setting('decimal_precision')
        id_text: str
        floatingNode: bool
        lockNode: bool
        shape_name: str

        if not self.contiguous:
            self.pos_ctrl.ChangeValue('?')
            self.size_ctrl.ChangeValue('?')
        else:
            self._ChangePairValue(self.pos_ctrl, self._bounding_rect.position, prec)
            self._ChangePairValue(self.size_ctrl, self._bounding_rect.size, prec)

        if len(self._selected_idx) == 1:
            [node] = nodes
            self.id_ctrl.Enable(True)
            id_text = node.id
            floatingNode = node.floatingNode
            lockNode = node.lockNode
            assert node.composite_shape is not None
            shape_name = node.composite_shape.name
        else:
            self.id_ctrl.Enable(False)
            id_text = '; '.join(sorted(list(n.id for n in nodes)))

            floatingNode = all(n.floatingNode for n in nodes)
            lockNode = all(n.lockNode for n in nodes)
            shape_name_set = set(n.composite_shape.name for n in nodes)
            if len(shape_name_set) == 1:
                shape_name = next(iter(shape_name_set))
            else:
                shape_name = ''

        shapes = [n.composite_shape for n in nodes]
        num_distinct_shapes = len(set(s.name for s in shapes))
        if num_distinct_shapes == 1:
            self._UpdatePrimitiveFields(shapes, nodes)
        else:
            self._UpdatePrimitiveFields([], nodes)
        self.pos_ctrl.Enable(self.contiguous)
        self.size_ctrl.Enable(self.contiguous)

        self.id_ctrl.ChangeValue(id_text)

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
            self.compositeShapesDropDown.SetSelection(NOT_FOUND)

@dataclass
class StoichInfo:
    """Helper class that stores node stoichiometry info for reaction form"""
    nodei: int
    stoich: float


class ReactionForm(EditPanelForm):
    def __init__(self, parent, canvas: Canvas, controller: IController):
        super().__init__(parent, canvas, controller)

        self._reactions = list()
        self.InitLayout()

    def CreateControls(self, sizer: wx.GridSizer):
        self.id_ctrl = self.CreateTextCtrl()
        self.id_ctrl.Bind(wx.EVT_TEXT, self._OnIdText)
        self._AppendControl(sizer, 'identifier', self.id_ctrl)

        self.ratelaw_ctrl = self.CreateTextCtrl()
        self.ratelaw_ctrl.Bind(wx.EVT_TEXT, self._OnRateLawText)
        self._AppendControl(sizer, 'rate law', self.ratelaw_ctrl)

        self.fill_ctrl, self.fill_alpha_ctrl = self._CreateColorControl(
            'fill color', 'fill opacity',
            self._OnFillColorChanged, self._FillAlphaCallback, sizer)

        self.stroke_width_ctrl = self.CreateTextCtrl()
        stroke_cb = self._MakeFloatCtrlFunction(self.stroke_width_ctrl.GetId(),
                                                self._StrokeWidthCallback, (0.1, 100))
        self.stroke_width_ctrl.Bind(wx.EVT_TEXT, stroke_cb)
        self._AppendControl(sizer, 'line width', self.stroke_width_ctrl)

        # Whether the center position should be autoly set?
        self.auto_center_ctrl = wx.CheckBox(self)
        self.auto_center_ctrl.SetValue(True)
        self.auto_center_ctrl.Bind(wx.EVT_CHECKBOX, self._AutoCenterCallback)
        self._AppendControl(sizer, 'auto center pos', self.auto_center_ctrl)

        self.center_pos_ctrl = self.CreateTextCtrl()
        self.center_pos_ctrl.Disable()
        self.center_pos_ctrl.Bind(wx.EVT_TEXT, self._CenterPosCallback)
        self._AppendControl(sizer, 'center position', self.center_pos_ctrl)

        self._reactant_subtitle = None
        self._product_subtitle = None
        self.reactant_stoich_ctrls = list()
        self.product_stoich_ctrls = list()

        states = ['bezier curve', 'straight line'] 
        self.rxnStatusDropDown = wx.Choice(self, choices=states)
        self._AppendControl(sizer, 'reaction status', self.rxnStatusDropDown)
        self.rxnStatusDropDown.Bind(wx.EVT_CHOICE, self.OnRxnStatusChoice)

        self.mod_tip_dropdown = wx.ComboBox(self, choices=[e.value for e in ModifierTipStyle], style=wx.CB_READONLY)
        self._AppendControl(sizer, 'modifier tip', self.mod_tip_dropdown)
        self.mod_tip_dropdown.Bind(wx.EVT_COMBOBOX, self.ModifierTipCallback)

        self._modifiers = set()
        self._nodes = list()
        self._node_indices = set()
        self.modifiers_ctrl = wx.CheckListBox(self, style=wx.LB_NEEDED_SB, size=(-1, 100))
        self._AppendControl(sizer, 'modifiers', self.modifiers_ctrl)
        self.modifiers_ctrl.Bind(wx.EVT_CHECKLISTBOX, self.OnModifierCheck)

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
                if rxn.id == new_id:
                    self._SetValidationState(False, ctrl_id, "Not saved: Duplicate ID")
                    return

            # loop terminated fine. There is no duplicate ID
            self._self_changes = True
            self.controller.start_group()
            self.controller.rename_reaction(self.net_index, reai, new_id)
            post_event(DidModifyReactionEvent(list(self._selected_idx)))
            self.controller.end_group()
            self._SetValidationState(True, ctrl_id)

    def _StrokeWidthCallback(self, width: float):
        reactions = [r for r in self._reactions if r.index in self._selected_idx]
        self._self_changes = True
        self.controller.start_group()
        for rxn in reactions:
            self.controller.set_reaction_line_thickness(self.net_index, rxn.index, width)
        post_event(DidModifyReactionEvent(list(self._selected_idx)))
        self.controller.end_group()

    def  OnRxnStatusChoice (self, evt):    
        """Callback for the change reaction status, bezier curve or straight line."""
        selection = self.rxnStatusDropDown.GetSelection()
        # TODO this is hardcoded. If the text changes this wouldn't work
        if selection == 0:
           bezierCurves = True
        else:
           bezierCurves = False 

        rxns = get_rxns_by_idx(self._reactions, self._selected_idx)
        self._self_changes = True
        self.controller.start_group()
        for rxn in rxns:
            self.controller.set_reaction_bezier_curves(self.net_index, rxn.index, bezierCurves)
        post_event(DidModifyReactionEvent(list(self._selected_idx)))
        self.controller.end_group()

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

        rxns = get_rxns_by_idx(self._reactions, self._selected_idx)
        self._self_changes = True
        self.controller.start_group()
        for rxn in rxns:
            self.controller.set_modifier_tip_style(self.net_index, rxn.index, entry)
        post_event(DidModifyReactionEvent(list(self._selected_idx)))
        self.controller.end_group()

    def _AutoCenterCallback(self, evt):
        checked = evt.GetInt()
        assert len(self._selected_idx) == 1
        prec = 2
        reaction = self.canvas.reaction_idx_map[next(iter(self._selected_idx))]
        centroid_map = self.canvas.GetReactionCentroids(self.net_index)
        centroid = centroid_map[reaction.index]
        if checked:
            self.center_pos_ctrl.Disable()
            self.center_pos_ctrl.ChangeValue('')
            self.controller.start_group()
            self.controller.set_reaction_center(self.net_index, reaction.index, None)
            # Move centroid handle along if centroid changed.
            if reaction.center_pos is not None:
                offset = centroid - reaction.center_pos
                if offset != Vec2():
                    self.controller.set_center_handle(self.net_index, reaction.index, reaction.src_c_handle.tip + offset)
            self.controller.end_group()
            self.center_pos_ctrl.Disable()
        else:
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
            self._SetValidationState(False, ctrl_id, 'Should be in the form "X, Y"')
            return

        pos = Vec2(xy)
        if pos.x < 0 or pos.y < 0:
            self._SetValidationState(False, ctrl_id, 'Position coordinates should be non-negative')
            return
        
        assert len(self._selected_idx) == 1
        reaction = self.canvas.reaction_idx_map[next(iter(self._selected_idx))]
        if reaction.center_pos != pos:
            offset = pos - reaction.center_pos
            self._self_changes = True
            self.controller.start_group()
            self.controller.set_reaction_center(self.net_index, reaction.index, pos)
            post_event(DidMoveReactionCenterEvent(self.net_index, reaction.index, offset, False))
            self.controller.end_group()
        self._SetValidationState(True, ctrl_id)

    def _OnFillColorChanged(self, fill: wx.Colour):
        """Callback for the fill color control."""
        reactions = [r for r in self._reactions if r.index in self._selected_idx]
        self._self_changes = True
        self.controller.start_group()
        for rxn in reactions:
            if on_msw():
                self.controller.set_reaction_fill_rgb(self.net_index, rxn.index, fill)
            else:
                # we can set both the RGB and the alpha at the same time
                self.controller.set_reaction_fill_rgb(self.net_index, rxn.index, fill)
                self.controller.set_reaction_fill_alpha(self.net_index, rxn.index, fill.Alpha())
        post_event(DidModifyReactionEvent(list(self._selected_idx)))
        self.controller.end_group()

    def _FillAlphaCallback(self, alpha: float):
        """Callback for when the fill alpha changes."""
        reactions = (r for r in self._reactions if r.index in self._selected_idx)
        self._self_changes = True
        self.controller.start_group()
        for rxn in reactions:
            self.controller.set_reaction_fill_alpha(self.net_index, rxn.index, int(alpha * 255))
        post_event(DidModifyReactionEvent(list(self._selected_idx)))
        self.controller.end_group()

    def _OnRateLawText(self, evt: wx.CommandEvent):
        ratelaw = evt.GetString()
        assert len(self._selected_idx) == 1, 'Reaction rate law field should be disabled when ' + \
            'multiple are selected'
        [reai] = self._selected_idx
        self._self_changes = True
        post_event(DidModifyReactionEvent(list(self._selected_idx)))
        self.controller.set_reaction_ratelaw(self.net_index, reai, ratelaw)

    def OnModifierCheck(self, evt: wx.CommandEvent):
        assert len(self._selected_idx) == 1
        reactions = [r for r in self._reactions if r.index in self._selected_idx]
        reaction = reactions[0]
        new_modifiers = [self._nodes[i].index for i in self.modifiers_ctrl.GetCheckedItems()]
        self.controller.set_reaction_modifiers(self.net_index, reaction.index, new_modifiers)

    def CanvasUpdated(self, reactions: List[Reaction], nodes: List[Node]):
        """Function called after the canvas has been updated."""
        self._reactions = reactions
        self._nodes = nodes
        new_node_indices = set(n.index for n in nodes)
        # if new_node_indices != self._node_indices:
        self._node_indices = new_node_indices
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
            self.labels[self.id_ctrl.GetId()].SetLabel(id_text)
            self.UpdateAllFields()
        self.ExternalUpdate()

    def _UpdateModifierList(self):
        # NOTE if slightly better performance is wanted, we don't have to update this widget
        # immediately. Rather we can have a dirty flag and update only when displaying
        self.modifiers_ctrl.Set([n.id for n in self._nodes])
        checked_indices = set(i for i, n in enumerate(self._nodes) if n.index in self._modifiers)
        self._UpdateModifierSelection(checked_indices)

    def _UpdateModifierSelection(self, new_modifiers: Set[int]):
        self._modifiers = new_modifiers
        self.modifiers_ctrl.SetCheckedItems(new_modifiers)

    def _UpdateStoichFields(self, reai: int, reactants: List[StoichInfo], products: List[StoichInfo]):
        sizer = self.GetSizer()

        self.Freeze()
        if self._reactant_subtitle is not None:
            start_row = sizer.GetItemPosition(self._reactant_subtitle).GetRow() - 2

            index = 0
            while index < sizer.GetItemCount():
                pos = sizer.GetItemPosition(index)
                if pos.GetRow() >= start_row:
                    item = sizer.GetItem(index)
                    if item.IsWindow():
                        window = item.GetWindow()
                        winid = window.GetId()
                        if winid in self.badges:
                            del self.badges[winid]
                            del self.labels[winid]
                        item.GetWindow().Destroy()
                    else:
                        sizer.Remove(index)
                else:
                    index += 1

            self._reactant_subtitle = None
            self._product_subtitle = None
            # reset rows
            sizer.SetRows(start_row)

        if len(reactants) != 0:
            # add back the fields
            self._reactant_subtitle = self._AppendSubtitle(sizer, 'Reactants')
            for stoich in reactants:
                stoich_ctrl = self.CreateTextCtrl(value=no_rzeros(stoich.stoich, precision=2))
                node_id = self.controller.get_node_id(self.net_index, stoich.nodei)
                self._AppendControl(sizer, node_id, stoich_ctrl)
                inner_callback = self._MakeSetSrcStoichFunction(reai, stoich.nodei)
                callback = self._MakeFloatCtrlFunction(stoich_ctrl.GetId(), inner_callback, (0, None),
                                                       left_incl=False)
                stoich_ctrl.Bind(wx.EVT_TEXT, callback)

            self._product_subtitle = self._AppendSubtitle(sizer, 'Products')
            for stoich in products:
                stoich_ctrl = self.CreateTextCtrl(value=no_rzeros(stoich.stoich, precision=2))
                node_id = self.controller.get_node_id(self.net_index, stoich.nodei)
                self._AppendControl(sizer, node_id, stoich_ctrl)
                inner_callback = self._MakeSetDestStoichFunction(reai, stoich.nodei)
                callback = self._MakeFloatCtrlFunction(
                    stoich_ctrl.GetId(), inner_callback, (0, None), left_incl=False)
                stoich_ctrl.Bind(wx.EVT_TEXT, callback)

        self.Layout()
        self.Thaw()

    def _MakeSetSrcStoichFunction(self, reai: int, nodei: int):
        def ret(val: float):
            self._self_changes = True
            self.controller.start_group()
            self.controller.set_src_node_stoich(self.net_index, reai, nodei, val)
            post_event(DidModifyReactionEvent(list(self._selected_idx)))
            self.controller.end_group()

        return ret

    def _MakeSetDestStoichFunction(self, reai: int, nodei: int):
        def ret(val: float):
            self.controller.start_group()
            self._self_changes = True
            self.controller.set_dest_node_stoich(self.net_index, reai, nodei, val)
            post_event(DidModifyReactionEvent(list(self._selected_idx)))
            self.controller.end_group()

        return ret

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
        self._self_changes = False
        assert len(self._selected_idx) != 0
        reactions = [r for r in self._reactions if r.index in self._selected_idx]
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
            self.ratelaw_ctrl.Enable()
            self.auto_center_ctrl.Enable()
            auto_set = reaction.center_pos is None
            self.auto_center_ctrl.SetValue(auto_set)
            self.center_pos_ctrl.Enable(not auto_set)

            self._UpdateStoichFields(reai, self._GetSrcStoichs(reai), self._GetDestStoichs(reai))
            self.modifiers_ctrl.Enable()
            self._UpdateModifierSelection(reaction.modifiers)
        else:
            self.id_ctrl.Disable()
            fill, fill_alpha = self._GetMultiColor(list(r.fill_color for r in reactions))
            ratelaw_text = 'multiple'
            self.ratelaw_ctrl.Disable()
            self.auto_center_ctrl.Disable()
            self.center_pos_ctrl.Disable()
            self._UpdateStoichFields(0, [], [])
            self.modifiers_ctrl.Disable()
            self._UpdateModifierSelection(set())

        bezierCurves = all(r.bezierCurves for r in reactions)
        mod_tip_style = self._GetMultiEnum(list(r.modifier_tip_style for r in reactions), ModifierTipStyle.CIRCLE)
        stroke_width = self._GetMultiFloatText(set(r.thickness for r in reactions), prec)

        self.id_ctrl.ChangeValue(id_text)
        self.fill_ctrl.SetColour(fill)
        self.ratelaw_ctrl.ChangeValue(ratelaw_text)
        self.stroke_width_ctrl.ChangeValue(stroke_width)
        self.mod_tip_dropdown.SetValue(mod_tip_style.value)

        if on_msw():
            self.fill_alpha_ctrl.ChangeValue(self._AlphaToText(fill_alpha, prec))
         
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
        self._compartments = list()
        self.contiguous = True

        self.InitLayout()

    def CreateControls(self, sizer: wx.GridSizer):
        self.id_ctrl = self.CreateTextCtrl()
        self.id_ctrl.Bind(wx.EVT_TEXT, self._OnIdText)
        self._AppendControl(sizer, 'identifier', self.id_ctrl)

        self.pos_ctrl = self.CreateTextCtrl()
        self.pos_ctrl.Bind(wx.EVT_TEXT, self._OnPosText)
        self._AppendControl(sizer, 'position', self.pos_ctrl)

        self.size_ctrl = self.CreateTextCtrl()
        self.size_ctrl.Bind(wx.EVT_TEXT, self._OnSizeText)
        self._AppendControl(sizer, 'size', self.size_ctrl)

        self.volume_ctrl = self.CreateTextCtrl()
        self._AppendControl(sizer, 'volume', self.volume_ctrl)
        volume_callback = self._MakeFloatCtrlFunction(self.volume_ctrl.GetId(),
                                                      self._VolumeCallback, (0, None), left_incl=False)
        self.volume_ctrl.Bind(wx.EVT_TEXT, volume_callback)

        self.fill_ctrl, self.fill_alpha_ctrl = self._CreateColorControl(
            'fill color', 'fill opacity',
            self._OnFillColorChanged, self._FillAlphaCallback,
            sizer)

        self.border_ctrl, self.border_alpha_ctrl = self._CreateColorControl(
            'border color', 'border opacity',
            self._OnBorderColorChanged, self._BorderAlphaCallback,
            sizer)

        self.border_width_ctrl = self.CreateTextCtrl()
        self._AppendControl(sizer, 'border width', self.border_width_ctrl)
        border_callback = self._MakeFloatCtrlFunction(self.border_width_ctrl.GetId(),
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
            self._SetValidationState(False, ctrl_id, "ID cannot be empty")
            return
        else:
            for comp in self._compartments:
                if comp.id == new_id:
                    self._SetValidationState(False, ctrl_id, "Not saved: Duplicate ID")
                    return

            # loop terminated fine. There is no duplicate ID
            self._self_changes = True
            self.controller.start_group()
            self.controller.rename_compartment(self.net_index, compi, new_id)
            post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))
            self.controller.end_group()
            self._SetValidationState(True, ctrl_id)

    def _OnPosText(self, evt):
        """Callback for the position control."""
        assert self.contiguous
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
        comps = [c for c in self._compartments if c.index in self.selected_idx]
        bounds = Rect(Vec2(), self.canvas.realsize)
        clamped = clamp_rect_pos(Rect(pos, self._bounding_rect.size), bounds)
        if self._bounding_rect.position != pos or pos != clamped:
            offset = clamped - self._bounding_rect.position
            self._self_changes = True
            self.controller.start_group()
            for comp in comps:
                comp.position += offset
            post_event(DidMoveCompartmentsEvent(list(self.selected_idx), offset, dragged=False))
            for comp in comps:
                self.controller.move_node(self.net_index, comp.index, comp.position)
            self.controller.end_group()
        self._SetValidationState(True, self.pos_ctrl.GetId())

    def _OnSizeText(self, evt):
        """Callback for the size control."""
        ctrl_id = self.size_ctrl.GetId()
        text = evt.GetString()
        wh = parse_num_pair(text)
        if wh is None:
            self._SetValidationState(False, ctrl_id, 'Should be in the form "width, height"')
            return

        comps = [c for c in self._compartments if c.index in self.selected_idx]
        size = Vec2(wh)
        _, comp_min_ratio = self.canvas.select_box.compute_min_ratio()
        assert comp_min_ratio is not None
        limit = self._bounding_rect.size.elem_mul(comp_min_ratio)

        if size.x < limit.x or size.y < limit.y:
            message = 'Size of {} needs to be at least ({}, {})'.format(
                'bounding box' if len(comps) > 1 else 'compartment',
                no_rzeros(limit.x, 2), no_rzeros(limit.y, 2))
            self._SetValidationState(False, ctrl_id, message)
            return

        clamped = clamp_rect_size(Rect(self._bounding_rect.position, size), self.canvas.realsize)
        if self._bounding_rect.size != clamped or size != clamped:
            ratio = clamped.elem_div(self._bounding_rect.size)
            self._self_changes = True
            self.controller.start_group()

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

            idx_list = list(self.selected_idx)
            post_event(DidMoveCompartmentsEvent(idx_list, offsets, dragged=False))
            post_event(DidResizeCompartmentsEvent(idx_list, ratio, dragged=False))
            if len(peripheral_nodes) != 0:
                post_event(DidMoveNodesEvent(peripheral_nodes, peripheral_offsets, dragged=False))
            for comp in comps:
                self.controller.move_compartment(self.net_index, comp.index, comp.position)
                self.controller.set_compartment_size(self.net_index, comp.index, comp.size)

            for node in peripheral_nodes:
                self.controller.move_node(self.net_index, node.index, node.position)
            self.controller.end_group()
        self._SetValidationState(True, self.size_ctrl.GetId())

    def _VolumeCallback(self, volume: float):
        """Callback for when the border width changes."""
        comps = [c for c in self._compartments if c.index in self.selected_idx]
        self._self_changes = True
        self.controller.start_group()
        for comp in comps:
            self.controller.set_compartment_volume(self.net_index, comp.index, volume)
        post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))
        self.controller.end_group()

    def _OnFillColorChanged(self, fill: wx.Colour):
        """Callback for the fill color control."""
        comps = [c for c in self._compartments if c.index in self.selected_idx]
        self._self_changes = True
        self.controller.start_group()
        for comp in comps:
            if on_msw():
                fill = wx.Colour(fill.GetRGB())  # remove alpha channel
            self.controller.set_compartment_fill(self.net_index, comp.index, fill)
        post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))
        self.controller.end_group()

    def _OnBorderColorChanged(self, border: wx.Colour):
        """Callback for the border color control."""
        comps = [c for c in self._compartments if c.index in self.selected_idx]
        self._self_changes = True
        self.controller.start_group()
        for comp in comps:
            if on_msw():
                border = wx.Colour(border.GetRGB())  # remove alpha channel
            self.controller.set_compartment_border(self.net_index, comp.index, border)
        post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))
        self.controller.end_group()

    def _FillAlphaCallback(self, alpha: float):
        """Callback for when the fill alpha changes."""
        comps = [c for c in self._compartments if c.index in self.selected_idx]
        self._self_changes = True
        self.controller.start_group()
        for comp in comps:
            new_fill = change_opacity(comp.fill, int(alpha * 255))
            self.controller.set_compartment_fill(self.net_index, comp.index, new_fill)
        post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))
        self.controller.end_group()

    def _BorderAlphaCallback(self, alpha: float):
        """Callback for when the border alpha changes."""
        comps = [c for c in self._compartments if c.index in self.selected_idx]
        self._self_changes = True
        self.controller.start_group()
        for comp in comps:
            new_border = change_opacity(comp.border, int(alpha * 255))
            self.controller.set_compartment_border(self.net_index, comp.index, new_border)
        post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))
        self.controller.end_group()

    def _BorderWidthCallback(self, width: float):
        """Callback for when the border width changes."""
        comps = [c for c in self._compartments if c.index in self.selected_idx]
        self._self_changes = True
        self.controller.start_group()
        for comp in comps:
            self.controller.set_compartment_border_width(self.net_index, comp.index, width)
        post_event(DidModifyCompartmentsEvent(list(self._selected_idx)))
        self.controller.end_group()

    def UpdateCompartments(self, comps: List[Compartment]):
        self._compartments = comps
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
            self.labels[self.id_ctrl.GetId()].SetLabel(id_text)
        self.ExternalUpdate()

    def UpdateAllFields(self):
        self._self_changes = False
        comps = [c for c in self._compartments if c.index in self.selected_idx]
        assert len(comps) == len(self.selected_idx)
        prec = 2

        id_text = '; '.join([c.id for c in comps])
        fill: wx.Colour
        fill_alpha: Optional[int]
        border: wx.Colour

        self.pos_ctrl.Enable(self.contiguous)
        self.size_ctrl.Enable(self.contiguous)
        border_width = self._GetMultiFloatText(set(c.border_width for c in comps), prec)
        volume = self._GetMultiFloatText(set(c.volume for c in comps), prec)

        if not self.contiguous:
            self.pos_ctrl.ChangeValue('?')
            self.size_ctrl.ChangeValue('?')
        else:
            self._ChangePairValue(self.pos_ctrl, self._bounding_rect.position, prec)
            self._ChangePairValue(self.size_ctrl, self._bounding_rect.size, prec)

        if len(self._selected_idx) == 1:
            [comp] = comps
            self.id_ctrl.Enable()
            fill = comp.fill
            fill_alpha = comp.fill.Alpha()
            border = comp.border
            border_alpha = comp.border.Alpha()
        else:
            self.id_ctrl.Disable()
            fill, fill_alpha = self._GetMultiColor(list(c.fill for c in comps))
            border, border_alpha = self._GetMultiColor(list(c.border for c in comps))

        self.id_ctrl.ChangeValue(id_text)
        self.fill_ctrl.SetColour(fill)
        self.border_ctrl.SetColour(border)
        self.volume_ctrl.ChangeValue(volume)

        # set fill alpha if on windows
        if on_msw():
            self.fill_alpha_ctrl.ChangeValue(self._AlphaToText(fill_alpha, prec))
            self.border_alpha_ctrl.ChangeValue(self._AlphaToText(border_alpha, prec))

        self.border_width_ctrl.ChangeValue(border_width)


    def CompsMovedOrResized(self, evt):
        """Called when nodes are moved or resized by dragging"""
        if not evt.dragged:
            return
        self._UpdateBoundingRect()
        prec = 2
        self._ChangePairValue(self.pos_ctrl, self._bounding_rect.position, prec)
        self._ChangePairValue(self.size_ctrl, self._bounding_rect.size, prec)

    def _UpdateBoundingRect(self):
        """Update bounding rectangle; mixed indicates whether both nodes and comps are selected.
        """
        rects = [c.rect for c in self._compartments if c.index in self.selected_idx]
        # It could be that compartments have been updated but selected indices have not.
        # In that case rects can be empty
        if len(rects) != 0:
            self._bounding_rect = get_bounding_rect(rects)
