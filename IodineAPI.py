import ctypes

libIodine = ctypes.cdll.LoadLibrary('../go-NOM/Iodine_Dll/Iodine.dll')

#########################   argtypes   #########################
libIodine.cFree.argtypes = [ctypes.c_char_p]
libIodine.newNetwork.argtypes = [ctypes.c_char_p]
libIodine.getNetworkIndex.argtypes = [ctypes.c_char_p]
libIodine.saveNetworkAsJSON.argtypes = [
    ctypes.c_int,  ctypes.c_char_p]
libIodine.readNetworkFromJSON.argtypes = [
    ctypes.c_char_p]
libIodine.deleteNetwork.argtypes = [ctypes.c_int]
libIodine.getNetworkID.argtypes = [ctypes.c_int]
libIodine.addNode.argtypes = [ctypes.c_int, ctypes.c_char_p,
                              ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]
libIodine.getNodeIndex.argtypes = [ctypes.c_int, ctypes.c_char_p]
libIodine.deleteNode.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.clearNetwork.argtypes = [ctypes.c_int]
libIodine.getNumberOfNodes.argtypes = [ctypes.c_int]
libIodine.getNodeCenterX.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeCenterY.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeID.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeX.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeY.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeW.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeH.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeFillColorRGB.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeFillColorAlpha.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeOutlineColorRGB.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeOutlineColorAlpha.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getNodeOutlineThickness.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.setNodeID.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
libIodine.setNodeCoordinateAndSize.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]
libIodine.setNodeFillColorRGB.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
libIodine.setNodeFillColorAlpha.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_float]
libIodine.setNodeOutlineColorRGB.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,ctypes.c_int]
libIodine.setNodeOutlineColorAlpha.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_float]
libIodine.setNodeOutlineThickness.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int]

libIodine.createReaction.argtypes = [ctypes.c_int, ctypes.c_char_p]
libIodine.getReactionIndex.argtypes = [ctypes.c_int, ctypes.c_char_p]
libIodine.deleteReaction.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.clearReactions.argtypes = [ctypes.c_int]
libIodine.getNumberOfReactions.argtypes = [ctypes.c_int]
libIodine.getReactionID.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getReactionRateLaw.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getReactionFillColorRGB.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getReactionFillColorAlpha.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getReactionLineThickness.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getReactionSrcNodeStoich.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
libIodine.getReactionDestNodeStoich.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
libIodine.getNumberOfSrcNodes.argtypes = [
    ctypes.c_int, ctypes.c_int]
libIodine.getNumberOfDestNodes.argtypes = [
    ctypes.c_int, ctypes.c_int]
libIodine.getListOfReactionSrcNodes.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getListOfReactionDestNodes.argtypes = [ctypes.c_int, ctypes.c_int]
libIodine.getReactionNodeID.argtypes = [ctypes.c_int]
libIodine.addSrcNode.argtypes = [ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_float]
libIodine.addDestNode.argtypes = [ctypes.c_int,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_float]
libIodine.deleteSrcNode.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
libIodine.deleteDestNode.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
libIodine.setRateLaw.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
libIodine.setReactionFillColorRGB.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,ctypes.c_int]
libIodine.setReactionFillColorAlpha.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_float]
libIodine.setReactionLineThickness.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int]


#########################   restype   #########################
libIodine.getErrorCode.restype = ctypes.c_int
libIodine.undo.restype = ctypes.c_int
libIodine.redo.restype = ctypes.c_int
libIodine.newNetwork.restype = ctypes.c_int
libIodine.getNetworkIndex.restype = ctypes.c_int
libIodine.saveNetworkAsJSON.restype = ctypes.c_int
libIodine.readNetworkFromJSON.restype = ctypes.c_int
libIodine.deleteNetwork.restype = ctypes.c_int
libIodine.getNumberOfNetworks.restype = ctypes.c_int
libIodine.getNetworkID.restype = ctypes.c_char_p
libIodine.addNode.restype = ctypes.c_int
libIodine.getNodeIndex.restype = ctypes.c_int
libIodine.deleteNode.restype = ctypes.c_int
libIodine.clearNetwork.restype = ctypes.c_int
libIodine.getNumberOfNodes.restype = ctypes.c_int
libIodine.getNodeCenterX.restype = ctypes.c_float
libIodine.getNodeCenterY.restype = ctypes.c_float
libIodine.getNodeID.restype = ctypes.c_char_p
libIodine.getNodeX.restype = ctypes.c_float
libIodine.getNodeY.restype = ctypes.c_float
libIodine.getNodeW.restype = ctypes.c_float
libIodine.getNodeH.restype = ctypes.c_float
libIodine.getNodeFillColorRGB.restype = ctypes.c_uint32
libIodine.getNodeFillColorAlpha.restype = ctypes.c_float
libIodine.getNodeOutlineColorRGB.restype = ctypes.c_uint32
libIodine.getNodeOutlineColorAlpha.restype = ctypes.c_float
libIodine.getNodeOutlineThickness.restype = ctypes.c_int
libIodine.setNodeID.restype = ctypes.c_int
libIodine.setNodeCoordinateAndSize.restype = ctypes.c_int
libIodine.setNodeFillColorRGB.restype = ctypes.c_int
libIodine.setNodeFillColorAlpha.restype = ctypes.c_int
libIodine.setNodeOutlineColorRGB.restype = ctypes.c_int
libIodine.setNodeOutlineColorAlpha.restype = ctypes.c_int
libIodine.setNodeOutlineThickness.restype = ctypes.c_int

