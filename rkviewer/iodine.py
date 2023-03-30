"""
Iodine Network Object Model.

Original author:    RJ Zhou
"Forked" from:      https://github.com/zrj26/go-NOM
Adapted by:         Gary Geng

TODOs
    * Phase out errCode, or at least provide more detalis in error messages.
"""
# from __future__ import annotations
import abc
from re import S, X
from functools import partial

from marshmallow.decorators import post_dump, post_load, pre_load
from marshmallow_polyfield import PolyField
from numpy.lib.npyio import recfromcsv
from .mvc import (ModifierTipStyle, IDNotFoundError, IDRepeatError, NodeNotFreeError, NetIndexError,
                  ReactionIndexError, NodeIndexError, CompartmentIndexError, StoichError,
                  StackEmptyError, JSONError, FileError)
from .config import ColorField, Pixel, Dim, Dim2, Color, Font, FontField, get_theme
from .canvas.geometry import Vec2
from .canvas.data import CompositeShapeFactory, PrimitiveFactory, CirclePrim, CompositeShape, Primitive, \
    RectanglePrim, HexagonPrim, LinePrim, TrianglePrim, Transform, TextPrim, ChoiceItem,\
    FONT_FAMILY_CHOICES, FONT_STYLE_CHOICES, FONT_WEIGHT_CHOICES, TEXT_ALIGNMENT_CHOICES
import copy
from dataclasses import dataclass, field
import json
from typing import Any, DefaultDict, Dict, MutableSet, Optional, Set, Tuple, List, cast
from enum import Enum
from collections import defaultdict
from marshmallow import Schema, fields, validate, missing as missing_, ValidationError, pre_dump
from pprint import pprint


# The current version of the network serialization schema.
SERIAL_VERSION = "1.0.0"


def get_theme_fn(name):
    return partial(get_theme, name, convert_color=False)

# kwargs common to geometric shapes
geometry_kwargs = {
    'fill_color': get_theme_fn('node_fill'),
    'border_color': get_theme_fn('node_border'),
    'border_width': get_theme_fn('node_border_width'),
}

# Default primitive factories
rectFact = PrimitiveFactory(RectanglePrim, **geometry_kwargs)
circleFact = PrimitiveFactory(CirclePrim, **geometry_kwargs)
hexFact = PrimitiveFactory(HexagonPrim, **geometry_kwargs)
lineFact = PrimitiveFactory(LinePrim, **geometry_kwargs)
triangleFact = PrimitiveFactory(TrianglePrim, **geometry_kwargs)
textFact = PrimitiveFactory(TextPrim)
singletonTrans = Transform()  # fills the entire bounding box

DEFAULT_SHAPE_FACTORY = CompositeShapeFactory([(rectFact, singletonTrans)],
                        (textFact, singletonTrans), 'rectangle')
# These are the default shape factories. They should never be modified by the user.
shapeFactories = [
    DEFAULT_SHAPE_FACTORY,
    CompositeShapeFactory([(circleFact, singletonTrans)], (textFact, singletonTrans), 'circle'),
    CompositeShapeFactory([(hexFact, singletonTrans)], (textFact, singletonTrans), 'hexagon'),
    CompositeShapeFactory([(lineFact, singletonTrans)], (textFact, singletonTrans), 'line'),
    CompositeShapeFactory([(triangleFact, singletonTrans)], (textFact, singletonTrans), 'triangle'),
    CompositeShapeFactory([], (textFact, singletonTrans), 'text-only'),
    CompositeShapeFactory([(circleFact, Transform(scale=Vec2.repeat(0.5))),
                          (circleFact, Transform(scale=Vec2.repeat(0.5), translation=Vec2.repeat(0.5))),
                          (PrimitiveFactory(RectanglePrim, fill_color=Color(255, 0, 0, 255)),
                               Transform(scale=Vec2.repeat(0.5), translation=Vec2.repeat(0.25)))
                          ],
       (PrimitiveFactory(TextPrim, font_color=Color(255, 255, 255, 255)), singletonTrans), 'demo combo'),
]


# TODO add lockedNode here too
class TAbstractNode(abc.ABC):
    index: int
    position: Vec2
    rectSize: Vec2
    compi: int
    nodeLocked: bool


@dataclass
class TNode(TAbstractNode):
    index: int
    id: str
    position: Vec2
    rectSize: Vec2
    floating : bool  # If false it means the node is a boundary node
    nodeLocked: bool #if false it means the node can be moved
    compi: int = -1
    shapei: int = 0
    shape: CompositeShape = field(default_factory=lambda: shapeFactories[0].produce())
    concentration: float = 0.0
    node_name: str = ''
    node_SBO: str = ''

@dataclass
class TAliasNode(TAbstractNode):
    index: int
    position: Vec2
    rectSize: Vec2
    originalIdx: int
    nodeLocked: bool
    compi: int = -1


class TNetwork:
    '''Represents an entire reaction network.

    **NOTE IMPORTANT** whenever any change is made to the code that changes how the network is
    serialized/deserialized, one must bump the global variable SERIAL_VERSION to reflect that. See
    NetworkSchema::serialVersion for more information.
    '''
    id: str
    nodes: Dict[int, TAbstractNode]
    reactions: Dict[int, 'TReaction']
    compartments: Dict[int, 'TCompartment']
    baseNodes: Set[int]  #: Set of node indices not in any compartment
    srcMap: DefaultDict[int, MutableSet[int]]  #: Map nodes to reactions of which it is a source
    destMap: DefaultDict[int, MutableSet[int]]  #: Map nodes to reactions of which it is a target
    lastNodeIdx: int
    lastReactionIdx: int
    lastCompartmentIdx: int
    parameters: Dict[str, float]

    def __init__(self, id: str, nodes: Dict[int, TAbstractNode] = None,
                 reactions: Dict[int, 'TReaction'] = None,
                 compartments: Dict[int, 'TCompartment'] = None,
                 parameters: Dict[str, float] = None,
                 ):
        if nodes is None:
            nodes = dict()
        if reactions is None:
            reactions = dict()
        if compartments is None:
            compartments = dict()
        if parameters is None:
            parameters = dict()
        self.id = id
        self.nodes = nodes
        self.reactions = reactions
        self.compartments = compartments
        self.parameters = parameters
        self.baseNodes = set(index for index, n in nodes.items() if n.compi == -1)
        self.srcMap = defaultdict(set)
        self.destMap = defaultdict(set)
        # Initialize srcMap and destMap
        for index, reaction in reactions.items():
            for src in reaction.reactants:
                self.srcMap[src].add(index)
            for dest in reaction.products:
                self.destMap[dest].add(index)

        self.lastNodeIdx = max(nodes.keys(), default=-1) + 1
        self.lastReactionIdx = max(reactions.keys(), default=-1) + 1
        self.lastCompartmentIdx = max(compartments.keys(), default=-1) + 1

    def addNode(self, node: TAbstractNode) -> int:
        self.nodes[self.lastNodeIdx] = node
        self.baseNodes.add(self.lastNodeIdx)
        ret = self.lastNodeIdx
        self.lastNodeIdx += 1
        return ret

    def addReaction(self, rea: 'TReaction'):
        self.reactions[self.lastReactionIdx] = rea

        # update nodeToReactions
        for src in rea.reactants:
            self.srcMap[src].add(self.lastReactionIdx)
        for dest in rea.products:
            self.destMap[dest].add(self.lastReactionIdx)

        self.lastReactionIdx += 1

    def addCompartment(self, comp: 'TCompartment') -> int:
        ind = self.lastCompartmentIdx
        self.compartments[ind] = comp
        self.lastCompartmentIdx += 1
        return ind


@dataclass
class TReaction:
    id: str
    centerPos: Optional[Vec2] = None
    rateLaw: str = ""
    reactants: Dict[int, 'TSpeciesNode'] = field(default_factory=dict)
    products: Dict[int, 'TSpeciesNode'] = field(default_factory=dict)
    fillColor: Color = Color(255, 150, 80, 255)
    thickness: float = 3.0
    centerHandlePos: Vec2 = Vec2()
    bezierCurves: bool = True  # If false it means a straight line
    modifiers: Set[int] = field(default_factory=set)
    tipStyle: ModifierTipStyle = ModifierTipStyle.CIRCLE


@dataclass
class TSpeciesNode:
    stoich: float
    handlePos: Vec2 = Vec2()


@dataclass
class TCompartment:
    id: str
    position: Vec2
    rectSize: Vec2
    node_indices: Set[int] = field(default_factory=set)
    volume: float = 1
    fillColor: Color = Color(0, 247, 255, 255)
    outlineColor: Color = Color(0, 106, 255, 255)
    outlineThickness: float = 2


class TStack:
    items: List['TNetworkDict']

    def __init__(self):
        self.items = []

    def isEmpty(self):
        return self.items == []

    def push(self, netDict: 'TNetworkDict'):
        theSet = copy.deepcopy(netDict)
        self.items.append(theSet)

    def pop(self):
        return self.items.pop()


class TNetworkDict(Dict[int, TNetwork]):
    def __init__(self):
        super().__init__()
        self.lastNetIndex = 0


class ErrorCode(Enum):
    OK = 0
    OTHER = -1
    ID_NOT_FOUND = -2
    ID_REPEAT = -3
    NODE_NOT_FREE = -4
    NETI_NOT_FOUND = -5
    REAI_NOT_FOUND = -6
    NODEI_NOT_FOUND = -7
    BAD_STOICH = -8
    STACK_EMPTY = -9
    JSON_ERROR = -10
    FILE_ERROR = -11
    OUT_OF_RANGE = -12
    COMPI_NOT_FOUND = -13


