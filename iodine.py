import json

class TNode(object):
    def __init__(self, nodeID:str, x:float, y:float, w:float, h:float):
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


class TNetwork(object):
    def __init__(self, netID:str):
        self.magicIDentifier = "NM01"
        self.id = netID
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


class TReaction(object):
    def __init__(self, reaID:str):
        self.id = reaID
        self.rateLaw = ""
        self.species = [{}, {}]
        self.fillColor = TColor(255, 150, 80, 255)
        self.thickness = 3.0
        self.centerHandleX = 0.0         
        self.centerHandleY = 0.0         


class TSpeciesNode(object):
    def __init__(self, stoich: str):
        self.stoich = stoich
        self.handleX = 0.0         
        self.handleY = 0.0     

class TColor(object):
    def __init__(self, r:int, g:int, b:int, a:int):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


class TNetworkSet(list):
    def __init__(self, netList=[]):
        list.__init__([])
        self.extend(netList)

    def deepCopy(self):
        NewNetworkSet = TNetworkSet()
        for i in self:
            NewNetworkX = TNetwork(i.id)
            NewNetworkX.magicIDentifier = i.magicIDentifier
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
                NewNodeX.fontPointSize = j.fontPointSize
                NewNodeX.fontFamily = j.fontFamily
                NewNodeX.fontStyle = j.fontStyle
                NewNodeX.fontWeight = j.fontWeight
                NewNodeX.fontName = j.fontName
                NewNodeX.fontColor.r = j.fontColor.r
                NewNodeX.fontColor.g = j.fontColor.g
                NewNodeX.fontColor.b = j.fontColor.b
                NewNodeX.fontColor.a = j.fontColor.a
                NewNetworkX.nodes.append(NewNodeX)
            for k in i.reactions:
                NewReactionX = TReaction(k.id)
                NewReactionX.fillColor.r = k.fillColor.r
                NewReactionX.fillColor.g = k.fillColor.g
                NewReactionX.fillColor.b = k.fillColor.b
                NewReactionX.fillColor.a = k.fillColor.a
                NewReactionX.thickness = k.thickness
                NewReactionX.rateLaw = k.rateLaw
                NewReactionX.centerHandleX = k.centerHandleX
                NewReactionX.centerHandleY = k.centerHandleY
                for l in k.species[0]:
                    NewSpeciesNodeX = TSpeciesNode(k.species[0][l].stoich)
                    NewSpeciesNodeX.handleX = k.species[0][l].handleX
                    NewSpeciesNodeX.handleY = k.species[0][l].handleY
                    NewReactionX.species[0][l] = NewSpeciesNodeX
                for m in k.species[1]:
                    NewSpeciesNodeX = TSpeciesNode(k.species[1][m].stoich)
                    NewSpeciesNodeX.handleX = k.species[1][m].handleX
                    NewSpeciesNodeX.handleY = k.species[1][m].handleY
                    NewReactionX.species[1][m] = NewSpeciesNodeX
                NewNetworkX.reactions.append(NewReactionX)
            NewNetworkSet.append(NewNetworkX)
        return NewNetworkSet


class TStack(object):
    def __init__(self):
        self.items = []

    def isEmpty(self):
        return self.items == []

    def push(self, netSet):
        theSet = netSet.deepCopy()
        self.items.append(theSet)
    def pop(self):
        return self.items.pop()


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
    -2: IDNotFoundError,
    -3: IDRepeatError,
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


fontFamilyDict ={
	"default": 0,
	"decorative": 1,
	"roman": 2,
	"script": 3,
	"swiss": 4,
	"modern": 5,
}

fontStyleDict ={
	"normal": 0,
	"italic": 1,
}

fontWeightDict ={
	"default": 0,
	"light": 1,
	"bold": 2,
}


stackFlag = True
errCode = 0
networkSet = TNetworkSet()
netSetStack = TStack()
redoStack = TStack()



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
    redoStack = TStack()
    netSetStack.push(networkSet)
    stackFlag = False


def endGroup():
    """
    EndGroup used at the end of a group operaction or secondary function.
    """
    global stackFlag
    stackFlag = True


def newNetwork(netID:str):  
    """
    newNetwork Create a new network
    errCode -3: id repeat, 0 :ok
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    for i in range(len(networkSet)):
        if networkSet[i].id == netID:
            errCode = -3
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], netID)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)

        newNetwork = TNetwork(netID)
        networkSet.append(newNetwork)


def getNetworkIndex(netID: str):
    """
    getNetworkIndex 
    return: -2: net id can't find
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = -2

    for i in range(len(networkSet)):
        if networkSet[i].id == netID:
            index = i
            errCode = 0

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], netID)
    else:
        return index