libIodine.createReaction.restype = ctypes.c_int
libIodine.getReactionIndex.restype = ctypes.c_int
libIodine.deleteReaction.restype = ctypes.c_int
libIodine.clearReactions.restype = ctypes.c_int
libIodine.getNumberOfReactions.restype = ctypes.c_int
libIodine.getReactionID.restype = ctypes.c_char_p
libIodine.getReactionRateLaw.restype = ctypes.c_char_p
libIodine.getReactionFillColorRGB.restype = ctypes.c_uint32
libIodine.getReactionFillColorAlpha.restype = ctypes.c_float
libIodine.getReactionLineThickness.restype = ctypes.c_int
libIodine.getReactionSrcNodeStoich.restype = ctypes.c_float
libIodine.getReactionDestNodeStoich.restype = ctypes.c_float
libIodine.getNumberOfSrcNodes.restype = ctypes.c_int
libIodine.getNumberOfDestNodes.restype = ctypes.c_int
libIodine.getListOfReactionSrcNodes.restype = ctypes.c_int
libIodine.getListOfReactionDestNodes.restype = ctypes.c_int
libIodine.getReactionNodeID.restype = ctypes.c_char_p
libIodine.addSrcNode.restype = ctypes.c_int
libIodine.addDestNode.restype = ctypes.c_int
libIodine.deleteSrcNode.restype = ctypes.c_int
libIodine.deleteDestNode.restype = ctypes.c_int
libIodine.setRateLaw.restype = ctypes.c_int
libIodine.setReactionFillColorRGB.restype = ctypes.c_int
libIodine.setReactionFillColorAlpha.restype = ctypes.c_int
libIodine.setReactionLineThickness.restype = ctypes.c_int


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


def getErrorCode():
    """get the error code of last function"""
    errCode = libIodine.getErrorCode()
    return errCode


def undo():
    errCode = libIodine.undo()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])


def redo():
    errCode = libIodine.redo()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode])

def startGroup():
    libIodine.startGroup()

def endGroup():
    libIodine.endGroup()

def cFree(cString):
    libIodine.cFree(cString)


def newNetwork(netId):
    errCode = libIodine.newNetwork(netId.encode())
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], netId)


def getNetworkIndex(netId):
    neti = libIodine.getNetworkIndex(netId.encode())
    if neti < 0:
        raise ExceptionDict[neti](errorDict[neti], netId)
    else:
        return neti


def saveNetworkAsJSON(neti, fileName):
    errCode = libIodine.saveNetworkAsJSON(
        neti, fileName.encode())
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, fileName)


def readNetworkFromJSON(filePath):
    errCode = libIodine.readNetworkFromJSON(filePath.encode())
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], filePath)


def deleteNetwork(neti):
    errCode = libIodine.deleteNetwork(neti)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)


def clearNetworks():
    libIodine.clearNetworks()


def getNumberOfNetworks():
    return libIodine.getNumberOfNetworks()


def getNetworkId(neti):
    netId = libIodine.getNetworkID(neti).decode("utf-8")
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode],  neti)
    else:
        return netId


def getListOfNetworks():
    a = getNumberOfNetworks()
    idList = []
    for neti in range(a):
        idList.append(getNetworkId(neti))
    return idList


