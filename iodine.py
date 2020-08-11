import json

class TNode:
    def __init__(self, id, x, y, w, h):
        self.id = id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.fillColor = TColor(255, 150, 80, 255)
        self.outlineColor = TColor(255, 100, 80, 255)
        self.outlineThickness = 3


class TNetwork:
    def __init__(self, id):
        self.magicIdentifier = "NM01"
        self.id = id
        self.nodes = []
        self.reactions = []

    def getFreenodes(self):
        """
        get list of nodes not in any existed reactions
        """
        reaNodeSet = {}
        for i in self.reactions:
            for j in i.species[0]:
                reaNodeSet[j] = ""
            for j in i.species[1]:
                reaNodeSet[j] = ""
        s = []
        for i in range(len(self.nodes)):
            flag = 0
            for j in reaNodeSet:
                if self.nodes[i].id == j:
                    flag = 1
            if flag == 0:
                s.append(i)
        return s


class TReaction:
    def __init__(self, id):
        self.id = id
        self.rateLaw = ""
        self.species = [{}, {}]
        self.fillColor = TColor(255, 150, 80, 255)
        self.thickness = 3


class TColor:
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


class Error(Exception):
    """Base class for other exceptions"""
    pass


class IdNotFoundError(Error):
    pass


class IdRepeatError(Error):
    pass


class NodeNotFreeError(Error):
    pass


class NetIndexOutOfRangeError(Error):
    pass


class ReactionIndexOutOfRangeError(Error):
    pass


class NodeIndexOutOfRangeError(Error):
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
    -6: "reaction index out of range: ",
    -7: "node index out of range: ",
    -8: "wrong stoich: stoich has to be positive: ",
    -9: "stack is empty",
    -10: "Json convert error",
    -11: "File error",
    -12: "Variable out of range: "
}


ExceptionDict = {
    -2: IdNotFoundError,
    -3: IdRepeatError,
    -4: NodeNotFreeError,
    -5: NetIndexOutOfRangeError,
    -6: ReactionIndexOutOfRangeError,
    -7: NodeIndexOutOfRangeError,
    -8: StoichError,
    -9: StackEmptyError,
    -10: JSONError,
    -11: FileError,
    -12: VariableOutOfRangeError
}


class Stack(object):
    def __init__(self):
        self.items = []

    def isEmpty(self):
        return self.items == []

    def push(self, set):
        theSet = deepcopy(set)
        self.items.append(theSet)

    def pop(self):
        return self.items.pop()


stackFlag = True
errCode = 0
networkSet = []
netSetStack = Stack()
redoStack = Stack()


def deepcopy(n):
    NewNetworkSet = []
    for i in n:
        NewNetworkX = TNetwork(i.id)
        NewNetworkX.magicIdentifier = i.magicIdentifier
        for j in i.nodes:
            NewNodeX = TNode(j.id, j.x, j.y, j.w, j.h)
            NewNodeX.fillColor.r = j.fillColor.r
            NewNodeX.fillColor.g = j.fillColor.g
            NewNodeX.fillColor.b = j.fillColor.b
            NewNodeX.fillColor.a = j.fillColor.a
            NewNodeX.outlineThickness = j.outlineThickness
            NewNodeX.outlineColor.r = j.outlineColor.r
            NewNodeX.outlineColor.g = j.outlineColor.g
            NewNodeX.outlineColor.b = j.outlineColor.b
            NewNodeX.outlineColor.a = j.outlineColor.a
            NewNetworkX.nodes.append(NewNodeX)
        for k in i.reactions:
            NewReactionX = TReaction(k.id)
            NewReactionX.fillColor.r = k.fillColor.r
            NewReactionX.fillColor.g = k.fillColor.g
            NewReactionX.fillColor.b = k.fillColor.b
            NewReactionX.fillColor.a = k.fillColor.a
            NewReactionX.thickness = k.thickness
            NewReactionX.rateLaw = k.rateLaw
            for l in k.species[0]:
                NewReactionX.species[0][l] = k.species[0][l]
            for m in k.species[1]:
                NewReactionX.species[1][m] = k.species[1][m]
            NewNetworkX.reactions.append(NewReactionX)
        NewNetworkSet.append(NewNetworkX)
    return NewNetworkSet


def getErrorCode():
    """get the error code of last function"""
    global errCode
    return errCode