errorDict = {
    0: "ok",
    -1: "other",
    -2: "id not found",
    -3: "id repeat",
    -4: "node is not free",
    -5: "net index not found",
    -6: "reaction index not found",
    -7: "node index not found",
    -8: "bad stoich: stoich has to be positive",
    -9: "undo/redo stack is empty",
    -10: "Json convert error",
    -11: "File error",
    -12: "Variable out of range",
    -13: "Compartment index not found",
}


ExceptionDict = {
    -2: IDNotFoundError,
    -3: IDRepeatError,
    -4: NodeNotFreeError,
    -5: NetIndexError,
    -6: ReactionIndexError,
    -7: NodeIndexError,
    -8: StoichError,
    -9: StackEmptyError,
    -10: JSONError,
    -11: FileError,
    -12: ValueError,
    -13: CompartmentIndexError,
}


fontFamilyDict = {
    "default": 0,
    "decorative": 1,
    "roman": 2,
    "script": 3,
    "swiss": 4,
    "modern": 5,
}

fontStyleDict = {
    "normal": 0,
    "italic": 1,
}

fontWeightDict = {
    "default": 0,
    "light": 1,
    "bold": 2,
}


stackFlag: bool = True
errCode: int = 0
# dict mapping from index to network
networkDict: TNetworkDict = TNetworkDict()
undoStack: TStack = TStack()
redoStack: TStack = TStack()
lastNetIndex: int = 0


def getErrorCode():
    """get the error code of last function"""
    global errCode
    return errCode


def undo():
    """
    Undo ge back to last state
    errCode: -9: stack is empty
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if undoStack.isEmpty():
        errCode = -9
    else:
        redoStack.push(networkDict)
        networkDict = undoStack.pop()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])


def redo():
    """
    Redo redo
    errCode: -9: stack is empty
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    if redoStack.isEmpty():
        errCode = -9
    else:
        undoStack.push(networkDict)
        networkDict = redoStack.pop()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])


def startGroup():
    """
    StartGroup used at the start of a group operaction or secondary function.
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    redoStack = TStack()
    undoStack.push(networkDict)
    stackFlag = False


def endGroup():
    """
    EndGroup used at the end of a group operaction or secondary function.
    """
    global stackFlag
    stackFlag = True


def newNetwork(netID: str):
    """
    newNetwork Create a new network
    errCode -3: id repeat, 0 :ok
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack, lastNetIndex
    errCode = 0
    for network in networkDict.values():
        if network.id == netID:
            errCode = -3
            break
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])
    else:
        _pushUndoStack()

        newNetwork = TNetwork(netID)
        networkDict[lastNetIndex] = newNetwork
        lastNetIndex += 1


def getNetworkIndex(netID: str) -> int:
    """
    getNetworkIndex
    return: -2: net id can't find
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = -2

    for i, net in networkDict.items():
        if net.id == netID:
            errCode = 0
            return i

    raise ExceptionDict[errCode](errorDict[errCode])


# def saveNetworkAsJSON(neti: int, fileName: str):
#     """
#     SaveNetworkAsJSON SaveNetworkAsJSON
#     errCode: -5: net index out of range
#     -10: "Json convert error", -11: "File error"
#     """
#     global stackFlag, errCode, networkDict, undoStack, redoStack
#     errCode = 0
#     if neti not in networkDict:
#         errCode = -5
#         raise ExceptionDict[errCode](errorDict[errCode])
#     else:
#         data2 = json.dumps(networkDict[neti],
#                            sort_keys=True, indent=4, separators=(',', ': '))
#         print(data2)


# #ReadNetworkFromJSON ReadNetworkFromJSON
# #errCode -3: id repeat, 0 :ok
# #-10: "Json convert error", -11: "File error",
# def ReadNetworkFromJSON(filePath string) int :
#     errCode = 0
#     file, err1 = ioutil.ReadFile(filePath)
#     if err1 != nil :
#         errCode = -11
#         addErrorMessage(errCode, "(\"" + filePath + "\")", "", "")
#         return errCode

#     newNet = TNetwork{
#     err2 = json.Unmarshal([]byte(file), &newNet)
#     if err2 != nil :
#         errCode = -10
#         addErrorMessage(errCode, "(\"" + filePath + "\")", "", "")
#         return errCode

#     for i = range networkDict :
#         if newNet.id == networkDict[i].id :
#             errCode = -3
#             addErrorMessage(errCode, ("(\"" + filePath + "\")"), newNet.id, "")
#             return errCode


#     if stackFlag :
#         redoStack = TundoStack{
#         undoStack.push(networkDict)

#     networkDict = append(networkDict, newNet)
#     # fmt.Println(networkDict)
#     return errCode


def deleteNetwork(neti: int):
    """
    DeleteNetwork DeleteNetwork
    errCode: -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])
    else:
        _pushUndoStack()

        del networkDict[neti]


def clearNetworks():
    global stackFlag, errCode, networkDict, undoStack, redoStack, lastNetIndex
    errCode = 0
    _pushUndoStack()
    networkDict = TNetworkDict()
    lastNetIndex = 0


def getNumberOfNetworks():
    return len(networkDict)


def getNetworkID(neti: int):
    """
    GetNetworkID GetID of network
    errCode: -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])
    else:
        return networkDict[neti].id


def getListOfNetworks() -> List[int]:
    return list(networkDict.keys())


def _raiseError(eCode: int):
    global errCode
    assert eCode < 0
    errCode = eCode
    raise ExceptionDict[errCode](errorDict[errCode])


def _addNetwork(network: TNetwork) -> int:
    """Helper function that adds a network object."""
    global lastNetIndex
    for net in networkDict.values():
        if net.id == network.id:
            _raiseError(-3)
    _pushUndoStack()

    networkDict[lastNetIndex] = network
    lastNetIndex += 1
    return lastNetIndex - 1


def _getNetwork(neti: int) -> TNetwork:
    if neti not in networkDict:
        errCode = -5
        raise ExceptionDict[errCode](errorDict[errCode])
    return networkDict[neti]


def _getNodeOrAlias(neti: int, nodei: int) -> TAbstractNode:
    net = _getNetwork(neti)
    if nodei not in net.nodes:
        _raiseError(-7)

    return net.nodes[nodei]


def _getConcreteNode(neti: int, nodei: int) -> TNode:
    net = _getNetwork(neti)
    node = _getNodeOrAlias(neti, nodei)

    if isinstance(node, TAliasNode):
        # get the original node
        originalIdx = node.originalIdx
        assert originalIdx  in net.nodes
        node = net.nodes[originalIdx]

    assert isinstance(node, TNode)

    return node


def _getReaction(neti: int, reai: int) -> TReaction:
    net = _getNetwork(neti)
    if reai not in net.reactions:
        _raiseError(-6)
    return net.reactions[reai]


def _getCompartment(neti: int, compi: int) -> TCompartment:
    global errCode
    net = _getNetwork(neti)
    if compi not in net.compartments:
        errCode = -13
        raise CompartmentIndexError('Unknown index: {}'.format(compi))
    return net.compartments[compi]


def _pushUndoStack():
    global stackFlag, errCode, networkDict, undoStack, redoStack
    if stackFlag:
        redoStack = TStack()
        undoStack.push(networkDict)


def addNode(neti: int, nodeID: str, x: float, y: float, w: float, h: float, 
            floatingNode: bool = True, nodeLocked: bool = False, 
            nodeName: str = '', nodeSBO: str = '') -> int:
    """
    AddNode adds a node to the network
    errCode - 3: id repeat, 0: ok
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    n = _getNetwork(neti)
    for node in n.nodes.values():
        if isinstance(node, TNode) and node.id == nodeID:
            _raiseError(-3)

    if x < 0 or y < 0 or w <= 0 or h <= 0:
        _raiseError(-12)

    _pushUndoStack()
    newNode = TNode(n.lastNodeIdx, nodeID, Vec2(x, y), Vec2(w, h), 
                    floatingNode, nodeLocked, nodeName, nodeSBO)
    return n.addNode(newNode)


def addAliasNode(neti: int, originalIdx: int, x: float, y: float, w: float, h: float) -> int:
    net = _getNetwork(neti)

    # make sure we can get it
    original_node = _getConcreteNode(neti, originalIdx)

    _pushUndoStack()

    # Refer to the original node's index, whether 'original_index' is a TNode or a TAliasNode
    anode = TAliasNode(net.lastNodeIdx, Vec2(x, y), Vec2(w, h), original_node.index,
                       nodeLocked=False)

    anodei = net.addNode(anode)
    setCompartmentOfNode(neti, anodei, original_node.compi)
    return anodei


def aliasForReaction(neti: int, reai: int, nodei: int, x: float, y: float, w: float, h: float):
    '''Create an alias for nodei, and replace each instance of nodei in reai with the alias
    '''
    # ensure that the original node exists
    _getConcreteNode(neti, nodei)
    _pushUndoStack()

    aliasi = addAliasNode(neti, nodei, x, y, w, h)

    reaction = _getReaction(neti, reai)
    net = _getNetwork(neti)

    # update reactants and srcMap
    if nodei in reaction.reactants:
        reaction.reactants[aliasi] = reaction.reactants[nodei]
        del reaction.reactants[nodei]
        net.srcMap[nodei].remove(reai)
        net.srcMap[aliasi].add(reai)

    # update products and destMap
    if nodei in reaction.products:
        reaction.products[aliasi] = reaction.products[nodei]
        del reaction.products[nodei]
        net.destMap[nodei].remove(reai)
        net.destMap[aliasi].add(reai)


def getNodeIndex(neti: int, nodeID: str):
    """
    GetNodeIndex get node index by id
    errCode: -2: node id not found,
    -5: net index out of range
    return: >=0
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = -2
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        for i, node, in n.nodes.items():
            if isinstance(node, TNode) and node.id == nodeID:
                errCode = 0
                return i

    assert errCode < 0
    raise ExceptionDict[errCode](errorDict[errCode])


