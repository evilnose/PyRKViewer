"""
Iodine Network Object Model.

Original author:    RJ Zhou
"Forked" from:      https://github.com/zrj26/go-NOM
Adapted by:         Gary Geng
"""
from __future__ import annotations
import copy
import json
from typing import Dict, Set, Tuple, List


class TNode(object):
    id: str
    x: float
    y: float
    w: float
    h: float
    fillColor: TColor
    outlineColor: TColor
    outlineThickness: float
    fontPointSize: int
    fontFamily: str  # TODO change to enum
    fontStyle: str
    fontWeight: str
    fontName: str
    fontColor: TColor

    def __init__(self, nodeID: str, x: float, y: float, w: float, h: float):
        self.id = nodeID
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.fillColor = TColor(255, 150, 80, 255)
        self.outlineColor = TColor(255, 100, 80, 255)
        self.outlineThickness = 3.0
        self.fontPointSize = 20
        self.fontFamily = "default"
        self.fontStyle = "normal"
        self.fontWeight = "default"
        self.fontName = ""
        self.fontColor = TColor(0, 0, 0, 255)


class TNetwork:
    magicIDentifier: str
    id: str
    nodes: Dict[int, TNode]
    reactions: Dict[int, TReaction]
    lastNodeIdx: int
    lastReactionIdx: int

    def __init__(self, netID: str):
        self.magicIDentifier = "NM01"
        self.id = netID
        self.nodes = dict()
        self.reactions = dict()
        self.lastNodeIdx = 0
        self.lastReactionIdx = 0

    def addNode(self, node: TNode):
        self.nodes[self.lastNodeIdx] = node
        self.lastNodeIdx += 1

    def addReaction(self, rea: TReaction):
        self.reactions[self.lastReactionIdx] = rea
        self.lastReactionIdx += 1

    def getFreenodes(self) -> Set[int]:
        """
        get list of nodes not in any existed reactions
        """
        reaNodeSet = set()
        for reaction in self.reactions.values():
            reaNodeSet |= set(reaction.srcDict.keys()) | set(reaction.destDict.keys())

        return set(ni for ni in self.nodes.keys() if ni not in reaNodeSet)


class TReaction(object):
    id: str
    rateLaw: str
    srcDict: Dict[int, TSpeciesNode]
    destDict: Dict[int, TSpeciesNode]
    fillColor: TColor
    thickness: float
    centerHandleX: float
    centerHandleY: float

    def __init__(self, reaID: str):
        self.id = reaID
        self.rateLaw = ""
        self.srcDict = dict()
        self.destDict = dict()
        self.fillColor = TColor(255, 150, 80, 255)
        self.thickness = 3.0
        self.centerHandleX = 0.0
        self.centerHandleY = 0.0


class TSpeciesNode(object):
    stoich: float
    handleX: float
    handleY: float

    def __init__(self, stoich: float):
        self.stoich = stoich
        self.handleX = 0.0
        self.handleY = 0.0


class TColor(object):
    r: int
    g: int
    b: int
    h: int

    def __init__(self, r: int, g: int, b: int, a: int):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


class TStack:
    items: List[TNetworkDict]
    def __init__(self):
        self.items = []

    def isEmpty(self):
        return self.items == []

    def push(self, netDict: TNetworkDict):
        theSet = copy.deepcopy(netDict)
        self.items.append(theSet)

    def pop(self):
        return self.items.pop()


class TNetworkDict(Dict[int, TNetwork], dict):
    def __init__(self):
        super().__init__()
        self.lastNetIndex = 0


class Error(Exception):
    """Base class for other exceptions"""
    pass


class IDNotFoundError(Error):
    pass


class IDRepeatError(Error):
    pass


class NodeNotFreeError(Error):
    pass


class NetIndexOutOfRangeError(Error):
    pass


class ReactionIndexNotFoundError(Error):
    pass


class NodeIndexNotFoundError(Error):
    pass


class StoichError(Error):
    pass


class StackEmptyError(Error):
    pass


class JSONError(Error):
    pass


class FileError(Error):
    pass


class VariableOutOfRangeError(Error):
    pass


errorDict = {
    0: "ok",
    -1: "other",
    -2: "id not found: ",
    -3: "id repeat: ",
    -4: "node is not free: ",
    -5: "net index out of range: ",
    -6: "reaction index does not exist: ",
    -7: "node index does not exist: ",
    -8: "wrong stoich: stoich has to be positive: ",
    -9: "stack is empty",
    -10: "Json convert error",
    -11: "File error",
    -12: "Variable out of range: "
}