def saveNetworkAsJSON(neti:int, fileName: str):
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



def deleteNetwork(neti:int):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        if neti == 0:
            networkSet = TNetworkSet(networkSet[1:])
        elif neti == len(networkSet)-1:
            networkSet = TNetworkSet(networkSet[:len(networkSet)-1])
        else:
            networkSet = TNetworkSet(networkSet[:neti]+networkSet[neti+1:])


def clearNetworks():
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if stackFlag:
        redoStack = TStack()
        netSetStack.push(networkSet)
    networkSet = TNetworkSet()


def getNumberOfNetworks():
    return len(networkSet)


def getNetworkID(neti:int):
    """    
    GetNetworkID GetID of network
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
        idList.append(getNetworkID(neti))
    return idList


def addNode(neti: int, nodeID: str, x: float, y: float, w: float, h: float):
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
            if i.id == nodeID:
                errCode = -3
    if errCode == 0:
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, nodeID, x, y, w, h)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        newNode = TNode(nodeID, x, y, w, h)
        n.nodes.append(newNode)
        networkSet[neti] = n


def getNodeIndex(neti:int, nodeID:str):
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
            if n.nodes[i].id == nodeID:
                index = i
                errCode = 0
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodeID)
    else:
        return index


def deleteNode(neti:int, nodei:int):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        if nodei == 0:
            n.nodes = n.nodes[1:]
        elif nodei == len(n.nodes)-1:
            n.nodes = n.nodes[:len(n.nodes)-1]
        else:
            n.nodes = n.nodes[:nodei] + n.nodes[nodei+1:]
        networkSet[neti] = n


def clearNetwork(neti:int):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].nodes = []
        networkSet[neti].reactions = []


def getNumberOfNodes(neti:int):
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


def getNodeCenter(neti:int, nodei:int):
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


def getNodeID(neti:int, nodei:int):
    """
    GetNodeID Get the id of the node
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


def getListOfNodeIDs(neti:int):
    n = getNumberOfNodes(neti)
    nodeList = []
    for nodei in range(n):
        nodeList.append(getNodeID(neti, nodei))
    return nodeList


def getNodeCoordinateAndSize(neti:int, nodei:int):
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


def getNodeFillColor(neti:int, nodei:int):
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


def getNodeFillColorRGB(neti:int, nodei:int):
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


def getNodeFillColorAlpha(neti:int, nodei:int):
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


def getNodeOutlineColor(neti:int, nodei:int):
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


def getNodeOutlineColorRGB(neti:int, nodei:int):
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


def getNodeOutlineColorAlpha(neti:int, nodei:int):
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


def getNodeOutlineThickness(neti:int, nodei:int):
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


def getNodeFontPointSize(neti: int, nodei: int):
    """
    getNodeFontPointSize
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
        return n.nodes[nodei].fontPointSize


def getNodeFontFamily(neti: int, nodei: int):
    """
    getNodeFontFamily
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
        return n.nodes[nodei].fontFamily

def getNodeFontStyle(neti: int, nodei: int):
    """
    getNodeFontStyle
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
        return n.nodes[nodei].fontStyle

def getNodeFontWeight(neti: int, nodei: int):
    """
    getNodeFontWeight
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
        return n.nodes[nodei].fontWeight


def getNodeFontName(neti: int, nodei: int):
    """
    getNodeFontName
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
        return n.nodes[nodei].fontName


def getNodeFontColor(neti: int, nodei: int):
    """
    getNodeFontColor rgba tulple format, rgb range int[0,255] alpha range float[0,1]
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
        return (n.nodes[nodei].fontColor.r, n.nodes[nodei].fontColor.g, n.nodes[nodei].fontColor.b, float(n.nodes[nodei].fontColor.a)/255)


def getNodeFontColorRGB(neti: int, nodei: int):
    """
    getNodeFontColorRGB getNodeFontColor rgb int format
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
        color1 = n.nodes[nodei].fontColor.r
        color1 = (color1 << 8) | n.nodes[nodei].fontColor.g
        color1 = (color1 << 8) | n.nodes[nodei].fontColor.b
        return color1


def getNodeFontColorAlpha(neti: int, nodei: int):
    """
    getNodeFontColorAlpha getNodeFontColor alpha value(float)
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
        return float(n.nodes[nodei].fontColor.a)/255