def deleteNode(neti: int, nodei: int) -> bool:
    """
    DeleteNode deletes the node with index. Returns whether there was a node with the given index,
    i.e. whether a node was deleted.

    This does not throw an error due to the possibility of someone deleting nodes in a loop, in
    which case an original copy may be deleted before its alias, and so when the alias is reached,
    it no longer exists.
    """
    def deleteHelper(net: TNetwork, node: TAbstractNode, neti: int, nodei: int, is_alias: bool):
        # to delete an alias, remove it from the compartment
        # modify the reactions that it is in, so that previous references now point to the original
        # node. Also modify the modifiers to do the same

        if is_alias:
            # swap all occurrences of alias with the original node, since we're deleting the alias
            assert isinstance(node, TAliasNode)
            srcReactions = net.srcMap[nodei]
            destReactions = net.destMap[nodei]

            # put the original node in the reaction in the place of the alias node
            for reai in srcReactions:
                rxn = net.reactions[reai]
                rxn.reactants[node.originalIdx] = rxn.reactants[nodei]
                # I'm not sure what should happen if both a node and its alias are reactants of
                # the same reaction. Originally I thought of adding up the stoich of the deleted
                # alias to that of the original node, but frankly this is such a nonsensical case
                # that I think doing so would be making it unncessarily complicated.
                # So now I'm just deleting it and doing nothing
                # if original_species:
                #     new_species = rxn.reactants[node.originalIdx]
                #     new_species.stoich += original_species.stoich
                #     new_species.handlePos = original_species.handlePos
                del rxn.reactants[nodei]

            for reai in destReactions:
                rxn = net.reactions[reai]
                # see above for explanation
                rxn.products[node.originalIdx] = rxn.products[nodei]
                # if original_species:
                #     new_species = rxn.products[node.originalIdx]
                #     new_species.stoich += original_species.stoich
                #     new_species.handlePos = original_species.handlePos
                del rxn.products[nodei]

            # update srcMap and destMap
            net.srcMap[node.originalIdx] |= net.srcMap[nodei]
            net.destMap[node.originalIdx] |= net.destMap[nodei]
            del net.srcMap[nodei]
            del net.destMap[nodei]

            # replace occurrences in modifiers
            for rxn in net.reactions.values():
                if nodei in rxn.modifiers:
                    rxn.modifiers.remove(nodei)
                    rxn.modifiers.add(node.originalIdx)
        else:
            # for now, disallow removing concrete nodes that are part of a reaction
            if len(net.srcMap[nodei]) != 0 or len(net.destMap[nodei]) != 0:
                _raiseError(-4)

            # remove self from modifiers list
            for rxn in net.reactions.values():
                rxn.modifiers.discard(nodei)

        # remove from compartment
        compi = getCompartmentOfNode(neti, nodei)
        if compi == -1:
            net.baseNodes.remove(nodei)
        else:
            net.compartments[compi].node_indices.remove(nodei)

        # remove from 'nodes'
        del net.nodes[nodei]


    net = _getNetwork(neti)
    try:
        node = _getNodeOrAlias(neti, nodei)
    except NodeIndexError:
        return False

    # validate that node is not part of a reaction
    if isinstance(node, TNode) and (len(net.srcMap[nodei]) != 0 or len(net.destMap[nodei]) != 0):
        _raiseError(-4)

    _pushUndoStack()

    is_alias = isinstance(node, TAliasNode)
    if is_alias:
        deleteHelper(net, node, neti, nodei, True)
    else:
        # delete all the aliases of node if node is an original node
        alias_indices = [i for i, n in net.nodes.items() if isinstance(n, TAliasNode) and cast(TAliasNode, n).originalIdx == nodei]
        for alias_idx in alias_indices:
            deleteHelper(net, net.nodes[alias_idx], neti, alias_idx, True)

        # delete original node
        deleteHelper(net, node, neti, nodei, False)

    return True


def clearNetwork(neti: int):
    """
    ClearNetwork clear all nodes and reactions in this network
    errCode: -5:  net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])
    else:
        _pushUndoStack()
        # networkDict[neti].nodes.clear()
        # networkDict[neti].reactions.clear()
        # networkDict[neti].compartments.clear()
        networkDict[neti] = TNetwork(networkDict[neti].id)


def getNumberOfNodes(neti: int):
    """
    GetNumberOfNodes get the number of nodes in the current network
    num: >= -5:  net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])
    else:
        n = networkDict[neti]
        return len(n.nodes)


def getNodeCenter(neti: int, nodei: int):
    """
    GetNodeCenter Get the X and  Y coordinate of the Center of node
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes:
            errCode = -7
        else:
            X = round(n.nodes[nodei].position.x + n.nodes[nodei].rectSize.x*0.5, 2)
            Y = round(n.nodes[nodei].position.y + n.nodes[nodei].rectSize.y*0.5, 2)
            return (X, Y)

    raise ExceptionDict[errCode](errorDict[errCode])


def getNodeID(neti: int, nodei: int):
    """
    GetNodeID: Get the id of the node
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        node = _getConcreteNode(neti, nodei)
        return node.id

    raise ExceptionDict[errCode](errorDict[errCode])

def getNodeName(neti: int, nodei: int):
    """
    GetNodeName: Get the name of the node
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        node = _getConcreteNode(neti, nodei)
        return node.node_name

    raise ExceptionDict[errCode](errorDict[errCode])


def getNodeSBO(neti: int, nodei: int):
    """
    GetNodeSBO: Get the SBO of the node
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        node = _getConcreteNode(neti, nodei)
        return node.node_SBO

    raise ExceptionDict[errCode](errorDict[errCode])

def getNodeConcentration(neti: int, nodei: int):
    """
    GetNodeConcentration - get the concentration of the node
    errcode:
        -7: node index out of range
        -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        node = _getConcreteNode(neti, nodei)
        return node.concentration

    raise ExceptionDict[errCode](errorDict[errCode])


def getOriginalIndex(neti: int, nodei: int) -> int:
    '''Return -1 if the node is an original, or if this is an alias, return the original index.'''
    node = _getNodeOrAlias(neti, nodei)
    if isinstance(node, TNode):
        return -1
    else:
        assert isinstance(node, TAliasNode)
        return node.originalIdx


def IsFloatingNode(neti : int, nodei : int):
    return _getConcreteNode(neti, nodei).floating


def IsBoundaryNode(neti : int, nodei : int):
    return not IsFloatingNode(neti, nodei)


def IsNodeLocked(neti: int, nodei: int):
    return _getNodeOrAlias(neti, nodei).nodeLocked


def getListOfNodeIDs(neti: int) -> List[str]:
    if neti not in networkDict:
        errCode = -5
        raise ExceptionDict[errCode](errorDict[errCode])
    return [n.id for n in networkDict[neti].nodes.values() if isinstance(n, TNode)]


def getListOfNodeIndices(neti: int) -> Set[int]:
    return cast(Set[int], _getNetwork(neti).nodes.keys())


def getListOfReactionIndices(neti: int) -> Set[int]:
    return cast(Set[int], _getNetwork(neti).reactions.keys())


def getListOfCompartmentIndices(neti: int) -> Set[int]:
    return cast(Set[int], _getNetwork(neti).compartments.keys())


def getSrcReactions(neti: int, nodei: int) -> Set[int]:
    return set(_getNetwork(neti).srcMap[nodei])


def getDestReactions(neti: int, nodei: int) -> Set[int]:
    return set(_getNetwork(neti).destMap[nodei])


def getNodeCoordinateAndSize(neti: int, nodei: int):
    """
    getNodeCoordinateAndSize get the x,y,w,h of the node
    errCode:-7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes:
            errCode = -7
        else:
            X = round(n.nodes[nodei].position.x, 2)
            Y = round(n.nodes[nodei].position.y, 2)
            W = round(n.nodes[nodei].rectSize.x, 2)
            H = round(n.nodes[nodei].rectSize.y, 2)
            return (X, Y, W, H)

    raise ExceptionDict[errCode](errorDict[errCode])


def colorToRGB(color: Color):
    color1 = color.r
    color1 = (color1 << 8) | color.g
    color1 = (color1 << 8) | color.b
    return color1


def getNodeFillColor(neti: int, nodei: int):
    """
    Return the 'fill_color' property of the first primitive in the given node's composite shape, if
    there is such a primitive. Otherwise, return None.

    This function exists for backwards-compatibility and convenience reasons.

    errCode: -7: node index out of range
    -5: net index out of range
    """
    node = _getConcreteNode(neti, nodei)
    for prim, _ in node.shape.items:
        if 'fill_color' in prim.__dataclass_fields__:
            ret = getattr(prim, 'fill_color')
            assert isinstance(ret, Color)
            return ret
    return None


def getNodeFillColorRGB(neti: int, nodei: int):
    """
    See getNodeFillColor(), except only returns the RGB values

    errCode: -7: node index out of range
    -5: net index out of range
    """
    color = getNodeFillColor(neti, nodei)
    if color is None:
        return None
    return colorToRGB(color)