ExceptionDict = {
    -2: IDNotFoundError,
    -3: IDRepeatError,
    -4: NodeNotFreeError,
    -5: NetIndexOutOfRangeError,
    -6: ReactionIndexNotFoundError,
    -7: NodeIndexNotFoundError,
    -8: StoichError,
    -9: StackEmptyError,
    -10: JSONError,
    -11: FileError,
    -12: VariableOutOfRangeError
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
networkDict: TNetworkDict = TNetworkDict()
netSetStack: TStack = TStack()
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
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if netSetStack.isEmpty():
        errCode = -9
    else:
        redoStack.push(networkDict)
        networkDict = netSetStack.pop()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])


def redo():
    """
    Redo redo
    errCode: -9: stack is empty
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    if redoStack.isEmpty():
        errCode = -9
    else:
        netSetStack.push(networkDict)
        networkDict = redoStack.pop()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])


def startGroup():
    """
    StartGroup used at the start of a group operaction or secondary function.
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    redoStack = TStack()
    netSetStack.push(networkDict)
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
    global stackFlag, errCode, networkDict, netSetStack, redoStack, lastNetIndex
    errCode = 0
    for network in networkDict.values():
        if network.id == netID:
            errCode = -3
            break
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], netID)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkDict)

        newNetwork = TNetwork(netID)
        networkDict[lastNetIndex] = newNetwork
        lastNetIndex += 1


def getNetworkIndex(netID: str) -> int:
    """
    getNetworkIndex
    return: -2: net id can't find
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = -2

    for i, net in networkDict.items():
        if net.id == netID:
            errCode = 0
            return i

    raise ExceptionDict[errCode](errorDict[errCode], netID)


def saveNetworkAsJSON(neti: int, fileName: str):
    """
    SaveNetworkAsJSON SaveNetworkAsJSON
    errCode: -5: net index out of range
    -10: "Json convert error", -11: "File error"
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
        raise ExceptionDict[errCode](errorDict[errCode], neti, fileName)
    else:
        data2 = json.dumps(networkDict[neti],
                           sort_keys=True, indent=4, separators=(',', ': '))
        print(data2)


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
#         redoStack = TNetSetStack{
#         netSetStack.push(networkDict)

#     networkDict = append(networkDict, newNet)
#     # fmt.Println(networkDict)
#     return errCode


def deleteNetwork(neti: int):
    """
    DeleteNetwork DeleteNetwork
    errCode: -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkDict)

        del networkDict[neti]


def clearNetworks():
    global stackFlag, errCode, networkDict, netSetStack, redoStack, lastNetIndex
    errCode = 0
    if stackFlag:
        redoStack = TStack()
        netSetStack.push(networkDict)
    networkDict = TNetworkDict()
    lastNetIndex = 0


def getNumberOfNetworks():
    return len(networkDict)


def getNetworkID(neti: int):
    """
    GetNetworkID GetID of network
    errCode: -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        return networkDict[neti].id


def getListOfNetworks() -> List[int]:
    return list(networkDict.keys())


def addNode(neti: int, nodeID: str, x: float, y: float, w: float, h: float):
    """
    AddNode adds a node to the network
    errCode - 3: id repeat, 0: ok
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    try:
        if neti not in networkDict:
            errCode = -5
            return
        else:
            n = networkDict[neti]
            for i in n.nodes.values():
                if i.id == nodeID:
                    errCode = -3
                    return
        if errCode == 0:
            if x < 0 or y < 0 or w <= 0 or h <= 0:
                errCode = -12
                return

        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkDict)
        newNode = TNode(nodeID, x, y, w, h)
        n.addNode(newNode)
        networkDict[neti] = n
    finally:
        if errCode < 0:
            raise ExceptionDict[errCode](
                errorDict[errCode], neti, nodeID, x, y, w, h)


def getNodeIndex(neti: int, nodeID: str):
    """
    GetNodeIndex get node index by id
    errCode: -2: node id not found,
    -5: net index out of range
    return: >=0
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = -2
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        for i, node, in n.nodes.items():
            if node.id == nodeID:
                errCode = 0
                return i

    assert errCode < 0
    raise ExceptionDict[errCode](errorDict[errCode], neti, nodeID)


def deleteNode(neti: int, nodei: int):
    """
    DeleteNode delete the node with index
    return: -7: node index out of range, -4: node is not free
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = -4
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            s = n.getFreenodes()
            if nodei in s:
                errCode = 0
                if stackFlag:
                    redoStack = TStack()
                    netSetStack.push(networkDict)
                del n.nodes[nodei]
                networkDict[neti] = n
                return

    assert errCode < 0
    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def clearNetwork(neti: int):
    """
    ClearNetwork clear all nodes and reactions in this network
    errCode: -5:  net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkDict)
        networkDict[neti].nodes.clear()
        networkDict[neti].reactions.clear()