def setNodeID(neti:int, nodei:int, newID:str):
    """
    setNodeID set the id of a node
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
                if i.id == newID:
                    errCode = -3
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, newID)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].id = newID


def setNodeCoordinate(neti: int, nodei: int, x:float, y:float):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].x = x
        n.nodes[nodei].y = y


def setNodeSize(neti: int, nodei: int, w: float, h: float):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].w = w
        n.nodes[nodei].h = h


def setNodeFillColorRGB(neti: int, nodei: int, r: int, g: int, b: int):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].fillColor.r = r
        n.nodes[nodei].fillColor.g = g
        n.nodes[nodei].fillColor.b = b


def setNodeFillColorAlpha(neti:int, nodei:int, a:float):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].nodes[nodei].fillColor.a = int(a*255)


def setNodeOutlineColorRGB(neti: int, nodei: int, r: int, g: int, b: int):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].outlineColor.r = r
        n.nodes[nodei].outlineColor.g = g
        n.nodes[nodei].outlineColor.b = b


def setNodeOutlineColorAlpha(neti:int, nodei:int, a:float):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        A1 = int(a * 255)
        n.nodes[nodei].outlineColor.a = A1


def setNodeOutlineThickness(neti:int, nodei:int, thickness:float):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].outlineThickness = thickness


def setNodeFontPointSize(neti: int, nodei: int, fontPointSize: int):
    """
    setNodeFontPointSize setNodeFontPointSize
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
        elif fontPointSize <= 0:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, nodei, fontPointSize)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].fontPointSize = fontPointSize


def setNodeFontFamily(neti: int, nodei: int, fontFamily: str):
    """
    setNodeFontFamily set the fontFamily of a node
    errCode 
    -5: net index out of range
    -7: node index out of range
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
        elif fontFamily not in fontFamilyDict:
            errCode = -12
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, nodei, fontFamily)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].fontFamily = fontFamily


def setNodeFontStyle(neti: int, nodei: int, fontStyle: str):
    """
    setNodeFontStyle set the fontStyle of a node
    errCode 
    -5: net index out of range
    -7: node index out of range
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
        elif fontStyle not in fontStyleDict:
            errCode = -12
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, nodei, fontStyle)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].fontStyle = fontStyle

def setNodeFontWeight(neti: int, nodei: int, fontWeight: str):
    """
    setNodeFontWeight set the fontWeight of a node
    errCode 
    -5: net index out of range
    -7: node index out of range
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
        elif fontWeight not in fontWeightDict:
            errCode = -12
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, nodei, fontWeight)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].fontWeight = fontWeight


def setNodeFontName(neti: int, nodei: int, fontName: str):
    """
    setNodeFontName set the fontName of a node
    errCode 
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

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, nodei, fontName)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].fontName = fontName


def setNodeFontColorRGB(neti: int, nodei: int, r: int, g: int, b: int):
    """
    setNodeFontColorRGB setNodeFontColorRGB
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        n.nodes[nodei].fontColor.r = r
        n.nodes[nodei].fontColor.g = g
        n.nodes[nodei].fontColor.b = b


def setNodeFontColorAlpha(neti: int, nodei: int, a: float):
    """
    setNodeFontColorAlpha setNodeFontColorAlpha
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].nodes[nodei].fontColor.a = int(a*255)

def createReaction(neti:int, reaID:str): 
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
            if i.id == reaID:
                errCode = -3

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reaID)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        newReact = TReaction(reaID)
        r.append(newReact)
        networkSet[neti].reactions = r


def getReactionIndex(neti:int, reaID:str):
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
            if r[i].id == reaID:
                index = i
                errCode = 0

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reaID)
    else:
        return index


def deleteReaction(neti:int, reai:int):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        if reai == 0:
            r = r[1:]
        elif reai == len(r)-1:
            r = r[:-1]
        else:
            r = r[:reai]+r[reai+1:]
        networkSet[neti].reactions = r


def clearReactions(neti:int):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions = []


def getNumberOfReactions(neti:int):
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


def getReactionID(neti:int, reai:int):
    """
    getReactionID get the id of Reaction
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


def getListOfReactionIDs(neti:int):
    n = getNumberOfReactions(neti)
    reaList = []
    for i in range(n):
        reaList.append(getReactionID(neti, i))
    return reaList


def getReactionRateLaw(neti:int, reai:int):
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


def getReactionFillColor(neti:int, reai:int):
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


def getReactionFillColorRGB(neti:int, reai:int):
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


def getReactionFillColorAlpha(neti:int, reai:int):
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


def getReactionLineThickness(neti:int, reai:int):
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


def getReactionCenterHandlePosition(neti: int, reai: int):
    """
    getReactionCenterHandlePosition getReactionCenterHandlePosition
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
        return (round(r[reai].centerHandleX, 2), round(r[reai].centerHandleY, 2))