def getNodeFillColorAlpha(neti: int, nodei: int):
    """
    getNodeFillColorAlpha getNodeFillColor alpha value(float)
    errCode: -7: node index out of range
    -5: net index out of range
    """
    color = getNodeFillColor(neti, nodei)
    if color is None:
        return None
    return float(color.a) / 255


def getNodeBorderColor(neti: int, nodei: int):
    """
    getNodeBorderColor rgba tulple format, rgb range int[0,255] alpha range float[0,1]
    errCode: -7: node index out of range
    -5: net index out of range
    """
    node = _getConcreteNode(neti, nodei)
    for prim, _ in node.shape.items:
        if 'border_color' in prim.__dataclass_fields__:
            ret = getattr(prim, 'border_color')
            assert isinstance(ret, Color)
            return ret
    return None


def getNodeBorderColorRGB(neti: int, nodei: int):
    """
    getNodeBorderColorRGB getNodeBorderColor rgb int format
    errCode: -7: node index out of range
    -5: net index out of range
    """
    color = getNodeBorderColor(neti, nodei)
    if color is None:
        return None
    return colorToRGB(color)


def getNodeBorderColorAlpha(neti: int, nodei: int):
    """
    getNodeBorderColorAlpha getNodeBorderColor alpha value(float)
    errCode: -7: node index out of range
    -5: net index out of range
    """
    color = getNodeBorderColor(neti, nodei)
    if color is None:
        return None
    return float(color.a) / 255


def getNodeBorderWidth(neti: int, nodei: int):
    """
    getNodeBorderWidth
    errCode: -7: node index out of range
    -5: net index out of range
    """
    node = _getConcreteNode(neti, nodei)
    for prim, _ in node.shape.items:
        if 'border_width' in prim.__dataclass_fields__:
            return getattr(prim, 'border_width')
    return None


def setNodeID(neti: int, nodei: int, newID: str):
    """
    setNodeID set the id of a node
    errCode -3: id repeat
    -5: net index out of range
    -7: node index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        net = networkDict[neti]
        if nodei not in net.nodes.keys():
            errCode = -7
        else:
            if any((n.id == newID for n in net.nodes.values() if isinstance(n, TNode))):
                errCode = -3
            else:
                _pushUndoStack()
                _getConcreteNode(neti, nodei).id = newID
                return
    raise ExceptionDict[errCode](errorDict[errCode])

def setNodeName(neti: int, nodei: int, newName: str):
    """
    setNodeName set the name of a node
    -5: net index out of range
    -7: node index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        net = networkDict[neti]
        if nodei not in net.nodes.keys():
            errCode = -7
        else:
            _pushUndoStack()
            _getConcreteNode(neti, nodei).node_name = newName
            return
    raise ExceptionDict[errCode](errorDict[errCode])

def setNodeSBO(neti: int, nodei: int, newSBO: str):
    """
    setNodeSBO set the name of a node
    -5: net index out of range
    -7: node index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        net = networkDict[neti]
        if nodei not in net.nodes.keys():
            errCode = -7
        else:
            _pushUndoStack()
            _getConcreteNode(neti, nodei).node_SBO = newSBO
            return
    raise ExceptionDict[errCode](errorDict[errCode])

def setNodeConcentration(neti: int, nodei: int, newConc: float):
    """
    setNodeConcentration - sets the concentration of a node
    errCode -5: net index out of range
            -7: node index out of range
            -12: variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        net = networkDict[neti]
        if nodei not in net.nodes.keys():
            errCode = -7
        elif newConc < 0.0:
            errCode = -12
        else:
            _pushUndoStack()
            _getConcreteNode(neti, nodei).concentration = newConc
            return
    raise ExceptionDict[errCode](errorDict[errCode])

def setNodeCoordinate(neti: int, nodei: int, x: float, y: float, allowNegativeCoordinates: bool = False):
    """
    setNodeCoordinate setNodeCoordinate
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0

    if allowNegativeCoordinates:
        lowerLimit = -1E12
    else:
        lowerLimit = 0

    if neti not in networkDict:
        errCode = -5
    else:
        if x < lowerLimit or y < lowerLimit:
            _raiseError(-12)

        n = _getNodeOrAlias(neti, nodei)
        # only move if node is locked
        if not n.nodeLocked:
            _pushUndoStack()
            n.position = Vec2(x, y)

        return

    raise ExceptionDict[errCode](errorDict[errCode])


def setNodeSize(neti: int, nodei: int, w: float, h: float):
    """
    setNodeSize setNodeSize
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes:
            errCode = -7
        elif w <= 0 or h <= 0:
            errCode = -12
        else:
            _pushUndoStack()
            n.nodes[nodei].rectSize = Vec2(w, h)
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def setNodeFloatingStatus (neti: int, nodei: int, floatingStatus : bool):
    """
    setNodeFloatingStatus setNodeFloatingStatus
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes:
            errCode = -7
        else:
            _pushUndoStack()
            _getConcreteNode(neti, nodei).floating = floatingStatus
            return

    raise ExceptionDict[errCode](errorDict[errCode])

def setNodeLockedStatus (neti: int, nodei: int, lockedNode: bool):
    """
    setNodeLockedStatus setNodeLockedStatus
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes:
            errCode = -7
        else:
            _pushUndoStack()
            _getNodeOrAlias(neti, nodei).nodeLocked = lockedNode
            return


def setNodeFillColorRGB(neti: int, nodei: int, r: int, g: int, b: int):
    """
    setNodeFillColorRGB setNodeFillColorRGB
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    if r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
        _raiseError(-12)

    node = _getConcreteNode(neti, nodei)
    for prim, _ in node.shape.items:
        if 'fill_color' in prim.__dataclass_fields__:
            old_color = getattr(prim, 'fill_color')
            assert isinstance(old_color, Color)
            setattr(prim, 'fill_color', old_color.swapped(r, g, b))


def setNodeFillColorAlpha(neti: int, nodei: int, a: float):
    """
    setNodeFillColorAlpha setNodeFillColorAlpha
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    if a < 0 or a > 1:
        _raiseError(-12)

    node = _getConcreteNode(neti, nodei)
    for prim, _ in node.shape.items:
        if 'fill_color' in prim.__dataclass_fields__:
            a_int = int(a * 255)
            old_color = getattr(prim, 'fill_color')
            assert isinstance(old_color, Color)
            setattr(prim, 'fill_color', old_color.swapped(a=a_int))


def setNodeBorderColorRGB(neti: int, nodei: int, r: int, g: int, b: int):
    """
    setNodeBorderColorRGB setNodeBorderColorRGB
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    if r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
        _raiseError(-12)

    node = _getConcreteNode(neti, nodei)
    for prim, _ in node.shape.items:
        if 'border_color' in prim.__dataclass_fields__:
            old_color = getattr(prim, 'border_color')
            assert isinstance(old_color, Color)
            setattr(prim, 'border_color', old_color.swapped(r, g, b))


def setNodeBorderColorAlpha(neti: int, nodei: int, a: float):
    """
    setNodeBorderColorAlpha setNodeBorderColorAlpha, alpha is a float between 0 and 1
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    if a < 0 or a > 1:
        _raiseError(-12)
    node = _getConcreteNode(neti, nodei)
    for prim, _ in node.shape.items:
        if 'border_color' in prim.__dataclass_fields__:
            a_int = int(a * 255)
            old_color = getattr(prim, 'border_color')
            assert isinstance(old_color, Color)
            setattr(prim, 'border_color', old_color.swapped(a=a_int))


def setNodeBorderWidth(neti: int, nodei: int, width: float):
    """
    setNodeBorderWidth setNodeBorderWidth
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    if width <= 0:
        _raiseError(-12)
    node = _getConcreteNode(neti, nodei)
    for prim, _ in node.shape.items:
        if 'border_width' in prim.__dataclass_fields__:
            setattr(prim, 'border_width', width)


def createReaction(neti: int, reaID: str, sources: List[int], targets: List[int]):
    """
    createReaction create an empty reacton
    errCode: -3: id repeat
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0

    if len(sources) == 0 or len(targets) == 0:
        raise ValueError("Reaction '{}' has no reactants or it has no products".format(reaID))

    net = _getNetwork(neti)
    # duplicate ID?
    if any((r.id == reaID for r in net.reactions.values())):
        errCode = -3
    else:
        # ensure nodes exist
        if any(nodei not in net.nodes.keys() for nodei in sources):
            _raiseError(-7)
        if any(nodei not in net.nodes.keys() for nodei in targets):
            _raiseError(-7)

        if set(sources) == set(targets):
            raise ValueError('Reaction source node set and target node set cannot be identical.')
        _pushUndoStack()
        newReact = TReaction(reaID)

        # Add src/target nodes
        for srcNodeIdx in sources:
            newReact.reactants[srcNodeIdx] = TSpeciesNode(1)  # default stoich to 1
        for destNodeIdx in targets:
            newReact.products[destNodeIdx] = TSpeciesNode(1)  # default stoich to 1

        net.addReaction(newReact)
        return

    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionIndex(neti: int, reaID: str):
    """
    getReactionIndex get reaction index by id
    return: -2: id can't find, >=0: ok
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        errCode = -2
        for i, r in networkDict[neti].reactions.items():
            if r.id == reaID:
                errCode = 0
                return i

    raise ExceptionDict[errCode](errorDict[errCode])


def deleteReaction(neti: int, reai: int):
    """
    deleteReaction delete the reaction with index
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            _pushUndoStack()
            net = _getNetwork(neti)
            reaction = _getReaction(neti, reai)
            for src in reaction.reactants:
                net.srcMap[src].remove(reai)
            for dest in reaction.products:
                net.destMap[dest].remove(reai)
            del networkDict[neti].reactions[reai]
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def clearReactions(neti: int):
    """
    clearReactions clear all reactions in this network
    errCode: -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])
    else:
        _pushUndoStack()
        net = _getNetwork(neti)
        net.reactions.clear()
        net.srcMap.clear()
        net.destMap.clear()


def getNumberOfReactions(neti: int):
    """
    getNumberOfReactions get the number of reactions in the current Reactionset
    return: >=0: ok, -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])
    else:
        r = networkDict[neti].reactions
        return len(r)