def getNumberOfNodes(neti: int):
    """
    GetNumberOfNodes get the number of nodes in the current network
    num: >= -5:  net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        n = networkDict[neti]
        return len(n.nodes)


def getNodeCenter(neti: int, nodei: int):
    """
    GetNodeCenter Get the X and  Y coordinate of the Center of node
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            X = round(n.nodes[nodei].x + n.nodes[nodei].w*0.5, 2)
            Y = round(n.nodes[nodei].y + n.nodes[nodei].h*0.5, 2)
            return (X, Y)

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeID(neti: int, nodei: int):
    """
    GetNodeID Get the id of the node
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return n.nodes[nodei].id

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getListOfNodeIDs(neti: int) -> List[str]:
    if neti not in networkDict:
        errCode = -5
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    return [n.id for n in networkDict[neti].nodes.values()]


def getNodeCoordinateAndSize(neti: int, nodei: int):
    """
    getNodeCoordinateAndSize get the x,y,w,h of the node
    errCode:-7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            X = round(n.nodes[nodei].x, 2)
            Y = round(n.nodes[nodei].y, 2)
            W = round(n.nodes[nodei].w, 2)
            H = round(n.nodes[nodei].h, 2)
            return (X, Y, W, H)

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


# TODO make this return TColor
def getNodeFillColor(neti: int, nodei: int):
    """
    getNodeFillColor  rgba tulple format, rgb range int[0,255] alpha range float[0,1]
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return (n.nodes[nodei].fillColor.r, n.nodes[nodei].fillColor.g,
                    n.nodes[nodei].fillColor.b,
                    float(n.nodes[nodei].fillColor.a)/255)

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFillColorRGB(neti: int, nodei: int):
    """
    getNodeFillColorRGB getNodeFillColor rgb int format
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0

    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            color1 = n.nodes[nodei].fillColor.r
            color1 = (color1 << 8) | n.nodes[nodei].fillColor.g
            color1 = (color1 << 8) | n.nodes[nodei].fillColor.b
            return color1

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFillColorAlpha(neti: int, nodei: int):
    """
    getNodeFillColorAlpha getNodeFillColor alpha value(float)
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return float(n.nodes[nodei].fillColor.a)/255

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeOutlineColor(neti: int, nodei: int):
    """
    getNodeOutlineColor rgba tulple format, rgb range int[0,255] alpha range float[0,1]
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return (n.nodes[nodei].outlineColor.r, n.nodes[nodei].outlineColor.g,
                    n.nodes[nodei].outlineColor.b,
                    float(n.nodes[nodei].outlineColor.a)/255)

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeOutlineColorRGB(neti: int, nodei: int):
    """
    getNodeOutlineColorRGB getNodeOutlineColor rgb int format
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0

    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            color1 = n.nodes[nodei].outlineColor.r
            color1 = (color1 << 8) | n.nodes[nodei].outlineColor.g
            color1 = (color1 << 8) | n.nodes[nodei].outlineColor.b
            return color1

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeOutlineColorAlpha(neti: int, nodei: int):
    """
    getNodeOutlineColorAlpha getNodeOutlineColor alpha value(float)
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0

    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return float(n.nodes[nodei].outlineColor.a)/255

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeOutlineThickness(neti: int, nodei: int):
    """
    getNodeOutlineThickness
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return n.nodes[nodei].outlineThickness

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFontPointSize(neti: int, nodei: int):
    """
    getNodeFontPointSize
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return n.nodes[nodei].fontPointSize

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFontFamily(neti: int, nodei: int):
    """
    getNodeFontFamily
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return n.nodes[nodei].fontFamily

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFontStyle(neti: int, nodei: int):
    """
    getNodeFontStyle
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return n.nodes[nodei].fontStyle

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFontWeight(neti: int, nodei: int):
    """
    getNodeFontWeight
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return n.nodes[nodei].fontWeight

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFontName(neti: int, nodei: int):
    """
    getNodeFontName
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return n.nodes[nodei].fontName

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFontColor(neti: int, nodei: int):
    """
    getNodeFontColor rgba tulple format, rgb range int[0,255] alpha range float[0,1]
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return (n.nodes[nodei].fontColor.r, n.nodes[nodei].fontColor.g,
                    n.nodes[nodei].fontColor.b,
                    float(n.nodes[nodei].fontColor.a)/255)

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFontColorRGB(neti: int, nodei: int):
    """
    getNodeFontColorRGB getNodeFontColor rgb int format
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0

    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            color1 = n.nodes[nodei].fontColor.r
            color1 = (color1 << 8) | n.nodes[nodei].fontColor.g
            color1 = (color1 << 8) | n.nodes[nodei].fontColor.b
            return color1

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def getNodeFontColorAlpha(neti: int, nodei: int):
    """
    getNodeFontColorAlpha getNodeFontColor alpha value(float)
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0

    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            return float(n.nodes[nodei].fontColor.a)/255

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def setNodeID(neti: int, nodei: int, newID: str):
    """
    setNodeID set the id of a node
    errCode -3: id repeat
    -5: net index out of range
    -7: node index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        net = networkDict[neti]
        if nodei not in net.nodes.keys():
            errCode = -7
        else:
            if any((n.id == newID for n in net.nodes.values())):
                errCode = -3
            else:
                if stackFlag:
                    redoStack = TStack()
                    netSetStack.push(networkDict)
                net.nodes[nodei].id = newID
                return
    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, newID)