def getReactionSrcNodeStoich(neti:int, reai:int, srcNodeID:str):
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
        elif srcNodeID not in r[reai].species[0]:
            errCode = -2
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeID)
    else:
        return r[reai].species[0][srcNodeID].stoich


def getReactionDestNodeStoich(neti:int, reai:int, destNodeID:str):
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
        elif destNodeID not in r[reai].species[1]:
            errCode = -2
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, destNodeID)
    else:
        s = r[reai].species[1][destNodeID]
        return s.stoich


def getReactionSrcNodeHandlePosition(neti: int, reai: int, srcNodeID: str):
    """
    getReactionSrcNodeHandlePosition get the SrcNode HandlePosition of Reaction
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
        elif srcNodeID not in r[reai].species[0]:
            errCode = -2
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeID)
    else:
        return (round(r[reai].species[0][srcNodeID].handleX,2),round(r[reai].species[0][srcNodeID].handleY,2))


def getReactionDestNodeHandlePosition(neti: int, reai: int, destNodeID: str):
    """
    getReactionDestNodeStoich get the DestNode HandlePosition of Reaction
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
        elif destNodeID not in r[reai].species[1]:
            errCode = -2
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, destNodeID)
    else:
        return (round(r[reai].species[1][destNodeID].handleX, 2), round(r[reai].species[1][destNodeID].handleY, 2))


def getNumberOfSrcNodes(neti:int, reai:int):
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


def getNumberOfDestNodes(neti:int, reai:int):
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


def getListOfReactionSrcNodes(neti:int, reai:int):
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


def getListOfReactionDestNodes(neti:int, reai:int):
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


def getListOfReactionSrcStoich(neti:int, reai:int):
    n = getListOfReactionSrcNodes(neti, reai)
    srcStoichList = []
    for srcNodeID in n:
        srcStoichList.append(getReactionSrcNodeStoich(neti, reai, srcNodeID))
    return srcStoichList


def getListOfReactionDestStoich(neti:int, reai:int):
    n = getListOfReactionDestNodes(neti, reai)
    destStoichList = []
    for destNodeID in n:
        destStoichList.append(
            getReactionDestNodeStoich(neti, reai, destNodeID))
    return destStoichList


def printReactionInfo(neti:int, reai:int):
    print("id:", getReactionID(neti, reai))
    print("rateLaw:", getReactionRateLaw(neti, reai))
    print("SrcNodes:", getListOfReactionSrcNodes(neti, reai))
    print("DestNodes:", getListOfReactionDestNodes(neti, reai))
    print("SrcNodeStoichs:", getListOfReactionSrcStoich(neti, reai))
    print("DestNodeStoichs:", getListOfReactionDestStoich(neti, reai))


def addSrcNode(neti:int, reai:int, nodei:int, stoich:float):  
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
            srcNodeID = networkSet[neti].nodes[nodei].id
            if srcNodeID in r[reai].species[0]:
                errCode = -3

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, nodei, stoich)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        R.species[0][srcNodeID] = TSpeciesNode(stoich)
        networkSet[neti].reactions[reai] = R


def addDestNode(neti:int, reai:int, nodei:int, stoich:float):
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
            destNodeID = networkSet[neti].nodes[nodei].id
            if destNodeID in R.species[1]:
                errCode = -3

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, nodei, stoich)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        R.species[1][destNodeID] = TSpeciesNode(stoich)
        networkSet[neti].reactions[reai] = R


def deleteSrcNode(neti:int, reai:int, srcNodeID:str):
    """
    deleteSrcNode delete src nodes by id(ID).
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
            if srcNodeID not in R.species[0]:
                errCode = -2

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeID)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        del R.species[0][srcNodeID]
        networkSet[neti].reactions[reai] = R


def deleteDestNode(neti:int, reai:int, destNodeID:str):
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
            if destNodeID not in R.species[1]:
                errCode = -2

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, destNodeID)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        del R.species[1][destNodeID]
        networkSet[neti].reactions[reai] = R


def setReactionID(neti:int, reai:int, newID:str):
    """
    setReactionID edit id of reaction
    errCode: 0:ok, -6: reaction index out of range
    -5: net index out of range
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
        else:
            for i in r:
                if i.id == newID:
                    errCode = -3
                    break

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, newID)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].id = newID