def getReactionID(neti: int, reai: int):
    """
    getReactionID get the id of Reaction
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return r[reai].id

    raise ExceptionDict[errCode](errorDict[errCode])


def getListOfReactionIDs(neti: int) -> List[str]:
    if neti not in networkDict:
        errCode = -5
        raise ExceptionDict[errCode](errorDict[errCode])
    return [r.id for r in networkDict[neti].reactions.values()]


def getReactionRateLaw(neti: int, reai: int):
    """
    getReactionRateLaw get the ratelaw of Reaction
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return r[reai].rateLaw

    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionCenterPos(neti: int, reai: int):
    """
    getReactionCenterPos get the center position of the Reaction
    """
    r = _getReaction(neti, reai)
    return r.centerPos


def getReactionFillColor(neti: int, reai: int):
    """
    getReactionFillColor rgba tulple format, rgb range int[0,255] alpha range float[0,1]
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return (r[reai].fillColor.r, r[reai].fillColor.g, r[reai].fillColor.b, float(r[reai].fillColor.a)/255)

    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionFillColorRGB(neti: int, reai: int):
    """
    getReactionFillColorRGB getReactionFillColorRGB
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            color1 = r[reai].fillColor.r
            color1 = (color1 << 8) | r[reai].fillColor.g
            color1 = (color1 << 8) | r[reai].fillColor.b
            return color1

    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionFillColorAlpha(neti: int, reai: int):
    """
    getReactionFillColorAlpha getReactionFillColorAlpha
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            alpha1 = float(r[reai].fillColor.a) / 255
            return alpha1

    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionLineThickness(neti: int, reai: int):
    """
    getReactionLineThickness getReactionLineThickness
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return r[reai].thickness

    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionCenterHandlePosition(neti: int, reai: int):
    """
    getReactionCenterHandlePosition getReactionCenterHandlePosition
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return (round(r[reai].centerHandlePos.x, 2), round(r[reai].centerHandlePos.y, 2))

    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionSrcNodeStoich(neti: int, reai: int, srcNodeIdx: int):
    """
    getReactionSrcNodeStoich get the SrcNode stoichiometry of Reaction
    errCode: -6: reaction index out of range,
    -5: net index out of range, -7: node index not found
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif srcNodeIdx not in networkDict[neti].nodes:
            errCode = -7
        elif srcNodeIdx not in r[reai].reactants:
            raise ValueError('The given node index "{}" is not a reactant node of "{}"'.format(
                             srcNodeIdx, reai))
        else:
            return r[reai].reactants[srcNodeIdx].stoich
    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionDestNodeStoich(neti: int, reai: int, destNodeIdx: int):
    """
    getReactionDestNodeStoich get the DestNode stoichiometry of Reaction
    return: positive float : ok, -6: reaction index out of range, -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif destNodeIdx not in networkDict[neti].nodes:
            errCode = -7
        elif destNodeIdx not in r[reai].products:
            raise ValueError('The given node index "{}" is not a product node of "{}"'.format(
                             destNodeIdx, reai))
        else:
            s = r[reai].products[destNodeIdx]
            return s.stoich
    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionSrcNodeHandlePosition(neti: int, reai: int, srcNodeIdx: int):
    """
    getReactionSrcNodeHandlePosition get the SrcNode HandlePosition of Reaction
    errCode: -6: reaction index out of range,
    -5: net index out of range, -7: node index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif srcNodeIdx not in networkDict[neti].nodes:
            errCode = -7
        elif srcNodeIdx not in r[reai].reactants:
            raise ValueError('The given node index "{}" is not a reactant node of "{}"'.format(
                             srcNodeIdx, reai))
        else:
            return (round(r[reai].reactants[srcNodeIdx].handlePos.x, 2),
                    round(r[reai].reactants[srcNodeIdx].handlePos.y, 2))

    raise ExceptionDict[errCode](errorDict[errCode])


def getReactionDestNodeHandlePosition(neti: int, reai: int, destNodeIdx: int):
    """
    getReactionDestNodeStoich get the DestNode HandlePosition of Reaction
    return: positive float : ok, -6: reaction index out of range, -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif destNodeIdx not in networkDict[neti].nodes:
            errCode = -7
        elif destNodeIdx not in r[reai].products:
            raise ValueError('The given node index "{}" is not a product node of "{}"'.format(
                             destNodeIdx, reai))
        else:
            return (round(r[reai].products[destNodeIdx].handlePos.x, 2),
                    round(r[reai].products[destNodeIdx].handlePos.y, 2))

    raise ExceptionDict[errCode](errorDict[errCode])


def getNumberOfSrcNodes(neti: int, reai: int):
    """
    getNumberOfSrcNodes get the SrcNode length of Reaction
    return: non-negative int: ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return len(r[reai].reactants)

    raise ExceptionDict[errCode](errorDict[errCode])


def getNumberOfDestNodes(neti: int, reai: int):
    """
    getNumberOfDestNodes get the DestNode length of Reaction
    return: non-negative int: ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return len(r[reai].products)

    raise ExceptionDict[errCode](errorDict[errCode])


def getListOfReactionSrcNodes(neti: int, reai: int) -> List[int]:
    """
    getListOfReactionSrcNodes getListOfReactionSrcNodes in alphabetical order
    return: non-empty slice : ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        reactions = networkDict[neti].reactions
        if reai not in reactions:
            errCode = -6
        else:
            list1 = []
            for k in reactions[reai].reactants:
                list1.append(k)
            list1.sort()
            return list1

    raise ExceptionDict[errCode](errorDict[errCode])


def getListOfReactionDestNodes(neti: int, reai: int) -> List[int]:
    """
    getListOfReactionDestNodes getListOfReactionDestNodes in alphabetical order
    return: non-empty slice : ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            list1 = []
            for k in r[reai].products:
                list1.append(k)
            list1.sort()
            return list1

    raise ExceptionDict[errCode](errorDict[errCode])


def getListOfReactionSrcStoich(neti: int, reai: int) -> List[float]:
    n = getListOfReactionSrcNodes(neti, reai)
    srcStoichList = []
    for srcNodeID in n:
        srcStoichList.append(getReactionSrcNodeStoich(neti, reai, srcNodeID))
    return srcStoichList


def getListOfReactionDestStoich(neti: int, reai: int) -> List[float]:
    n = getListOfReactionDestNodes(neti, reai)
    destStoichList = []
    for destNodeID in n:
        destStoichList.append(getReactionDestNodeStoich(neti, reai, destNodeID))
    return destStoichList


def printReactionInfo(neti: int, reai: int):
    print("id:", getReactionID(neti, reai))
    print("rateLaw:", getReactionRateLaw(neti, reai))
    print("SrcNodes:", getListOfReactionSrcNodes(neti, reai))
    print("DestNodes:", getListOfReactionDestNodes(neti, reai))
    print("SrcNodeStoichs:", getListOfReactionSrcStoich(neti, reai))
    print("DestNodeStoichs:", getListOfReactionDestStoich(neti, reai))


# def deleteSrcNode(neti: int, reai: int, srcNodeIdx: int):
#     """
#     deleteSrcNode delete src nodes by id(ID).
#     errCode: -6: reaction index out of range,
#     -5: net index out of range
#     -2: id not found
#     """
#     global stackFlag, errCode, networkDict, undoStack, redoStack
#     errCode = 0
#     if neti not in networkDict:
#         errCode = -5
#     else:
#         r = networkDict[neti].reactions
#         if reai not in networkDict[neti].reactions:
#             errCode = -6
#         else:
#             rea = r[reai]
#             if srcNodeIdx not in rea.reactants:
#                 errCode = -2
#             else:
#                 _pushUndoStack()
#                 del rea.reactants[srcNodeIdx]
#                 networkDict[neti].reactions[reai] = rea
#                 return

#     raise ExceptionDict[errCode](errorDict[errCode])


# def deleteDestNode(neti: int, reai: int, destNodeIdx: int):
#     """
#     deleteDestNode delete all dest nodes by id
#     errCode: -6: reaction index out of range,
#     -5: net index out of range
#     -2: id not found
#     """
#     global stackFlag, errCode, networkDict, undoStack, redoStack
#     errCode = 0
#     if neti not in networkDict:
#         errCode = -5
#     else:
#         r = networkDict[neti].reactions
#         if reai not in networkDict[neti].reactions:
#             errCode = -6
#         else:
#             rea = r[reai]
#             if destNodeIdx not in rea.products:
#                 errCode = -2
#             else:
#                 _pushUndoStack()
#                 del rea.products[destNodeIdx]
#                 return

#     raise ExceptionDict[errCode](errorDict[errCode])