def undo():
    """
    Undo ge back to last state
    errCode: -9: stack is empty
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if netSetStack.isEmpty():
        errCode = -9
    else:
        redoStack.push(networkSet)
        networkSet = netSetStack.pop()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])


def redo():
    """
    Redo redo
    errCode: -9: stack is empty
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    if redoStack.isEmpty():
        errCode = -9
    else:
        netSetStack.push(networkSet)
        networkSet = redoStack.pop()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])


def startGroup():
    """
    StartGroup used at the start of a group operaction or secondary function.
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    redoStack = Stack()
    netSetStack.push(networkSet)
    stackFlag = False


def endGroup():
    """
    EndGroup used at the end of a group operaction or secondary function.
    """
    global stackFlag
    stackFlag = True


def newNetwork(netId):  # TODO: stackflag #TODO addErrorMsg
    """
    newNetwork Create a new network
    errCode -3: id repeat, 0 :ok
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    for i in range(len(networkSet)):
        if networkSet[i].id == netId:
            errCode = -3
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], netId)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)

        newNetwork = TNetwork(netId)
        networkSet.append(newNetwork)


def getNetworkIndex(netId):
    """
    getNetworkIndex 
    return: -2: net id can't find
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = -2

    for i in range(len(networkSet)):
        if networkSet[i].id == netId:
            index = i
            errCode = 0

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], netId)
    else:
        return index




def saveNetworkAsJSON(neti, fileName):
    """
    SaveNetworkAsJSON SaveNetworkAsJSON
    errCode: -5: net index out of range
    -10: "Json convert error", -11: "File error"
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        data2 = json.dumps(networkSet[neti],
                           sort_keys=True, indent=4, separators=(',', ': '))
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, fileName)
    else:
        print(data2)

    
    # err2 = ioutil.WriteFile(fileName, file, 0644)
    # if err2 != nil :
    #     errCode = -11
    #     return errCode
    
    # return errCode


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
    
#     for i = range networkSet :
#         if newNet.id == networkSet[i].id :
#             errCode = -3
#             addErrorMessage(errCode, ("(\"" + filePath + "\")"), newNet.id, "")
#             return errCode
        
    

#     if stackFlag :
#         redoStack = TNetSetStack{
#         netSetStack.push(networkSet)
    
#     networkSet = append(networkSet, newNet)
#     # fmt.Println(networkSet)
#     return errCode



def deleteNetwork(neti):
    """
    DeleteNetwork DeleteNetwork
    errCode: -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        if neti == 0:
            networkSet = networkSet[1:]
        elif neti == len(networkSet)-1:
            networkSet = networkSet[:len(networkSet)-1]
        else:
            networkSet = networkSet[:neti]+networkSet[neti+1:]


def clearNetworks():
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if stackFlag:
        redoStack = Stack()
        netSetStack.push(networkSet)
    networkSet = []


def getNumberOfNetworks():
    return len(networkSet)


def getNetworkId(neti):
    """    
    GetNetworkId GetId of network
    errCode: -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        return networkSet[neti].id


def getListOfNetworks():
    a = getNumberOfNetworks()
    idList = []
    for neti in range(a):
        idList.append(getNetworkId(neti))
    return idList


def addNode(neti, nodeId, x, y, w, h):
    """
    AddNode adds a node to the network
    errCode - 3: id repeat, 0: ok
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        for i in n.nodes:
            if i.id == nodeId:
                errCode = -3
    if errCode == 0:
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, nodeId, x, y, w, h)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        newNode = TNode(nodeId, x, y, w, h)
        n.nodes.append(newNode)
        networkSet[neti] = n


def getNodeIndex(neti, nodeId):
    """
    GetNodeIndex get node index by id
    errCode: -2: node id not found,
    -5: net index out of range
    return: >=0
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = -2
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        for i in range(len(n.nodes)):
            if n.nodes[i].id == nodeId:
                index = i
                errCode = 0
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodeId)
    else:
        return index


def deleteNode(neti, nodei):
    """
    DeleteNode delete the node with index
    return: -7: node index out of range, -4: node is not free
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = -4
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
        else:
            s = n.getFreenodes()
            for i in s:
                if nodei == i:
                    errCode = 0
                    break

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        if nodei == 0:
            n.nodes = n.nodes[1:]
        elif nodei == len(n.nodes)-1:
            n.nodes = n.nodes[:len(n.nodes)-1]
        else:
            n.nodes = n.nodes[:nodei] + n.nodes[nodei+1:]
        networkSet[neti] = n


def clearNetwork(neti):
    """
    ClearNetwork clear all nodes and reactions in this network
    errCode: -5:  net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        networkSet[neti].nodes = []
        networkSet[neti].reactions = []