def setNodeCoordinate(neti: int, nodei: int, x: float, y: float):
    """
    setNodeCoordinate setNodeCoordinate
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif x < 0 or y < 0:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].x = x
            n.nodes[nodei].y = y
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, x, y)


def setNodeSize(neti: int, nodei: int, w: float, h: float):
    """
    setNodeSize setNodeSize
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif w <= 0 or h <= 0:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].w = w
            n.nodes[nodei].h = h
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, w, h)


def setNodeFillColorRGB(neti: int, nodei: int, r: int, g: int, b: int):
    """
    setNodeFillColorRGB setNodeFillColorRGB
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].fillColor.r = r
            n.nodes[nodei].fillColor.g = g
            n.nodes[nodei].fillColor.b = b
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei,  r, g, b)


def setNodeFillColorAlpha(neti: int, nodei: int, a: float):
    """
    setNodeFillColorAlpha setNodeFillColorAlpha
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif a < 0 or a > 1:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            networkDict[neti].nodes[nodei].fillColor.a = int(a*255)
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, a)


def setNodeOutlineColorRGB(neti: int, nodei: int, r: int, g: int, b: int):
    """
    setNodeOutlineColorRGB setNodeOutlineColorRGB
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].outlineColor.r = r
            n.nodes[nodei].outlineColor.g = g
            n.nodes[nodei].outlineColor.b = b
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei,  r, g, b)


def setNodeOutlineColorAlpha(neti: int, nodei: int, a: float):
    """
    setNodeOutlineColorAlpha setNodeOutlineColorAlpha, alpha is a float between 0 and 1
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif a < 0 or a > 1:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            A1 = int(a * 255)
            n.nodes[nodei].outlineColor.a = A1
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, a)


def setNodeOutlineThickness(neti: int, nodei: int, thickness: float):
    """
    setNodeOutlineThickness setNodeOutlineThickness
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif thickness <= 0:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].outlineThickness = thickness
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, thickness)


def setNodeFontPointSize(neti: int, nodei: int, fontPointSize: int):
    """
    setNodeFontPointSize setNodeFontPointSize
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif fontPointSize <= 0:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].fontPointSize = fontPointSize
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, fontPointSize)


def setNodeFontFamily(neti: int, nodei: int, fontFamily: str):
    """
    setNodeFontFamily set the fontFamily of a node
    errCode
    -5: net index out of range
    -7: node index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif fontFamily not in fontFamilyDict:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].fontFamily = fontFamily
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, fontFamily)


def setNodeFontStyle(neti: int, nodei: int, fontStyle: str):
    """
    setNodeFontStyle set the fontStyle of a node
    errCode
    -5: net index out of range
    -7: node index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif fontStyle not in fontStyleDict:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].fontStyle = fontStyle
            return
    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, fontStyle)


def setNodeFontWeight(neti: int, nodei: int, fontWeight: str):
    """
    setNodeFontWeight set the fontWeight of a node
    errCode
    -5: net index out of range
    -7: node index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif fontWeight not in fontWeightDict:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].fontWeight = fontWeight
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, fontWeight)


def setNodeFontName(neti: int, nodei: int, fontName: str):
    """
    setNodeFontName set the fontName of a node
    errCode
    -5: net index out of range
    -7: node index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].fontName = fontName
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, fontName)