def setReactionID(neti: int, reai: int, newID: str):
    """
    setReactionID edit id of reaction
    errCode: 0:ok, -6: reaction index out of range
    -5: net index out of range
    -3: id repeat
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        reactions = networkDict[neti].reactions
        if reai not in reactions:
            errCode = -6
        else:
            if any((r.id == newID for r in reactions.values())):
                errCode = -3
            else:
                _pushUndoStack()
                networkDict[neti].reactions[reai].id = newID
                return

    raise ExceptionDict[errCode](errorDict[errCode])


def setRateLaw(neti: int, reai: int, rateLaw: str):
    """
    setRateLaw edit rate law of reaction
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            _pushUndoStack()
            networkDict[neti].reactions[reai].rateLaw = rateLaw
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def setReactionCenterPos(neti: int, reai: int, centerPos: Optional[Vec2]):
    """
    setReactionCenterPos set the center position of the Reaction
    """
    r = _getReaction(neti, reai)
    r.centerPos = centerPos


def setReactionSrcNodeStoich(neti: int, reai: int, srcNodeIdx: int, newStoich: float):
    """
    setReactionSrcNodeStoich edit Stoich by Reaction srcNodeID
    errCode: -6: reaction index not found,
    -5: net index not found
    -7: node index not found,
    -8: wrong stoich
    raises ValueError if given node index not a dest node
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif srcNodeIdx not in networkDict[neti].nodes:
            errCode = -7
        elif srcNodeIdx not in r[reai].reactants:
            raise ValueError('The given node index "{}" is not a reactant node of "{}"'.format(
                             srcNodeIdx, reai))
        elif newStoich <= 0.0:
            errCode = -8
        else:
            _pushUndoStack()
            networkDict[neti].reactions[reai].reactants[srcNodeIdx].stoich = newStoich
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def setReactionDestNodeStoich(neti: int, reai: int, destNodeIdx: int, newStoich: float):
    """
    setReactionDestNodeStoich edit Stoich by Reaction destNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range,
    -7: node index not found,
    -8: wrong stoich
    raises ValueError if given node index not a dest node
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif destNodeIdx not in networkDict[neti].nodes:
            errCode = -7
        elif destNodeIdx not in r[reai].products:
            raise ValueError('The given node index "{}" is not a product node of "{}"'.format(
                             destNodeIdx, reai))
        elif newStoich <= 0.0:
            errCode = -8
        else:
            _pushUndoStack()
            networkDict[neti].reactions[reai].products[destNodeIdx].stoich = newStoich
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def setReactionSrcNodeHandlePosition(neti: int, reai: int, srcNodeIdx: int, handlePosX: float, handlePosY: float):
    """
    setReactionSrcNodeHandlePosition edit HandlePosition by Reaction srcNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -7: node index not found
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif srcNodeIdx not in networkDict[neti].nodes:
            _raiseError(-7)
        elif srcNodeIdx not in r[reai].reactants:
            raise ValueError('The given node index "{}" is not a reactant node of "{}"'.format(
                             srcNodeIdx, reai))
        else:
            _pushUndoStack()
            networkDict[neti].reactions[reai].reactants[srcNodeIdx].handlePos = Vec2(
                handlePosX, handlePosY)
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def setReactionDestNodeHandlePosition(neti: int, reai: int, destNodeIdx: int, handlePosX: float, handlePosY: float):
    """
    setReactionDestNodeHandlePosition edit HandlePosition by Reaction destNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif destNodeIdx not in networkDict[neti].nodes:
            _raiseError(-7)
        elif destNodeIdx not in r[reai].products:
            raise ValueError('The given node index "{}" is not a product node of "{}"'.format(
                             destNodeIdx, reai))
        else:
            _pushUndoStack()
            networkDict[neti].reactions[reai].products[destNodeIdx].handlePos = Vec2(
                handlePosX, handlePosY)
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def setReactionFillColorRGB(neti: int, reai: int, R: int, G: int, B: int):
    """
    setReactionFillColorRGB setReactionFillColorRGB
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif R < 0 or R > 255 or G < 0 or G > 255 or B < 0 or B > 255:
            errCode = -12
        else:
            _pushUndoStack()
            r[reai].fillColor = r[reai].fillColor.swapped(R, G, B)
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def setReactionFillColorAlpha(neti: int, reai: int, a: float):
    """
    setReactionFillColorAlpha setReactionFillColorAlpha
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif a < 0 or a > 1:
            errCode = -12
        else:
            _pushUndoStack()
            A1 = int(a * 255)
            r[reai].fillColor = r[reai].fillColor.swapped(a=A1)
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def setReactionLineThickness(neti: int, reai: int, thickness: float):
    """
    setReactionLineThickness setReactionLineThickness
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif thickness <= 0:
            errCode = -12
        else:
            _pushUndoStack()
            networkDict[neti].reactions[reai].thickness = thickness
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def bezier_curves(neti: int, reai: int):
    n = _getNetwork(neti)
    return n.reactions[reai].bezierCurves

def setReactionBezierCurves(neti: int, reai: int, bezierCurves: bool):
    """
    setReactionBezierCurves setReactionBezierCurves
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            _pushUndoStack()
            r[reai].bezierCurves = bezierCurves
            return

    raise ExceptionDict[errCode](errorDict[errCode])


def setReactionModifiers(neti: int, reai: int, modifiers: Set[int]):
    r = _getReaction(neti, reai)
    r.modifiers = copy.copy(set(modifiers))


def getReactionModifiers(neti: int, reai: int) -> Set[int]:
    r = _getReaction(neti, reai)
    return copy.copy(r.modifiers)


def setModifierTipStyle(neti: int, reai: int, tipStyle: ModifierTipStyle):
    r = _getReaction(neti, reai)
    r.tipStyle = tipStyle


def getModifierTipStyle(neti: int, reai: int) -> ModifierTipStyle:
    r = _getReaction(neti, reai)
    return r.tipStyle