def getNumberOfNodes(neti):
    """
    GetNumberOfNodes get the number of nodes in the current network
    num: >= -5:  net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        n = networkSet[neti]
        return len(n.nodes)


def getNodeCenter(neti, nodei):
    """
    GetNodeCenter Get the X and  Y coordinate of the Center of node
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        X = round(n.nodes[nodei].x + n.nodes[nodei].w*0.5, 2)
        Y = round(n.nodes[nodei].y + n.nodes[nodei].h*0.5, 2)
        return (X, Y)


def getNodeId(neti, nodei):
    """
    GetNodeId Get the id of the node
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        return n.nodes[nodei].id


def getListOfNodeIds(neti):
    n = getNumberOfNodes(neti)
    nodeList = []
    for nodei in range(n):
        nodeList.append(getNodeId(neti, nodei))
    return nodeList


def getNodeCoordinateAndSize(neti, nodei):
    """
    getNodeCoordinateAndSize get the x,y,w,h of the node
    errCode:-7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        X = round(n.nodes[nodei].x, 2)
        Y = round(n.nodes[nodei].y, 2)
        W = round(n.nodes[nodei].w, 2)
        H = round(n.nodes[nodei].h, 2)
        return (X, Y, W, H)


def getNodeFillColor(neti, nodei):
    """
    getNodeFillColor  rgba tulple format, rgb range int[0,255] alpha range float[0,1]
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        return (n.nodes[nodei].fillColor.r, n.nodes[nodei].fillColor.g, n.nodes[nodei].fillColor.b, float(n.nodes[nodei].fillColor.a)/255)


def getNodeFillColorRGB(neti, nodei):
    """
    getNodeFillColorRGB getNodeFillColor rgb int format
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0

    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        color1 = n.nodes[nodei].fillColor.r
        color1 = (color1 << 8) | n.nodes[nodei].fillColor.g
        color1 = (color1 << 8) | n.nodes[nodei].fillColor.b
        return color1


def getNodeFillColorAlpha(neti, nodei):
    """
    getNodeFillColorAlpha getNodeFillColor alpha value(float)
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        return float(n.nodes[nodei].fillColor.a)/255


def getNodeOutlineColor(neti, nodei):
    """
    getNodeOutlineColor rgba tulple format, rgb range int[0,255] alpha range float[0,1]
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        return (n.nodes[nodei].outlineColor.r, n.nodes[nodei].outlineColor.g, n.nodes[nodei].outlineColor.b, float(n.nodes[nodei].outlineColor.a)/255)


def getNodeOutlineColorRGB(neti, nodei):
    """
    getNodeOutlineColorRGB getNodeOutlineColor rgb int format
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0

    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        color1 = n.nodes[nodei].outlineColor.r
        color1 = (color1 << 8) | n.nodes[nodei].outlineColor.g
        color1 = (color1 << 8) | n.nodes[nodei].outlineColor.b
        return color1


def getNodeOutlineColorAlpha(neti, nodei):
    """
    getNodeOutlineColorAlpha getNodeOutlineColor alpha value(float)
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0

    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        return float(n.nodes[nodei].outlineColor.a)/255


def getNodeOutlineThickness(neti, nodei):
    """
    getNodeOutlineThickness
    errCode: -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        return n.nodes[nodei].outlineThickness


def setNodeId(neti, nodei, newId):
    """
    setNodeId set the id of a node
    errCode -3: id repeat
    -5: net index out of range
    -7: node index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
        else:
            for i in n.nodes:
                if i.id == newId:
                    errCode = -3
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, newId)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        n.nodes[nodei].id = newId


def setNodeCoordinate(neti, nodei, x, y):
    """
    setNodeCoordinate setNodeCoordinate
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
        elif x < 0 or y < 0:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, x, y)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        n.nodes[nodei].x = x
        n.nodes[nodei].y = y


def setNodeSize(neti, nodei, w, h):
    """
    setNodeSize setNodeSize
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
        elif w <= 0 or h <= 0:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, w, h)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        n.nodes[nodei].w = w
        n.nodes[nodei].h = h