def setNodeFontColorRGB(neti: int, nodei: int, r: int, g: int, b: int):
    """
    setNodeFontColorRGB setNodeFontColorRGB
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            n.nodes[nodei].fontColor.r = r
            n.nodes[nodei].fontColor.g = g
            n.nodes[nodei].fontColor.b = b
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei,  r, g, b)


def setNodeFontColorAlpha(neti: int, nodei: int, a: float):
    """
    setNodeFontColorAlpha setNodeFontColorAlpha
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        n = networkDict[neti]
        if nodei not in n.nodes.keys():
            errCode = -7
        elif a < 0 or a > 1:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            networkDict[neti].nodes[nodei].fontColor.a = int(a*255)
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, a)


def createReaction(neti: int, reaID: str):
    """
    createReaction create an empty reacton
    errCode: -3: id repeat
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        if any((r.id == reaID for r in networkDict[neti].reactions.values())):
            errCode = -3
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            newReact = TReaction(reaID)
            networkDict[neti].addReaction(newReact)
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reaID)


def getReactionIndex(neti: int, reaID: str):
    """
    getReactionIndex get reaction index by id
    return: -2: id can't find, >=0: ok
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        errCode = -2
        for i, r in networkDict[neti].reactions.items():
            if r.id == reaID:
                errCode = 0
                return i

    raise ExceptionDict[errCode](errorDict[errCode], neti, reaID)


def deleteReaction(neti: int, reai: int):
    """
    deleteReaction delete the reaction with index
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            del networkDict[neti].reactions[reai]
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def clearReactions(neti: int):
    """
    clearReactions clear all reactions in this network
    errCode: -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkDict)
        networkDict[neti].reactions.clear()


def getNumberOfReactions(neti: int):
    """
    getNumberOfReactions get the number of reactions in the current Reactionset
    return: >=0: ok, -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    if neti not in networkDict:
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        r = networkDict[neti].reactions
        return len(r)


def getReactionID(neti: int, reai: int):
    """
    getReactionID get the id of Reaction
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return r[reai].id

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getListOfReactionIDs(neti: int) -> List[str]:
    if neti not in networkDict:
        errCode = -5
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    return [r.id for r in networkDict[neti].reactions.values()]


def getReactionRateLaw(neti: int, reai: int):
    """
    getReactionRateLaw get the ratelaw of Reaction
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return r[reai].rateLaw

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getReactionFillColor(neti: int, reai: int):
    """
    getReactionFillColor rgba tulple format, rgb range int[0,255] alpha range float[0,1]
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return (r[reai].fillColor.r, r[reai].fillColor.g, r[reai].fillColor.b, float(r[reai].fillColor.a)/255)

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getReactionFillColorRGB(neti: int, reai: int):
    """
    getReactionFillColorRGB getReactionFillColorRGB
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
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

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getReactionFillColorAlpha(neti: int, reai: int):
    """
    getReactionFillColorAlpha getReactionFillColorAlpha
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
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

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getReactionLineThickness(neti: int, reai: int):
    """
    getReactionLineThickness getReactionLineThickness
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return r[reai].thickness

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getReactionCenterHandlePosition(neti: int, reai: int):
    """
    getReactionCenterHandlePosition getReactionCenterHandlePosition
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return (round(r[reai].centerHandleX, 2), round(r[reai].centerHandleY, 2))

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getReactionSrcNodeStoich(neti: int, reai: int, srcNodeIdx: int):
    """
    getReactionSrcNodeStoich get the SrcNode stoichiometry of Reaction
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif srcNodeIdx not in r[reai].srcDict:
            errCode = -2
        else:
            return r[reai].srcDict[srcNodeIdx].stoich
    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeIdx)


def getReactionDestNodeStoich(neti: int, reai: int, destNodeIdx: int):
    """
    getReactionDestNodeStoich get the DestNode stoichiometry of Reaction
    return: positive float : ok, -6: reaction index out of range, -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif destNodeIdx not in r[reai].destDict:
            errCode = -2
        else:
            s = r[reai].destDict[destNodeIdx]
            return s.stoich
    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, destNodeIdx)


def getReactionSrcNodeHandlePosition(neti: int, reai: int, srcNodeIdx: int):
    """
    getReactionSrcNodeHandlePosition get the SrcNode HandlePosition of Reaction
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif srcNodeIdx not in r[reai].srcDict:
            errCode = -2
        else:
            return (round(r[reai].srcDict[srcNodeIdx].handleX, 2),
                    round(r[reai].srcDict[srcNodeIdx].handleY, 2))

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeIdx)


def getReactionDestNodeHandlePosition(neti: int, reai: int, destNodeIdx: int):
    """
    getReactionDestNodeStoich get the DestNode HandlePosition of Reaction
    return: positive float : ok, -6: reaction index out of range, -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif destNodeIdx not in r[reai].destDict:
            errCode = -2
        else:
            return (round(r[reai].destDict[destNodeIdx].handleX, 2),
                    round(r[reai].destDict[destNodeIdx].handleY, 2))

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, destNodeIdx)