def setRateLaw(neti:int, reai:int, rateLaw:str):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].rateLaw = rateLaw


def setReactionSrcNodeStoich(neti: int, reai: int, srcNodeID: str, newStoich: float):
    """
    setReactionSrcNodeStoich edit Stoich by Reaction srcNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    -8: wrong stoich
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        elif srcNodeID not in r[reai].species[0]:
            errCode = -2
        elif newStoich <= 0.0:
            errCode = -8

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeID, newStoich)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].species[0][srcNodeID].stoich = newStoich


def setReactionDestNodeStoich(neti: int, reai: int, destNodeID: str, newStoich: float):
    """
    setReactionDestNodeStoich edit Stoich by Reaction destNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
    -8: wrong stoich
    """
    global stackFlag, errCode, networkSet, netSetStack, redoStack
    errCode = 0
    if neti < 0 or neti >= len(networkSet):
        errCode = -5
    else:
        r = networkSet[neti].reactions
        if reai < 0 or reai >= len(r):
            errCode = -6
        elif destNodeID not in r[reai].species[1]:
            errCode = -2
        elif newStoich <= 0.0:
            errCode = -8

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, destNodeID, newStoich)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].species[1][destNodeID].stoich = newStoich


def setReactionSrcNodeHandlePosition(neti: int, reai: int, srcNodeID: str, handleX: float, handleY: float):
    """
    setReactionSrcNodeHandlePosition edit HandlePosition by Reaction srcNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
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
        elif srcNodeID not in r[reai].species[0]:
            errCode = -2
        elif handleX < 0 or handleY < 0 :
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeID, handleX, handleY)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].species[0][srcNodeID].handleX = handleX
        networkSet[neti].reactions[reai].species[0][srcNodeID].handleY = handleY


def setReactionDestNodeHandlePosition(neti: int, reai: int, destNodeID: str, handleX: float, handleY: float):
    """
    setReactionDestNodeHandlePosition edit HandlePosition by Reaction destNodeID
    errCode: -6: reaction index out of range,
    -5: net index out of range, -2: id not found
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
        elif destNodeID not in r[reai].species[1]:
            errCode = -2
        elif handleX < 0 or handleY < 0:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, destNodeID,  handleX, handleY)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].species[1][destNodeID].handleX = handleX
        networkSet[neti].reactions[reai].species[1][destNodeID].handleY = handleY



def setReactionFillColorRGB(neti: int, reai: int, R: int, G: int, B: int):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        r[reai].fillColor.r = R
        r[reai].fillColor.g = G
        r[reai].fillColor.b = B


def setReactionFillColorAlpha(neti:int, reai:int, a:float):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        A1 = int(a * 255)
        r[reai].fillColor.a = A1


def setReactionLineThickness(neti:int, reai:int, thickness:float):
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
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].thickness = thickness


def setReactionCenterHandlePosition(neti: int, reai: int,  centerHandleX: float,centerHandleY: float):
    """
    setReactionCenterHandlePosition setReactionCenterHandlePosition
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
        elif centerHandleX < 0 or centerHandleY <0:
            errCode = -12

    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, centerHandleX, centerHandleY)
    else:
        if stackFlag:
            redoStack = TStack()
            netSetStack.push(networkSet)
        networkSet[neti].reactions[reai].centerHandleX = centerHandleX
        networkSet[neti].reactions[reai].centerHandleY = centerHandleY


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


# newNetwork("net1")
# newNetwork("net2")
# newNetwork("net3")

# print(networkSet)
# deleteNetwork(1)
# print(networkSet)
# a = TNetworkSet([111])
# print(a)
# print(type(networkSet[1:2]))

# print(networkSet[0].__dict__,"\n")
# print(type(networkSet))
# print(networkSet[0], "\n")
# print(type(set1))
# print(set1[0].__dict__,"\n")
# clearNetworks()
# print(type(networkSet))
# print(networkSet)
# newNetwork("net1")
# print(networkSet)

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
# print(getNetworkID(2))
# print(getNodeIndex(0, "node1"))
# print(getNodeIndex(0, "node2"))
# print(getNodeIndex(0, "node3"))
# print(getNodeCenter(0, 0))
# print(getNodeIndex(0, "node"))
# print(networkSet[0].getFreenodes())
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
# print(networkSet[0].getFreenodes())
# print(getNumberOfNodes(0))