def setReactionCenterHandlePosition(neti: int, reai: int, centerHandlePosX: float, centerHandlePosY: float):
    """
    setReactionCenterHandlePosition setReactionCenterHandlePosition
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, undoStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            _pushUndoStack()
            networkDict[neti].reactions[reai].centerHandlePos = Vec2(
                centerHandlePosX, centerHandlePosY)
            return

    raise ExceptionDict[errCode](errorDict[errCode])

def setParameter(netid: int, param_id: str, param_value: float):
    """
    Add or change network parameter
    """
    errCode = 0
    if netid not in networkDict:
        errCode = -5
    else:
        # TODO verify param values
        n = _getNetwork(netid)
        _pushUndoStack()
        n.parameters[param_id] = param_value
        return
    
    raise ExceptionDict[errCode](errorDict[errCode])

def removeParameter(netid: int, param_id: str):
    """
    Remove a network parameter. No change if param_id is not a parameter.
    """
    errCode = 0
    if netid not in networkDict:
        errCode = -5
    else:
        n = _getNetwork(netid)
        _pushUndoStack()
        n.parameters.pop(param_id)
        return

    raise ExceptionDict[errCode](errDict[errCode])

def getParameters(netid: int):
    if netid not in networkDict:
        raise ExceptionDict[-5](errDict[-5])
    else:
        n = _getNetwork(netid)
        return n.parameters
    

def addCompartment(neti: int, compID: str, x: float, y: float, w: float, h: float) -> int:
    """
    Create a compartment and add to canvas. Return the index of the compartment added.

    Args:
        neti: network index.
        compID: ID of the compartment.
        x: x coordinate of top-left corner
        y: y coordinate of top-left corner
        w: width
        h: height
    """
    if x < 0 or y < 0 or w < 0 or h < 0:
        _raiseError(-12)
    net = _getNetwork(neti)
    comp = TCompartment(compID, Vec2(x, y), Vec2(w, h))
    if any((compID == c.id for c in net.compartments.values())):
        _raiseError(-3)
    _pushUndoStack()
    return net.addCompartment(comp)


def deleteCompartment(neti: int, compi: int):
    """Delete the compartment of the given index in the given network."""
    net = _getNetwork(neti)
    if compi not in net.compartments:
        _raiseError(-13)

    _pushUndoStack()
    # Put all nodes in compartment in base compartment (-1)
    for nodei in net.compartments[compi].node_indices:
        assert net.nodes[nodei].compi == compi
        # move to base compartment
        net.nodes[nodei].compi = -1
        net.baseNodes.add(nodei)

    del net.compartments[compi]


def getListOfCompartments(neti: int) -> List[int]:
    return list(_getNetwork(neti).compartments.keys())


def getNodesInCompartment(neti: int, compi: int) -> List[int]:
    """Return the list of node indices in the given compartment."""
    if compi == -1:
        return list(_getNetwork(neti).baseNodes)
    return list(_getCompartment(neti, compi).node_indices)  # Make copy in the process


def getCompartmentOfNode(neti: int, nodei: int) -> int:
    """Return the compartment index that the given node is in, or -1 if it is not in any."""
    return _getNodeOrAlias(neti, nodei).compi


def setCompartmentOfNode(neti: int, nodei: int, compi: int):
    """Set the compartment of the node, or remove it from any compartment if -1 is given."""
    net = _getNetwork(neti)
    node = _getNodeOrAlias(neti, nodei)
    if node.compi == '':
        node.compi = -1
    _pushUndoStack()
    if node.compi != -1:
        net.compartments[node.compi].node_indices.remove(nodei)
    else:
        net.baseNodes.remove(nodei)

    if compi != -1:
        newComp = _getCompartment(neti, compi)
        newComp.node_indices.add(nodei)
    else:
        net.baseNodes.add(nodei)

    node.compi = compi


def setCompartmentPosition(neti: int, compi: int, x: float, y: float):
    if x < 0 or y < 0:
        _raiseError(-12)
    _pushUndoStack()
    comp = _getCompartment(neti, compi)
    comp.position = Vec2(x, y)


def getCompartmentPosition(neti: int, compi: int) -> Tuple[float, float]:
    comp = _getCompartment(neti, compi)
    return (comp.position.x, comp.position.y)


def setCompartmentSize(neti: int, compi: int, w: float, h: float):
    if w < 0 or h < 0:
        _raiseError(-12)
    _pushUndoStack()
    comp = _getCompartment(neti, compi)
    comp.rectSize = Vec2(w, h)


def getCompartmentSize(neti: int, compi: int) -> Tuple[float, float]:
    comp = _getCompartment(neti, compi)
    return (comp.rectSize.x, comp.rectSize.y)


def setCompartmentVolume(neti: int, compi: int, volume: float):
    _pushUndoStack()
    _getCompartment(neti, compi).volume = volume


def getCompartmentVolume(neti: int, compi: int) -> float:
    return _getCompartment(neti, compi).volume


def setCompartmentID(neti: int, compi: int, id: str):
    _pushUndoStack()
    _getCompartment(neti, compi).id = id


def getCompartmentID(neti: int, compi: int) -> str:
    return _getCompartment(neti, compi).id


# TODO note that this returns a Color instead of tuples of numbers. Should change the node &
# reaction color functions to do the same.
def setCompartmentFillColor(neti: int, compi: int, color: Color):
    _pushUndoStack()
    _getCompartment(neti, compi).fillColor = color


def getCompartmentFillColor(neti: int, compi: int) -> Color:
    return _getCompartment(neti, compi).fillColor


def setCompartmentOutlineColor(neti: int, compi: int, color: Color):
    _pushUndoStack()
    _getCompartment(neti, compi).outlineColor = color


def getCompartmentOutlineColor(neti: int, compi: int) -> Color:
    return _getCompartment(neti, compi).outlineColor


def setCompartmentOutlineThickness(neti: int, compi: int, thickness: float):
    _pushUndoStack()
    _getCompartment(neti, compi).outlineThickness = thickness


def getCompartmentOutlineThickness(neti: int, compi: int) -> float:
    return _getCompartment(neti, compi).outlineThickness


def createUniUni(neti: int, reaID: str, rateLaw: str, srci: int, desti: int, srcStoich: float, destStoich: float):
    startGroup()
    createReaction(neti, reaID, [srci], [desti])
    reai = getReactionIndex(neti, reaID)

    setReactionSrcNodeStoich(neti, reai, srci, srcStoich)
    setReactionDestNodeStoich(neti, reai, desti, destStoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


# TODO allow modification of this list later
# TODO make note that neti is useless here. Probably just remove the argument later
# Also need to change getCompositeShapeAt
def getListOfCompositeShapes(neti: int):
    return [f.produce() for f in shapeFactories]


def getCompositeShapeAt(neti: int, shapei: int):
    return shapeFactories[shapei].produce()


def getNodeShape(neti: int, nodei: int) -> CompositeShape:
    return copy.copy(_getConcreteNode(neti, nodei).shape)


def getNodeShapeIndex(neti: int, nodei: int) -> int:
    return _getConcreteNode(neti, nodei).shapei


def setNodeShapeIndex(neti: int, nodei: int, shapei: int, preserve_common_fields=True):
    '''If preserve_common_fields is True, then preserve common field values such as fill_color,
    if applicable.
    '''
    net = _getNetwork(neti)
    node = _getConcreteNode(neti, nodei)
    node.shapei = shapei
    shp = shapeFactories[shapei].produce()

    if preserve_common_fields and len(node.shape.items) == len(shp.items):
        for index, prim in enumerate(node.shape.items):
            fill = node.shape.items[index][0].fill_color
            borderc = node.shape.items[index][0].border_color
            borderw = node.shape.items[index][0].border_width
            node.shape.items[index] = shp.items[index]
            setNodePrimitiveProperty(neti, nodei, index, "fill_color", fill)
            setNodePrimitiveProperty(neti, nodei, index, "border_color", borderc)
            setNodePrimitiveProperty(neti, nodei, index, "border_width", 1.0 * borderw)
    else:
        node.shape = shp


def setNodePrimitiveProperty(neti: int, nodei: int, prim_index: int, prop_name: str, prop_value: Any):
    '''Set an individual property of a node's primitive.

    Args:
        neti:       The network index
        nodei:      The node index
        prim_index: The index of the primitive, in the node's shape. If -1, then update the text
                    primitive instead.
        prop_name:  The name of the primitive's property.
        prop_value: The value of the primitives's property
    '''
    node = _getConcreteNode(neti, nodei)
    if prim_index >= len(node.shape.items) or prim_index < -1:
        raise ValueError('Primitive index out of range for the shape of node {} in network {}'.format(nodei, neti))

    if prim_index == -1:
        primitive, _transform = node.shape.text_item
    else:
        primitive, _transform = node.shape.items[prim_index]

    if prop_name not in primitive.__dataclass_fields__:
        raise ValueError('`{}` is not a property of primitive `{}`'.format(
            prop_name, primitive.__class__.__name__))

    field = primitive.__dataclass_fields__[prop_name]
    # ensure that the assigned type is correct
    if not isinstance(prop_value, field.type):
        raise ValueError(f'Could not set primitive property `{prop_name}` of node {nodei} at '
                         f'primitive index {prim_index}. Expected object of type `{field.type.__name__}`; got '
                         f'`{prop_value}`(`{type(prop_value).__name__}`) instead. Note: the primitive '
                         f'is of type `{type(primitive).__name__}`.')

    # This is not very safe, but this is very simple to implement, so it shall be like this for now
    setattr(primitive, prop_name, prop_value)



def CreateUniBi(neti: int, reaID: str, rateLaw: str, srci: int, dest1i: int, dest2i: int, srcStoich: float, dest1Stoich: float, dest2Stoich: float):
    startGroup()
    createReaction(neti, reaID, [srci], [dest1i, dest2i])
    reai = getReactionIndex(neti, reaID)

    setReactionSrcNodeStoich(neti, reai, srci, srcStoich)
    setReactionDestNodeStoich(neti, reai, dest1i, dest1Stoich)
    setReactionDestNodeStoich(neti, reai, dest2i, dest2Stoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def CreateBiUni(neti: int, reaID: str, rateLaw: str, src1i: int, src2i: int, desti: int, src1Stoich: float, src2Stoich: float, destStoich: float):
    startGroup()
    createReaction(neti, reaID, [src1i, src2i], [desti])
    reai = getReactionIndex(neti, reaID)

    setReactionSrcNodeStoich(neti, reai, src1i, src1Stoich)
    setReactionSrcNodeStoich(neti, reai, src2i, src2Stoich)
    setReactionDestNodeStoich(neti, reai, desti, destStoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def CreateBiBi(neti: int, reaID: str, rateLaw: str, src1i: int, src2i: int, dest1i: int, dest2i: int, src1Stoich: float, src2Stoich: float, dest1Stoich: float, dest2Stoich: float):
    startGroup()
    createReaction(neti, reaID, [src1i, src2i], [dest1i, dest2i])
    reai = getReactionIndex(neti, reaID)

    setReactionSrcNodeStoich(neti, reai, src1i, src1Stoich)
    setReactionSrcNodeStoich(neti, reai, src2i, src2Stoich)
    setReactionDestNodeStoich(neti, reai, dest1i, dest1Stoich)
    setReactionDestNodeStoich(neti, reai, dest2i, dest2Stoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def reset():
    global stackFlag, errCode, networkDict, undoStack, redoStack, lastNetIndex
    stackFlag = True
    errCode = 0
    networkDict = TNetworkDict()
    undoStack = TStack()
    redoStack = TStack()
    lastNetIndex = 0


'''Code for serialization/deserialization.'''


class EnumField(fields.Field):
    def __init__(self, enum_class):
        super().__init__()
        choices = [entry.value for entry in enum_class]
        for choice in choices:
            if not isinstance(choice, str):
                raise ValueError('The enum class given to EnumField must have string values!')
        self.enum_class = enum_class
        self.str_field = fields.Str(validate=validate.OneOf(choices))

    def _serialize(self, entry, attr, obj, **kwargs):
        return entry.value

    def _deserialize(self, value, attr, data, **kwargs):
        self.str_field.validate(value)
        for entry in self.enum_class:
            if entry.value == value:
                return entry
        assert False, "Not supposed to reach here"

class ChoiceField(fields.Field):
    def __init__(self, choice_list):
        super().__init__()

        for choice in choice_list:
            if not isinstance(choice, ChoiceItem):
                raise ValueError("not choice item")
        self.choice_list = choice_list

    def _serialize(self, entry, attr, obj, **kwargs):
        for choice in self.choice_list:
            if entry == choice.value:
                return choice.text

    def _deserialize(self, value, attr, data, **kwargs):
        for choice in self.choice_list:
            if value == choice.text:
                return choice.value
        assert False, "No choice found"

class FontSchema(Schema):
    # TODO use this after implemented
    pointSize = Pixel()
    family = str  # TODO change to enum
    style: str
    weight: str
    name: str
    color: Color

class TransformSchema(Schema):
    translation = Dim2()
    rotation = Dim()
    scale = Dim2()

    @post_load
    def post_load(self, data: Any, **kwargs) -> Transform:
        return Transform(**data)


class PrimitiveSchema(Schema):
    name = fields.Str()
    fill_color = ColorField()
    border_color = ColorField()
    border_width = Dim()


class RectangleSchema(PrimitiveSchema):
    corner_radius = Dim()

    @post_load
    def post_load(self, data: Any, **kwargs) -> RectanglePrim:
        del data['name']
        return RectanglePrim(**data)


class CircleSchema(PrimitiveSchema):
    @post_load
    def post_load(self, data: Any, **kwargs) -> CirclePrim:
        del data['name']
        return CirclePrim(**data)


class PolygonSchema(PrimitiveSchema):
    #name = fields.Str()
    fill_color = ColorField()
    border_color = ColorField()
    border_width = Dim()
    corner_radius = Dim()
    radius = Dim()

class LineSchema(PrimitiveSchema):
    points = fields.Tuple(([Dim2()]*2))
    @post_load
    def post_load(self, data: Any, **kwargs) -> LinePrim:
        del data['name']
        return LinePrim(**data)


class TriangleSchema(PolygonSchema):
    points = fields.Tuple(((Dim2(),)*4))
    @post_load
    def post_load(self, data: Any, **kwargs) -> TrianglePrim:
        del data['name']
        return TrianglePrim(**data)


class HexagonSchema(PolygonSchema):
    points = fields.Tuple((Dim2(),)*7)
    @post_load
    def post_load(self, data: Any, **kwargs) -> HexagonPrim:
        del data['name']
        return HexagonPrim(**data)


def primitive_dump(base_obj, parent_obj):
    ret = {
        RectanglePrim.__name__: RectangleSchema,
        CirclePrim.__name__: CircleSchema,
        LinePrim.__name__: LineSchema,
        TrianglePrim.__name__: TriangleSchema,
        HexagonPrim.__name__: HexagonSchema

    }[base_obj.__class__.__name__]()
    return ret


primitive_schemas = {'rectangle':RectangleSchema(),
                     'circle': CircleSchema(),
                     'triangle': TriangleSchema(),
                     'line': LineSchema(),
                     'hexagon': HexagonSchema()}
def primitive_load(base_dict, parent_dict):
    return primitive_schemas[base_dict['name']]


primitiveField = PolyField(
    serialization_schema_selector=primitive_dump,
    deserialization_schema_selector=primitive_load,
    required=True,
)

class TextSchema(Schema):
    #name = fields.Str()
    bg_color = ColorField()
    font_color = ColorField()
    font_size = fields.Int()
    font_family = ChoiceField(FONT_FAMILY_CHOICES)
    font_style = ChoiceField(FONT_STYLE_CHOICES)
    font_weight = ChoiceField(FONT_WEIGHT_CHOICES)
    alignment = ChoiceField(TEXT_ALIGNMENT_CHOICES)

    @post_load
    def post_load(self, data: Any, **kwargs) -> TextPrim:
        return TextPrim(**data)

class CompositeShapeSchema(Schema):
    name = fields.Str()
    text_item = fields.Tuple((fields.Nested(TextSchema), fields.Nested(TransformSchema)))
    items = fields.List(fields.Tuple((primitiveField, fields.Nested(TransformSchema))))

    @post_load
    def post_load(self, data: Any, **kwargs) -> CompositeShape:
        return CompositeShape(**data)

class AbstractNodeSchema(Schema):
    index = fields.Int()
    id = fields.Str()
    position = Dim2()
    rectSize = Dim2()
    nodeLocked = fields.Bool()

    @post_dump
    def post_dump(self, data: Any, **kwargs):
        del data['index']
        return data


class NodeSchema(AbstractNodeSchema):
    floating = fields.Bool()
    compi = fields.Int(missing=-1)
    shape = fields.Nested(CompositeShapeSchema)

    @post_load
    def post_load(self, data: Any, **kwargs) -> TNode:
        shape_name = data['shape'].name
        # get shape index manually
        # If this fails, then somebody modified the shape name
        shapei = [s.name for s in shapeFactories].index(shape_name)
        data['shapei'] = shapei
        return TNode(**data)


class AliasSchema(AbstractNodeSchema):
    originalIdx = fields.Int()

    @post_load
    def post_load(self, data: Any, **kwargs):
        return TAliasNode(**data)


class SpeciesNode(Schema):
    """Represents a species in a reaction."""
    stoich = fields.Float()
    handlePos = Dim2()

    @post_load
    def post_load(self, data: Any, **kwargs) -> TSpeciesNode:
        return TSpeciesNode(**data)


class ReactionSchema(Schema):
    id = fields.Str()
    centerPos = Dim2(missing=None)
    rateLaw = fields.Str()
    reactants = fields.Dict(fields.Int(), fields.Nested(SpeciesNode))
    products = fields.Dict(fields.Int(), fields.Nested(SpeciesNode))
    fillColor = ColorField()
    thickness = Dim()
    centerHandlePos = Dim2()
    bezierCurves = fields.Bool()
    modifiers = fields.List(fields.Int())
    tipStyle = EnumField(ModifierTipStyle)

    @post_load
    def post_load(self, data: Any, **kwargs) -> TReaction:
        if 'modifiers' in data:
            data['modifiers'] = set(data['modifiers'])
        return TReaction(**data)

class CompartmentSchema(Schema):
    id = fields.Str()
    position = Dim2()
    rectSize = Dim2()
    nodes = fields.List(fields.Int())
    volume = Dim()
    fillColor = ColorField()
    outlineColor = ColorField()
    outlineThickness = Dim()

    @post_load
    def post_load(self, data: Any, **kwargs) -> TCompartment:
        return TCompartment(**data)


def node_or_alias_dump(base_obj, parent_obj):
    ret =  {
        TNode.__name__: NodeSchema,
        TAliasNode.__name__: AliasSchema,
    }[base_obj.__class__.__name__]()
    return ret


def node_or_alias_load(base_dict, parent_dict):
    if 'originalIdx' not in base_dict:
        return NodeSchema()
    else:
        return AliasSchema()


nodeOrAliasField = PolyField(
    serialization_schema_selector=node_or_alias_dump,
    deserialization_schema_selector=node_or_alias_load,
    required=True,
)

class NetworkSchema(Schema):
    id = fields.Str()
    nodes = fields.Mapping(fields.Int(), nodeOrAliasField)
    reactions = fields.Mapping(fields.Int(), fields.Nested(ReactionSchema))
    compartments = fields.Mapping(fields.Int(), fields.Nested(CompartmentSchema))

    @pre_load
    def pre_load(self, data: Any, **kwargs):
        # load serialization version
        # this records the version of the serialization. Whenever the serialization scheme is changed,
        # we update the version number, so that if a user is trying to load a network with an
        # older serialization version than the current application (or vice versa), we can either fail
        # to try to do some conversion.
        serial_version = data.get('serialVersion', 'pre-release')
        if serial_version != SERIAL_VERSION:
            # we have a mismatch
            print(("Warning: loaded network has serial version '{}', which does not match that of "
                   "the application: '{}'").format(serial_version, SERIAL_VERSION))
        if 'serialVersion' in data:
            del data['serialVersion']

        # populate the index field of nodes. This is a redundancy, so we don't expect this field
        # to be serialized/deserialized
        for nodei, nodedata in data['nodes'].items():
            nodedata['index'] = int(nodei)

        return data

    @post_load
    def post_load(self, data: Any, **kwargs) -> TNetwork:
        return TNetwork(**data)

    @post_dump
    def post_dump(self, data, **kwargs):
        data['serialVersion'] = SERIAL_VERSION
        return data


net_schema = NetworkSchema()


def dumpNetwork(neti: int):
    """Dump the network into an object and return it."""
    # TODO don't construct NetworkSchema every time.
    net = _getNetwork(neti)
    return net_schema.dump(net)


def loadNetwork(net_object) -> int:
    """Load the network object (laoded directly from JSON) and add it, returning the network index.

    Note:
        For now this overwrites the network at index 0.
    """
    # NOTE marshmallow::load does not guarantee that the input object is not modified. Therefore,
    # we need to make a deepcopy
    obj_copy = copy.deepcopy(net_object)
    net = net_schema.load(obj_copy)
    clearNetworks()
    _addNetwork(net)
    return 0


def validateState():
    assert undoStack is not None
    assert redoStack is not None

    net_ids = [net.id for net in networkDict.values()]
    assert len(net_ids) == len(set(net_ids)), "duplicate network IDs"

    assert isinstance(networkDict, dict)
    for neti, net in networkDict.items():
        assert isinstance(neti, int)
        assert isinstance(net, TNetwork)

        validateNodes(net.nodes)
        # TODO validate reactions, compartments, and cross-validate


def validateNodes(nodes: Dict[int, TAbstractNode]):
    assert isinstance(nodes, dict)

    for nodei, node in nodes.items():
        assert isinstance(nodei, int)
        assert isinstance(node, TNode) or isinstance(node, TAliasNode)

        assert isinstance(node, TNode) or isinstance(node, TAliasNode), 'unexpected type: ' + type(node)

    cnodes = [n for n in nodes.values() if isinstance(n, TNode)]
    aliases = [n for n in nodes.values() if isinstance(n, TAliasNode)]

    node_ids = [n.id for n in cnodes]
    assert len(node_ids) == len(set(node_ids)), "duplicate node IDs"

    # assert alias references are good
    for alias in aliases:
        assert isinstance(alias.originalIdx, int) and alias.originalIdx >= 0
        assert alias.originalIdx in nodes and isinstance(nodes[alias.originalIdx], TNode)

    for cnode in cnodes:
        assert isinstance(cnode.floating, bool)

    for node in nodes.values():
        node: TAbstractNode
        assert isinstance(node.nodeLocked, bool)
        assert isinstance(node.compi, int)
        assert isinstance(node.position, Vec2) and node.position.x >= 0 and node.position.y >= 0
        assert isinstance(node.rectSize, Vec2) and node.rectSize.x >= 0 and node.rectSize.y >= 0
        # TODO assert node.compi in net.compartments OUTSIDE of this function

    # TODO assert more properties