def getNumberOfSrcNodes(neti: int, reai: int):
    """
    getNumberOfSrcNodes get the SrcNode length of Reaction
    return: non-negative int: ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return len(r[reai].srcDict)

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getNumberOfDestNodes(neti: int, reai: int):
    """
    getNumberOfDestNodes get the DestNode length of Reaction
    return: non-negative int: ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            return len(r[reai].destDict)

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getListOfReactionSrcNodes(neti: int, reai: int) -> List[int]:
    """
    getListOfReactionSrcNodes getListOfReactionSrcNodes in alphabetical order
    return: non-empty slice : ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        reactions = networkDict[neti].reactions
        if reai not in reactions:
            errCode = -6
        else:
            list1 = []
            for k in reactions[reai].srcDict:
                list1.append(k)
            list1.sort()
            return list1

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def getListOfReactionDestNodes(neti: int, reai: int) -> List[int]:
    """
    getListOfReactionDestNodes getListOfReactionDestNodes in alphabetical order
    return: non-empty slice : ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            list1 = []
            for k in r[reai].destDict:
                list1.append(k)
            list1.sort()
            return list1

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


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


def addSrcNode(neti: int, reai: int, nodei: int, stoich: float):
    """
    addSrcNode add node and Stoich to reactionlist
    errCode:  0:ok,
    -5: net index out of range
    -6: reaction index out of range,
    -7: node index out of range
    -8: "wrong stoich: stoich has to be positive"
    -3: id repeat
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif nodei not in networkDict[neti].nodes:
            errCode = -7
        elif stoich <= 0.0:
            errCode = -8
        else:
            rea = r[reai]
            srcNodeIdx = nodei
            if srcNodeIdx in r[reai].srcDict:
                errCode = -3
            else:
                if stackFlag:
                    redoStack = TStack()
                    netSetStack.push(networkDict)
                rea.srcDict[srcNodeIdx] = TSpeciesNode(stoich)
                networkDict[neti].reactions[reai] = rea
                return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, nodei, stoich)


def addDestNode(neti: int, reai: int, nodei: int, stoich: float):
    """
    addDestNode add node and Stoich to reactionlist
    errCode:  0:ok,
    -5: net index out of range
    -6: reaction index out of range,
    -7: node index out of range
    -8: "wrong stoich: stoich has to be positive"
    -3: id repeat
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif nodei not in networkDict[neti].nodes:
            errCode = -7
        elif stoich <= 0:
            errCode = -8
        else:
            rea = r[reai]
            if nodei in rea.destDict:
                errCode = -3
            else:
                if stackFlag:
                    redoStack = TStack()
                    netSetStack.push(networkDict)
                rea.destDict[nodei] = TSpeciesNode(stoich)
                networkDict[neti].reactions[reai] = rea
                return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, nodei, stoich)


def deleteSrcNode(neti: int, reai: int, srcNodeIdx: int):
    """
    deleteSrcNode delete src nodes by id(ID).
    errCode: -6: reaction index out of range,
    -5: net index out of range
    -2: id not found
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            rea = r[reai]
            if srcNodeIdx not in rea.srcDict:
                errCode = -2
            else:
                if stackFlag:
                    redoStack = TStack()
                    netSetStack.push(networkDict)
                del rea.srcDict[srcNodeIdx]
                networkDict[neti].reactions[reai] = rea
                return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeIdx)


def deleteDestNode(neti: int, reai: int, destNodeIdx: int):
    """
    deleteDestNode delete all dest nodes by id
    errCode: -6: reaction index out of range,
    -5: net index out of range
    -2: id not found
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            rea = r[reai]
            if destNodeIdx not in rea.destDict:
                errCode = -2
            else:
                if stackFlag:
                    redoStack = TStack()
                    netSetStack.push(networkDict)
                del rea.destDict[destNodeIdx]
                return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, destNodeIdx)