def setNodeFillColorRGB(neti, nodei, r, g, b):
    """
    setNodeFillColorRGB setNodeFillColorRGB
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
        elif r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei,  r, g, b)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        n.nodes[nodei].fillColor.r = r
        n.nodes[nodei].fillColor.g = g
        n.nodes[nodei].fillColor.b = b


def setNodeFillColorAlpha(neti, nodei, a):
    """
    setNodeFillColorAlpha setNodeFillColorAlpha
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
        elif a < 0 or a > 1:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, a)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        networkSet[neti].nodes[nodei].fillColor.a = int(a*255)


def setNodeOutlineColorRGB(neti, nodei, r, g, b):
    """
    setNodeOutlineColorRGB setNodeOutlineColorRGB
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
        elif r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei,  r, g, b)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        n.nodes[nodei].outlineColor.r = r
        n.nodes[nodei].outlineColor.g = g
        n.nodes[nodei].outlineColor.b = b


def setNodeOutlineColorAlpha(neti, nodei, a):
    """
    setNodeOutlineColorAlpha setNodeOutlineColorAlpha, alpha is a float between 0 and 1
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
        elif a < 0 or a > 1:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, a)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        A1 = int(a * 255)
        n.nodes[nodei].outlineColor.a = A1


def setNodeOutlineThickness(neti, nodei, thickness):
    """
    setNodeOutlineThickness setNodeOutlineThickness
    errCode: -7: node index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        n = networkSet[neti]
        if nodei < 0 or nodei >= len(n.nodes):
            errCode = -7
        elif thickness <= 0:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, nodei, thickness)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        n.nodes[nodei].outlineThickness = thickness


def createReaction(neti, reaId): 
    """
    createReaction create an empty reacton
    errCode: -3: id repeat
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        for i in r:
            if i.id == reaId:
                errCode = -3

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reaId)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        newReact = TReaction(reaId)
        r.append(newReact)
        networkSet[neti].reactions = r


def getReactionIndex(neti, reaId):
    """
    getReactionIndex get reaction index by id
    return: -2: id can't find, >=0: ok
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        errCode = -2
        r = networkSet[neti].reactions
        for i in range(len(r)):
            if r[i].id == reaId:
                index = i
                errCode = 0

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reaId)
    else:
        return index


def deleteReaction(neti, reai):
    """
    deleteReaction delete the reaction with index
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        if reai == 0:
            r = r[1:]
        elif reai == len(r)-1:
            r = r[:-1]
        else:
            r = r[:reai]+r[reai+1:]
        networkSet[neti].reactions = r


def clearReactions(neti):
    """
    clearReactions clear all reactions in this network
    errCode: -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions = []


def getNumberOfReactions(neti):
    """
    getNumberOfReactions get the number of reactions in the current Reactionset
    return: >=0: ok, -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)
    else:
        r = networkSet[neti].reactions
        return len(r)


def getReactionId(neti, reai):
    """
    getReactionId get the id of Reaction
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return r[reai].id


def getListOfReactionIds(neti):
    n = getNumberOfReactions(neti)
    reaList = []
    for i in range(n):
        reaList.append(getReactionId(neti, i))
    return reaList


def getReactionRateLaw(neti, reai):
    """
    getReactionRateLaw get the ratelaw of Reaction
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return r[reai].rateLaw


def getReactionFillColor(neti, reai):
    """
    getReactionFillColor rgba tulple format, rgb range int[0,255] alpha range float[0,1]
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return (r[reai].fillColor.r, r[reai].fillColor.g, r[reai].fillColor.b, float(r[reai].fillColor.a)/255)


def getReactionFillColorRGB(neti, reai):
    """
    getReactionFillColorRGB getReactionFillColorRGB
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        color1 = r[reai].fillColor.r
        color1 = (color1 << 8) | r[reai].fillColor.g
        color1 = (color1 << 8) | r[reai].fillColor.b
        return color1


def getReactionFillColorAlpha(neti, reai):
    """
    getReactionFillColorAlpha getReactionFillColorAlpha
    errCode:  -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        alpha1 = float(r[reai].fillColor.a) / 255
        return alpha1


def getReactionLineThickness(neti, reai):
    """
    getReactionLineThickness getReactionLineThickness
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return r[reai].thickness


def getReactionSrcNodeStoich(neti, reai, srcNodeId):
    """
    getReactionSrcNodeStoich get the SrcNode stoichiometry of Reaction
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        elif srcNodeId not in r[reai].species[0]:
            errCode = -2
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeId)
    else:
        return r[reai].species[0][srcNodeId]


def getReactionDestNodeStoich(neti, reai, destNodeId):
    """
    getReactionDestNodeStoich get the DestNode stoichiometry of Reaction
    return: positive float : ok, -6: reaction index out of range, -7: node index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        elif destNodeId not in r[reai].species[1]:
            errCode = -2
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, destNodeId)
    else:
        return r[reai].species[1][destNodeId]