def addNode(neti, nodeId, x, y, w, h):
    errCode = libIodine.addNode(neti, nodeId.encode(), x, y, w, h)
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, nodeId, x, y, w, h)


def getNodeIndex(neti, nodeId):
    nodei = libIodine.getNodeIndex(neti, nodeId.encode())
    if nodei < 0:
        raise ExceptionDict[nodei](errorDict[nodei], neti, nodeId)
    else:
        return nodei


def deleteNode(neti, nodei):
    errCode = libIodine.deleteNode(neti, nodei)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def clearNetwork(neti):
    errCode = libIodine.clearNetwork(neti)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)


def getNumberOfNodes(neti):
    num = libIodine.getNumberOfNodes(neti)
    if num < 0:
        raise ExceptionDict[num](errorDict[num], neti)
    else:
        return num


def getNodeCenter(neti, nodei):
    X = round(libIodine.getNodeCenterX(neti, nodei), 2)
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    Y = round(libIodine.getNodeCenterY(neti, nodei), 2)
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    return (X, Y)


def getNodeId(neti, nodei):
    nodeId = libIodine.getNodeID(neti, nodei).decode("utf-8")
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    else:
        return nodeId


def getListOfNodesIds(neti):
    n = getNumberOfNodes(neti)
    nodeList = []
    for nodei in range(n):
        nodeList.append(getNodeId(neti, nodei))
    return nodeList


def getNodeCoordinateAndSize(neti, nodei):
    X = round(libIodine.getNodeX(neti, nodei), 2)
    Y = round(libIodine.getNodeY(neti, nodei), 2)
    W = round(libIodine.getNodeW(neti, nodei), 2)
    H = round(libIodine.getNodeH(neti, nodei), 2)
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    return (X,Y,W,H)


def getNodeFillColorRGB(neti, nodei):
    color1 = libIodine.getNodeFillColorRGB(neti, nodei)
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    return color1


def getNodeFillColorAlpha(neti, nodei):
    alpha1 = libIodine.getNodeFillColorAlpha(neti, nodei)
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    return alpha1

def getNodeOutlineColorRGB(neti, nodei):
    color1 = libIodine.getNodeOutlineColorRGB(neti, nodei)
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    return color1


def getNodeOutlineColorAlpha(neti, nodei):
    alpha1 = libIodine.getNodeOutlineColorAlpha(neti, nodei)
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)
    return alpha1

def getNodeOutlineThickness(neti, nodei):
    thickness = libIodine.getNodeOutlineThickness(neti, nodei)
    if thickness < 0:
        raise ExceptionDict[thickness](errorDict[thickness], neti, nodei)
    return thickness


def setNodeId(neti, nodei, newId):
    errCode = libIodine.setNodeID(neti, nodei, newId.encode())
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei, newId)


def setNodeCoordinateAndSize(neti, nodei, x, y, w, h):
    errCode = libIodine.setNodeCoordinateAndSize(neti, nodei, x, y, w, h)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def setNodeFillColorRGB(neti, nodei, r, g, b):
    errCode = libIodine.setNodeFillColorRGB(neti, nodei, r, g, b)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def setNodeFillColorAlpha(neti, nodei, a):
    errCode = libIodine.setNodeFillColorAlpha(neti, nodei, a)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)

def setNodeOutlineColorRGB(neti, nodei, r, g, b):
    errCode = libIodine.setNodeOutlineColorRGB(neti, nodei, r, g, b)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def setNodeOutlineColorAlpha(neti, nodei, a):
    errCode = libIodine.setNodeOutlineColorAlpha(neti, nodei, a)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def setNodeOutlineThickness(neti, nodei, thickness):
    errCode = libIodine.setNodeOutlineThickness(neti, nodei, thickness)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, nodei)


def createReaction(neti, reaId):
    errCode = libIodine.createReaction(neti, reaId.encode())
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reaId)


def getReactionIndex(neti, reaId):
    reai = libIodine.getReactionIndex(neti, reaId.encode())
    if reai < 0:
        raise ExceptionDict[reai](errorDict[reai], neti, reaId)
    else:
        return reai


def deleteReaction(neti, reai):
    errCode = libIodine.deleteReaction(neti, reai)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)


def clearReactions(neti):
    errCode = libIodine.clearReactions(neti)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti)


def getNumberOfReactions(neti):
    reaNum = libIodine.getNumberOfReactions(neti)
    if reaNum < 0:
        raise ExceptionDict[reaNum](errorDict[reaNum], neti)
    else:
        return reaNum