def setReactionID(neti: int, reai: int, newID: str):
    """
    setReactionID edit id of reaction
    errCode: 0:ok, -6: reaction index out of range
    -5: net index out of range
    -3: id repeat
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
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
                if stackFlag:
                    redoStack = TStack()
                    netSetStack.push(networkDict)
                networkDict[neti].reactions[reai].id = newID
                return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, newID)


def setRateLaw(neti: int, reai: int, rateLaw: str):
    """
    setRateLaw edit rate law of reaction
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            networkDict[neti].reactions[reai].rateLaw = rateLaw
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, rateLaw)


def setReactionSrcNodeStoich(neti: int, reai: int, srcNodeIdx: int, newStoich: float):
    """
    setReactionSrcNodeStoich edit Stoich by Reaction srcNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    -8: wrong stoich
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif srcNodeIdx not in r[reai].srcDict:
            errCode = -2
        elif newStoich <= 0.0:
            errCode = -8
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            networkDict[neti].reactions[reai].srcDict[srcNodeIdx].stoich = newStoich
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeIdx, newStoich)


def setReactionDestNodeStoich(neti: int, reai: int, destNodeIdx: int, newStoich: float):
    """
    setReactionDestNodeStoich edit Stoich by Reaction destNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    -8: wrong stoich
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif destNodeIdx not in r[reai].destDict:
            errCode = -2
        elif newStoich <= 0.0:
            errCode = -8
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            networkDict[neti].reactions[reai].destDict[destNodeIdx].stoich = newStoich
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, destNodeIdx, newStoich)


def setReactionSrcNodeHandlePosition(neti: int, reai: int, srcNodeIdx: int, handleX: float, handleY: float):
    """
    setReactionSrcNodeHandlePosition edit HandlePosition by Reaction srcNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif srcNodeIdx not in r[reai].srcDict:
            errCode = -2
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            networkDict[neti].reactions[reai].srcDict[srcNodeIdx].handleX = handleX
            networkDict[neti].reactions[reai].srcDict[srcNodeIdx].handleY = handleY
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeIdx, handleX, handleY)


def setReactionDestNodeHandlePosition(neti: int, reai: int, destNodeIdx: int, handleX: float, handleY: float):
    """
    setReactionDestNodeHandlePosition edit HandlePosition by Reaction destNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        r = networkDict[neti].reactions
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif destNodeIdx not in r[reai].destDict:
            errCode = -2
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            networkDict[neti].reactions[reai].destDict[destNodeIdx].handleX = handleX
            networkDict[neti].reactions[reai].destDict[destNodeIdx].handleY = handleY
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, destNodeIdx, handleX, handleY)


def setReactionFillColorRGB(neti: int, reai: int, R: int, G: int, B: int):
    """
    setReactionFillColorRGB setReactionFillColorRGB
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
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
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            r[reai].fillColor.r = R
            r[reai].fillColor.g = G
            r[reai].fillColor.b = B
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, R, G, B)


def setReactionFillColorAlpha(neti: int, reai: int, a: float):
    """
    setReactionFillColorAlpha setReactionFillColorAlpha
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
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
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            A1 = int(a * 255)
            r[reai].fillColor.a = A1
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, a)


def setReactionLineThickness(neti: int, reai: int, thickness: float):
    """
    setReactionLineThickness setReactionLineThickness
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        if reai not in networkDict[neti].reactions:
            errCode = -6
        elif thickness <= 0:
            errCode = -12
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            networkDict[neti].reactions[reai].thickness = thickness
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, thickness)


def setReactionCenterHandlePosition(neti: int, reai: int, centerHandleX: float, centerHandleY: float):
    """
    setReactionCenterHandlePosition setReactionCenterHandlePosition
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkDict, netSetStack, redoStack
    errCode = 0
    if neti not in networkDict:
        errCode = -5
    else:
        if reai not in networkDict[neti].reactions:
            errCode = -6
        else:
            if stackFlag:
                redoStack = TStack()
                netSetStack.push(networkDict)
            networkDict[neti].reactions[reai].centerHandleX = centerHandleX
            networkDict[neti].reactions[reai].centerHandleY = centerHandleY
            return

    raise ExceptionDict[errCode](errorDict[errCode], neti, reai, centerHandleX, centerHandleY)