def getNumberOfSrcNodes(neti, reai):
    """
    getNumberOfSrcNodes get the SrcNode length of Reaction
    return: non-negative int: ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return len(r[reai].species[0])


def getNumberOfDestNodes(neti, reai):
    """
    getNumberOfDestNodes get the DestNode length of Reaction
    return: non-negative int: ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return len(r[reai].species[1])


def getListOfReactionSrcNodes(neti, reai):
    """
    getListOfReactionSrcNodes getListOfReactionSrcNodes in alphabetical order
    return: non-empty slice : ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        list1 = []
        for k in r[reai].species[0]:
            list1.append(k)
        list1.sort()
        return list1


def getListOfReactionDestNodes(neti, reai):
    """
    getListOfReactionDestNodes getListOfReactionDestNodes in alphabetical order
    return: non-empty slice : ok, -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        list1 = []
        for k in r[reai].species[1]:
            list1.append(k)
        list1.sort()
        return list1


def getListOfReactionSrcStoich(neti, reai):
    n = getListOfReactionSrcNodes(neti, reai)
    srcStoichList = []
    for srcNodeId in n:
        srcStoichList.append(getReactionSrcNodeStoich(neti, reai, srcNodeId))
    return srcStoichList


def getListOfReactionDestStoich(neti, reai):
    n = getListOfReactionDestNodes(neti, reai)
    destStoichList = []
    for destNodeId in n:
        destStoichList.append(
            getReactionDestNodeStoich(neti, reai, destNodeId))
    return destStoichList


def printReactionInfo(neti, reai):
    print("id:", getReactionId(neti, reai))
    print("rateLaw:", getReactionRateLaw(neti, reai))
    print("SrcNodes:", getListOfReactionSrcNodes(neti, reai))
    print("DestNodes:", getListOfReactionDestNodes(neti, reai))
    print("SrcNodeStoichs:", getListOfReactionSrcStoich(neti, reai))
    print("DestNodeStoichs:", getListOfReactionDestStoich(neti, reai))


def addSrcNode(neti, reai, nodei, stoich):  # TODO
    """
    addSrcNode add node and Stoich to reactionlist
    errCode:  0:ok,
    -5: net index out of range
    -6: reaction index out of range,
    -7: node index out of range
    -8: "wrong stoich: stoich has to be positive"
    -3: id repeat
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        elif nodei < 0 or nodei >= len(networkSet[neti].nodes):
            errCode = -7
        elif stoich <= 0.0:
            errCode = -8
        else:
            R = r[reai]
            srcNodeId = networkSet[neti].nodes[nodei].id
            if srcNodeId in r[reai].species[0]:
                errCode = -3

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, nodei, stoich)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        R.species[0][srcNodeId] = stoich
        networkSet[neti].reactions[reai] = R


def addDestNode(neti, reai, nodei, stoich):
    """
    addDestNode add node and Stoich to reactionlist
    errCode:  0:ok,
    -5: net index out of range
    -6: reaction index out of range,
    -7: node index out of range
    -8: "wrong stoich: stoich has to be positive"
    -3: id repeat
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        elif nodei < 0 or nodei >= len(networkSet[neti].nodes):
            errCode = -7
        elif stoich <= 0:
            errCode = -8
        else:
            R = r[reai]
            destNodeId = networkSet[neti].nodes[nodei].id
            if destNodeId in R.species[1]:
                errCode = -3

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, nodei, stoich)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        R.species[1][destNodeId] = stoich
        networkSet[neti].reactions[reai] = R


def deleteSrcNode(neti, reai, srcNodeId):
    """
    deleteSrcNode delete src nodes by id(Id).
    errCode: -6: reaction index out of range,
    -5: net index out of range
    -2: id not found
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        else:
            R = r[reai]
            if srcNodeId not in R.species[0]:
                errCode = -2

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeId)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        del R.species[0][srcNodeId]
        networkSet[neti].reactions[reai] = R


def deleteDestNode(neti, reai, destNodeId):
    """
    deleteDestNode delete all dest nodes by id
    errCode: -6: reaction index out of range,
    -5: net index out of range
    -2: id not found
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        else:
            R = r[reai]
            if destNodeId not in R.species[1]:
                errCode = -2

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, destNodeId)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        del R.species[1][destNodeId]
        networkSet[neti].reactions[reai] = R