def getReactionId(neti, reai):
    reaId = libIodine.getReactionID(neti, reai).decode("utf-8")
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return reaId


def getListOfReactionIds(neti):
    n = getNumberOfReactions(neti)
    reaList = []
    for i in range(n):
        reaList.append(getReactionId(neti, i))
    return reaList


def getReactionRateLaw(neti, reai):
    rateLaw = libIodine.getReactionRateLaw(neti, reai).decode("utf-8")
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return rateLaw


def getReactionFillColorRGB(neti, reai):
    color1 = libIodine.getReactionFillColorRGB(neti, reai)
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return color1


def getReactionFillColorAlpha(neti, reai):
    alpha1 = libIodine.getReactionFillColorAlpha(neti, reai)
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai)
    else:
        return alpha1

def getReactionLineThickness(neti, reai):
    thickness = libIodine.getReactionLineThickness(neti, reai)
    if thickness < 0:
        raise ExceptionDict[thickness](errorDict[thickness], neti, reai)
    else:
        return thickness


def getReactionSrcNodeStoich(neti, reai, srcNodeId):
    SrcNodeStoich = libIodine.getReactionSrcNodeStoich(
        neti, reai, srcNodeId.encode())
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, srcNodeId)
    else:
        return round(SrcNodeStoich, 2)


def getReactionDestNodeStoich(neti, reai, destNodeId):
    DestNodeStoich = libIodine.getReactionDestNodeStoich(
        neti, reai, destNodeId.encode())
    errCode = getErrorCode()
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, destNodeId)
    else:
        return round(DestNodeStoich, 2)


def getNumberOfSrcNodes(neti, reai):
    Num = libIodine.getNumberOfSrcNodes(neti, reai)
    if Num < 0:
        raise ExceptionDict[Num](
            errorDict[Num], neti, reai)
    else:
        return Num


def getNumberOfDestNodes(neti, reai):
    Num = libIodine.getNumberOfDestNodes(neti, reai)
    if Num < 0:
        raise ExceptionDict[Num](
            errorDict[Num], neti, reai)
    else:
        return Num


def getListOfReactionSrcNodes(neti, reai):
    errCode = libIodine.getListOfReactionSrcNodes(neti, reai)
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai)
    n = getNumberOfSrcNodes(neti, reai)
    nodeList = []
    for i in range(n):
        nodeList.append(libIodine.getReactionNodeID(i).decode("utf-8"))
    return nodeList


def getListOfReactionDestNodes(neti, reai):
    errCode = libIodine.getListOfReactionDestNodes(neti, reai)
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai)
    n = getNumberOfDestNodes(neti, reai)
    nodeList = []
    for i in range(n):
        nodeList.append(libIodine.getReactionNodeID(i).decode("utf-8"))
    return nodeList

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


def addSrcNode(neti, reai, nodei, stoich):
    errCode = libIodine.addSrcNode(neti, reai, nodei, stoich)
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, nodei, stoich)


def addDestNode(neti, reai, nodei, stoich):
    errCode = libIodine.addDestNode(neti, reai, nodei, stoich)
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, nodei, stoich)

def deleteSrcNode(neti, reai, srcNodeId):
    errCode = libIodine.deleteSrcNode(
        neti, reai, srcNodeId.encode())
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, srcNodeId)


def deleteDestNode(neti, reai, destNodeId):
    errCode = libIodine.deleteDestNode(
        neti, reai, destNodeId.encode())
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, destNodeId)


def setRateLaw(neti, reai, rateLaw):
    errCode = libIodine.setRateLaw(neti, reai, rateLaw.encode())
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai, rateLaw)


def setReactionFillColorRGB(neti, reai, r, g, b):
    errCode = libIodine.setReactionFillColorRGB(neti, reai, r, g, b)
    if errCode < 0:
        raise ExceptionDict[errCode](errorDict[errCode], neti, reai,  r, g, b)


def setReactionFillColorAlpha(neti, reai, a):
    errCode = libIodine.setReactionFillColorAlpha(neti, reai, a)
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, a)

def setReactionLineThickness(neti, reai, thickness):
    errCode = libIodine.setReactionLineThickness(neti, reai, thickness)
    if errCode < 0:
        raise ExceptionDict[errCode](
            errorDict[errCode], neti, reai, thickness)



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