def createUniUni(neti: int, reaID:str, rateLaw:str, srci: int, desti: int, srcStoich:float, destStoich:float):
    startGroup()
    createReaction(neti, reaID)
    reai = getReactionIndex(neti, reaID)

    addSrcNode(neti, reai, srci, srcStoich)
    addDestNode(neti, reai, desti, destStoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def CreateUniBi(neti: int, reaID: str, rateLaw: str, srci: int, dest1i: int, dest2i: int, srcStoich: float, dest1Stoich:float, dest2Stoich:float):
    startGroup()
    createReaction(neti, reaID)
    reai = getReactionIndex(neti, reaID)

    addSrcNode(neti, reai, srci, srcStoich)
    addDestNode(neti, reai, dest1i, dest1Stoich)
    addDestNode(neti, reai, dest2i, dest2Stoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def CreateBiUni(neti: int, reaID: str, rateLaw: str, src1i: int, src2i: int, desti: int, src1Stoich: float, src2Stoich: float, destStoich: float):
    startGroup()
    createReaction(neti, reaID)
    reai = getReactionIndex(neti, reaID)

    addSrcNode(neti, reai, src1i, src1Stoich)
    addSrcNode(neti, reai, src2i, src2Stoich)
    addDestNode(neti, reai, desti, destStoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def CreateBiBi(neti:int, reaID:str, rateLaw:str, src1i:int, src2i:int, dest1i:int, dest2i:int, src1Stoich:float, src2Stoich:float, dest1Stoich:float, dest2Stoich:float):
    startGroup()
    createReaction(neti, reaID)
    reai = getReactionIndex(neti, reaID)

    addSrcNode(neti, reai, src1i, src1Stoich)
    addSrcNode(neti, reai, src2i, src2Stoich)
    addDestNode(neti, reai, dest1i, dest1Stoich)
    addDestNode(neti, reai, dest2i, dest2Stoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def reset():
    global stackFlag, errCode, networkDict, netSetStack, redoStack, lastNetIndex
    stackFlag = True
    errCode = 0
    networkDict = TNetworkDict()
    netSetStack = TStack()
    redoStack = TStack()
    lastNetIndex = 0


# newNetwork("net1")
# newNetwork("net2")
# newNetwork("net3")

# print(networkDict)
# deleteNetwork(1)
# print(networkDict)
# a = TNetworkDict([111])
# print(a)
# print(type(networkDict[1:2]))

# print(networkDict[0].__dict__,"\n")
# print(type(networkDict))
# print(networkDict[0], "\n")
# print(type(set1))
# print(set1[0].__dict__,"\n")
# clearNetworks()
# print(type(networkDict))
# print(networkDict)
# newNetwork("net1")
# print(networkDict)

# newNetwork("net2")
# newNetwork("net3")
# addNode(0, "node1", 1.1, 2.2, 3.3, 4.4)
# addNode(0, "node2", 1.1, 2.2, 3.3, 4.4)
# addNode(0, "node3", 1.1, 2.2, 3.3, 4.4)
# addNode(0, "node4", 1.1, 2.2, 3.3, 4.4)
# addNode(0, "node5", 1.1, 2.2, 3.3, 4.4)
# addNode(0, "node6", 1.1, 2.2, 3.3, 4.4)
# setNodeFillColorAlpha(0,0,0.5)
# print(getNodeFillColorAlpha(0,0))
# setNodeFillColorAlpha(0,0,0.6)
# setNodeFillColorAlpha(0,0,0.7)
# addNode(1, "node2", 1.1, 2.2, 3.3, 4.4)
# addNode(2, "node3", 1.1, 2.2, 3.3, 4.4)
# CreateBiBi(0, "Rea1", "k1*A", 0, 1, 2, 1, 1, 2, 3, 4)
# saveNetworkAsJSON(0,"")
# deleteNode(0, 1)
# print(networkDict)
# print("num", getNumberOfNetworks())
# # print(clearNetworks())
# # print(networkDict[0].id)
# print(networkDict)
# print(getNetworkIndex("net1"))
# print(getNetworkID(2))
# print(getNodeIndex(0, "node1"))
# print(getNodeIndex(0, "node2"))
# print(getNodeIndex(0, "node3"))
# print(getNodeCenter(0, 0))
# print(getNodeIndex(0, "node"))
# print(networkDict[0].getFreenodes())
# print(getNumberOfNodes(0))
# print(getNodeID(0, 0))
# print(getNodeCoordinateAndSize(0, 0))
# print(getNodeFillColor(0, 0))
# print(getNodeFillColorRGB(0, 0))
# print(getNodeFillColorAlpha(0, 0))

# print(getNodeOutlineColor(0, 0))
# print(getNodeOutlineColorRGB(0, 0))
# print(getNodeOutlineColorAlpha(0, 0))
# print(getNodeOutlineThickness(0, 0))
# print(setNodeID(0, 0, "sdf"))
# print(getNodeID(0, 0))
# clearNetwork(0)
# print(networkDict[0].getFreenodes())
# print(getNumberOfNodes(0))