def setRateLaw(neti, reai, rateLaw):
    """
    setRateLaw edit rate law of reaction
    errCode: -6: reaction index out of range
    -5: net index out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, rateLaw)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].rateLaw = rateLaw


def setReactionFillColorRGB(neti, reai, R, G, B):
    """
    setReactionFillColorRGB setReactionFillColorRGB
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        elif R < 0 or R > 255 or G < 0 or G > 255 or B < 0 or B > 255:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, R, G, B)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        r[reai].fillColor.r = R
        r[reai].fillColor.g = G
        r[reai].fillColor.b = B


def setReactionFillColorAlpha(neti, reai, a):
    """
    setReactionFillColorAlpha setReactionFillColorAlpha
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        elif a < 0 or a > 1:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, a)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        A1 = int(a * 255)
        r[reai].fillColor.a = A1


def setReactionLineThickness(neti, reai, thickness):
    """
    setReactionLineThickness setReactionLineThickness
    errCode: -6: reaction index out of range
    -5: net index out of range
    -12: Variable out of range

    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        elif thickness <= 0:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, thickness)
    else:
        if stackFlag:
            redoStack = Stack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].thickness = thickness


def createUniUni(neti, reaId, rateLaw, srci, desti, srcStoich, destStoich):
    startGroup()
    createReaction(neti, reaId)
    reai = getReactionIndex(neti, reaId)

    addSrcNode(neti, reai, srci, srcStoich)
    addDestNode(neti, reai, desti, destStoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def CreateUniBi(neti, reaId, rateLaw, srci, dest1i, dest2i, srcStoich, dest1Stoich, dest2Stoich):
    startGroup()
    createReaction(neti, reaId)
    reai = getReactionIndex(neti, reaId)

    addSrcNode(neti, reai, srci, srcStoich)
    addDestNode(neti, reai, dest1i, dest1Stoich)
    addDestNode(neti, reai, dest2i, dest2Stoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def CreateBiUni(neti, reaId, rateLaw, src1i, src2i, desti, src1Stoich, src2Stoich, destStoich):
    startGroup()
    createReaction(neti, reaId)
    reai = getReactionIndex(neti, reaId)

    addSrcNode(neti, reai, src1i, src1Stoich)
    addSrcNode(neti, reai, src2i, src2Stoich)
    addDestNode(neti, reai, desti, destStoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


def CreateBiBi(neti, reaId, rateLaw, src1i, src2i, dest1i, dest2i, src1Stoich, src2Stoich, dest1Stoich, dest2Stoich):
    startGroup()
    createReaction(neti, reaId)
    reai = getReactionIndex(neti, reaId)

    addSrcNode(neti, reai, src1i, src1Stoich)
    addSrcNode(neti, reai, src2i, src2Stoich)
    addDestNode(neti, reai, dest1i, dest1Stoich)
    addDestNode(neti, reai, dest2i, dest2Stoich)
    setRateLaw(neti, reai, rateLaw)
    endGroup()


# newNetwork("net1")
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
# print(networkSet)
# print("num", getNumberOfNetworks())
# # print(clearNetworks())
# # print(networkSet[0].id)
# print(networkSet)
# print(getNetworkIndex("net1"))
# print(getNetworkId(2))
# print(getNodeIndex(0, "node1"))
# print(getNodeIndex(0, "node2"))
# print(getNodeIndex(0, "node3"))
# print(getNodeCenter(0, 0))
# print(getNodeIndex(0, "node"))
# print(networkSet[0].getFreenodes())
# print(getNumberOfNodes(0))
# print(getNodeId(0, 0))
# print(getNodeCoordinateAndSize(0, 0))
# print(getNodeFillColor(0, 0))
# print(getNodeFillColorRGB(0, 0))
# print(getNodeFillColorAlpha(0, 0))

# print(getNodeOutlineColor(0, 0))
# print(getNodeOutlineColorRGB(0, 0))
# print(getNodeOutlineColorAlpha(0, 0))
# print(getNodeOutlineThickness(0, 0))
# print(setNodeId(0, 0, "sdf"))
# print(getNodeId(0, 0))
# clearNetwork(0)
# print(networkSet[0].getFreenodes())
# print(getNumberOfNodes(0))