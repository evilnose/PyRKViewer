import rkviewer.iodine as IodineAPI
import unittest

from rkviewer.iodine import CompartmentIndexError, IDRepeatError, NetIndexNotFoundError


class TestNetworkFunc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        IodineAPI.newNetwork("network1")
        IodineAPI.newNetwork("network2")

    def tearDown(self):
        IodineAPI.clearNetworks()

    def test_newNetwork(self):
        with self.assertRaises(IodineAPI.IDRepeatError):
            IodineAPI.newNetwork("network1")
        self.assertEqual(IodineAPI.newNetwork("network3"),  None)
        self.assertEqual(IodineAPI.newNetwork("network4"),  None)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.getListOfNetworks(), [0, 1, 2, 3])
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfNetworks(), [0, 1, 2])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfNetworks(), [0, 1, 2, 3])

    def test_getNetworkIndex(self):
        with self.assertRaises(IodineAPI.IDNotFoundError):
            IodineAPI.getNetworkIndex("network3")
        self.assertEqual(IodineAPI.getNetworkIndex("network2"),  1)
        self.assertEqual(IodineAPI.getNetworkIndex("network1"),  0)

    def test_deleteNetwork(self):
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.deleteNetwork(2)
        self.assertEqual(IodineAPI.deleteNetwork(1),  None)
        self.assertEqual(IodineAPI.getListOfNetworks(), [0])
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfNetworks(),
                         [0, 1])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfNetworks(),
                         [0])

    def test_clearNetworks(self):
        self.assertEqual(IodineAPI.clearNetworks(),  None)
        self.assertEqual(IodineAPI.getListOfNetworks(), [])
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfNetworks(), [0, 1])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfNetworks(), [])

    def test_getNumberOfNetworks(self):
        self.assertEqual(IodineAPI.getNumberOfNetworks(),  2)

    def test_getNetworkID(self):
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNetworkID(2)
        self.assertEqual(IodineAPI.getNetworkID(0),  'network1')

    def test_getListOfNetworks(self):
        self.assertEqual(IodineAPI.getListOfNetworks(), [0, 1])


class TestNodeFunc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        IodineAPI.newNetwork("network1")
        IodineAPI.addNode(0, "node1", 1.1, 2.5, 5.4, 6.4)
        IodineAPI.addNode(0, "node2", 1.2, 3.2, 2.5, 4.1)
        IodineAPI.addNode(0, "node3", 2.2, 3.1, 1.5, 4.5)
        IodineAPI.newNetwork("network2")
        IodineAPI.addNode(1, "node1", 1.1, 3.5, 7.4, 6.0)

    def tearDown(self):
        IodineAPI.clearNetworks()

    def test_addNode(self):
        self.assertEqual(IodineAPI.addNode(
            0, "node4", 1.1, 2.5, 5.4, 6.4), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(
            0), ["node1", "node2", "node3", "node4"])
        with self.assertRaises(IodineAPI.IDRepeatError):
            IodineAPI.addNode(0, "node2", 1.2, 3.2, 2.5, 4.1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.addNode(-1, "node5", 1.2, 3.2, 2.5, 4.1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.addNode(2, "node5", 1.2, 3.2, 2.5, 4.1)

        with self.assertRaises(ValueError):
            IodineAPI.addNode(0, "node5", -1, 2.5, 5.4, 6.4)
        with self.assertRaises(ValueError):
            IodineAPI.addNode(0, "node5", 1.1, -1, 5.4, 6.4)
        with self.assertRaises(ValueError):
            IodineAPI.addNode(0, "node5", 1.1, 2.5, -1, 6.4)
        with self.assertRaises(ValueError):
            IodineAPI.addNode(0, "node5", 1.1, 2.5,  0, 6.4)
        with self.assertRaises(ValueError):
            IodineAPI.addNode(0, "node5", 1.1, 2.5, 5.4, -1)
        with self.assertRaises(ValueError):
            IodineAPI.addNode(0, "node5", 1.1, 2.5, 5.4,  0)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(0),
                         ["node1", "node2", "node3"])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(0), [
                         "node1", "node2", "node3", "node4"])

    def test_getNodeIndex(self):
        self.assertEqual(IodineAPI.getNodeIndex(0, "node1"), 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeIndex(-1, "node2")
        with self.assertRaises(IodineAPI.IDNotFoundError):
            IodineAPI.getNodeIndex(0, "node5")

    def test_deleteNode(self):
        self.assertEqual(IodineAPI.deleteNode(0, 1), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(
            0), ["node1", "node3"])
        self.assertEqual(IodineAPI.deleteNode(1, 0), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(1), [])
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(1),
                         ["node1"])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(1), [])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.deleteNode(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.deleteNode(2, 0)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.deleteNode(0, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.deleteNode(0, 3)
        IodineAPI.createReaction(0, "rea1")
        IodineAPI.addSrcNode(0, 0, 0, 1)
        with self.assertRaises(IodineAPI.NodeNotFreeError):
            IodineAPI.deleteNode(0, 0)
        IodineAPI.addDestNode(0, 0, 2, 6)
        with self.assertRaises(IodineAPI.NodeNotFreeError):
            IodineAPI.deleteNode(0, 2)

    def test_clearNetwork(self):
        IodineAPI.CreateBiBi(0, "Rea1", "k1*A",
                             0, 1, 2, 1, 1, 2, 3, 4)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), ["Rea1"])
        self.assertEqual(IodineAPI.clearNetwork(0), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(0), [])
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), [])
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(0),
                         ["node1", "node2", "node3"])
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), ["Rea1"])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(0), [])
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), [])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.clearNetwork(-1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.clearNetwork(2)

    def test_getNumberOfNodes(self):
        self.assertEqual(IodineAPI.getNumberOfNodes(0), 3)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNumberOfNodes(-1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNumberOfNodes(2)

    def test_getNodeCenter(self):
        self.assertEqual(IodineAPI.getNodeCenter(0, 0), (3.80, 5.70))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeCenter(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeCenter(2, 0)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeCenter(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeCenter(0, 3)

    def test_getNodeID(self):
        self.assertEqual(IodineAPI.getNodeID(0, 0), "node1")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeID(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeID(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeID(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeID(1, 4)

    def test_getListOfNodeIDs(self):
        self.assertEqual(IodineAPI.getListOfNodeIDs(
            0), ["node1", "node2", "node3"])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfNodeIDs(-1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfNodeIDs(2)
        self.assertEqual(IodineAPI.clearNetwork(0), None)
        self.assertEqual(IodineAPI.getListOfNodeIDs(0), [])

    def test_getNodeCoordinateAndSize(self):
        self.assertEqual(IodineAPI.getNodeCoordinateAndSize(
            0, 0), (1.1, 2.5, 5.4, 6.4))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeCoordinateAndSize(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeCoordinateAndSize(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeCoordinateAndSize(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeCoordinateAndSize(1, 4)

    def test_getNodeFillColor(self):
        self.assertEqual(IodineAPI.getNodeFillColor(0, 0), (255, 150, 80, 1.0))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFillColor(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFillColor(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFillColor(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFillColor(1, 4)

    def test_getNodeFillColorRGB(self):
        self.assertEqual(hex(IodineAPI.getNodeFillColorRGB(0, 0)), '0xff9650')
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFillColorRGB(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFillColorRGB(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFillColorRGB(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFillColorRGB(1, 4)

    def test_getNodeFillColorAlpha(self):
        self.assertAlmostEqual(IodineAPI.getNodeFillColorAlpha(0, 0), 1, 2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFillColorAlpha(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFillColorAlpha(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFillColorAlpha(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFillColorAlpha(1, 4)

    def test_getNodeOutlineColor(self):
        self.assertEqual(
            IodineAPI.getNodeOutlineColor(0, 0), (255, 100, 80, 1.0))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeOutlineColor(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeOutlineColor(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeOutlineColor(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeOutlineColor(1, 4)

    def test_getNodeOutlineColorRGB(self):
        self.assertEqual(
            hex(IodineAPI.getNodeOutlineColorRGB(0, 0)), '0xff6450')
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeOutlineColorRGB(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeOutlineColorRGB(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeOutlineColorRGB(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeOutlineColorRGB(1, 4)

    def test_getNodeOutlineColorAlpha(self):
        self.assertAlmostEqual(IodineAPI.getNodeOutlineColorAlpha(0, 0), 1, 2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeOutlineColorAlpha(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeOutlineColorAlpha(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeOutlineColorAlpha(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeOutlineColorAlpha(1, 4)

    def test_getNodeOutlineThickness(self):
        self.assertEqual(IodineAPI.getNodeOutlineThickness(0, 1), 3.0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeOutlineThickness(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeOutlineThickness(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeOutlineThickness(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeOutlineThickness(1, 4)

    def test_getNodeFontPointSize(self):
        self.assertEqual(IodineAPI.getNodeFontPointSize(0, 1), 20)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontPointSize(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontPointSize(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontPointSize(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontPointSize(1, 4)

    def test_getNodeFontFamily(self):
        self.assertEqual(IodineAPI.getNodeFontFamily(0, 0), "default")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontFamily(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontFamily(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontFamily(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontFamily(1, 4)

    def test_getNodeFontStyle(self):
        self.assertEqual(IodineAPI.getNodeFontStyle(0, 0), "normal")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontStyle(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontStyle(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontStyle(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontStyle(1, 4)

    def test_getNodeFontWeight(self):
        self.assertEqual(IodineAPI.getNodeFontWeight(0, 0), "default")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontWeight(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontWeight(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontWeight(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontWeight(1, 4)

    def test_getNodeFontName(self):
        self.assertEqual(IodineAPI.getNodeFontName(0, 0), "")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontName(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontName(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontName(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontName(1, 4)

    def test_getNodeFontColorRGB(self):
        self.assertEqual(
            hex(IodineAPI.getNodeFontColorRGB(0, 0)), '0x0')
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontColorRGB(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontColorRGB(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontColorRGB(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontColorRGB(1, 4)

    def test_getNodeFontColorAlpha(self):
        self.assertAlmostEqual(IodineAPI.getNodeFontColorAlpha(0, 0), 1, 2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontColorAlpha(-1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNodeFontColorAlpha(3, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontColorAlpha(1, -1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.getNodeFontColorAlpha(1, 4)

    def test_setNodeID(self):
        self.assertEqual(IodineAPI.getNodeID(0, 1), "node2")
        self.assertEqual(IodineAPI.setNodeID(0, 1, "Node2"), None)
        self.assertEqual(IodineAPI.getNodeID(0, 1), "Node2")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeID(-1, 1, "Node2")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeID(3, 1, "Node2")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeID(1, -1, "Node2")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeID(1, 1, "Node2")
        with self.assertRaises(IodineAPI.IDRepeatError):
            IodineAPI.setNodeID(0, 1, "node1")
        with self.assertRaises(IodineAPI.IDRepeatError):
            IodineAPI.setNodeID(0, 1, "node3")

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getNodeID(0, 1), "node2")
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getNodeID(0, 1), "Node2")

    def test_setNodeCoordinate(self):
        self.assertEqual(IodineAPI.getNodeCoordinateAndSize(
            0, 1), (1.2, 3.2, 2.5, 4.1))
        self.assertEqual(IodineAPI.setNodeCoordinate(
            0, 1, 1.1, 2.5), None)
        self.assertEqual(IodineAPI.getNodeCoordinateAndSize(
            0, 1), (1.1, 2.5, 2.5, 4.1))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeCoordinate(-1, 1, 1.2, 3.2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeCoordinate(3, 1, 1.2, 3.2)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeCoordinate(1, -1, 1.2, 3.2)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeCoordinate(1, 4, 1.2, 3.2)

        with self.assertRaises(ValueError):
            IodineAPI.setNodeCoordinate(0, 1, -1, 2.5)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeCoordinate(0, 1, 1.1, -1)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getNodeCoordinateAndSize(
            0, 1), (1.2, 3.2, 2.5, 4.1))
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getNodeCoordinateAndSize(
            0, 1), (1.1, 2.5, 2.5, 4.1))

    def test_setNodeSize(self):
        self.assertEqual(IodineAPI.getNodeCoordinateAndSize(
            0, 1), (1.2, 3.2, 2.5, 4.1))
        self.assertEqual(IodineAPI.setNodeSize(
            0, 1, 5.4, 6.4), None)
        self.assertEqual(IodineAPI.getNodeCoordinateAndSize(
            0, 1), (1.2, 3.2, 5.4, 6.4))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeSize(-1, 1, 2.5, 4.1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeSize(3, 1, 2.5, 4.1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeSize(1, -1, 2.5, 4.1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeSize(1, 4, 2.5, 4.1)

        with self.assertRaises(ValueError):
            IodineAPI.setNodeSize(0, 1, -1, 6.4)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeSize(0, 1, 0, 6.4)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeSize(0, 1, 5.4, -1)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeSize(0, 1, 5.4, 0)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getNodeCoordinateAndSize(
            0, 1), (1.2, 3.2, 2.5, 4.1))
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getNodeCoordinateAndSize(
            0, 1), (1.2, 3.2, 5.4, 6.4))

    def test_setNodeFillColorRGB(self):
        self.assertEqual(hex(IodineAPI.getNodeFillColorRGB(0, 1)), '0xff9650')
        self.assertEqual(IodineAPI.setNodeFillColorRGB(
            0, 1, 30, 180, 160), None)
        self.assertEqual(hex(IodineAPI.getNodeFillColorRGB(0, 1)), '0x1eb4a0')
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFillColorRGB(-1, 1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFillColorRGB(3, 1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFillColorRGB(1, -1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFillColorRGB(1, 4, 30, 180, 160)

        with self.assertRaises(ValueError):
            IodineAPI.setNodeFillColorRGB(0, 1, -1, 180, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFillColorRGB(0, 1, 256, 180, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFillColorRGB(0, 1, 30, -1, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFillColorRGB(0, 1, 30, 256, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFillColorRGB(0, 1, 30, 180, -1)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFillColorRGB(0, 1, 30, 180, 256)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(hex(IodineAPI.getNodeFillColorRGB(0, 1)), '0xff9650')
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(hex(IodineAPI.getNodeFillColorRGB(0, 1)), '0x1eb4a0')

    def test_setNodeFillColorAlpha(self):
        self.assertAlmostEqual(IodineAPI.getNodeFillColorAlpha(0, 1), 1, 2)
        self.assertEqual(IodineAPI.setNodeFillColorAlpha(0, 1, 0.5), None)
        self.assertAlmostEqual(IodineAPI.getNodeFillColorAlpha(0, 1), 0.5, 2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFillColorAlpha(-1, 1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFillColorAlpha(3, 1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFillColorAlpha(1, -1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFillColorAlpha(1, 4, 1)

        with self.assertRaises(ValueError):
            IodineAPI.setNodeFillColorAlpha(0, 1, -0.1)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFillColorAlpha(0, 1, 1.1)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertAlmostEqual(IodineAPI.getNodeFillColorAlpha(0, 1), 1, 2)
        self.assertEqual(IodineAPI.redo(), None)
        self.assertAlmostEqual(IodineAPI.getNodeFillColorAlpha(0, 1), 0.5, 2)

    def test_setNodeOutlineColorRGB(self):
        self.assertEqual(hex(IodineAPI.getNodeOutlineColorRGB(0, 1)), '0xff6450')
        self.assertEqual(IodineAPI.setNodeOutlineColorRGB(
            0, 1, 30, 180, 160), None)
        self.assertEqual(
            hex(IodineAPI.getNodeOutlineColorRGB(0, 1)), '0x1eb4a0')
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeOutlineColorRGB(-1, 1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeOutlineColorRGB(3, 1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeOutlineColorRGB(1, -1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeOutlineColorRGB(1, 4, 30, 180, 160)

        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineColorRGB(0, 1, -1, 180, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineColorRGB(0, 1, 256, 180, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineColorRGB(0, 1, 30, -1, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineColorRGB(0, 1, 30, 256, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineColorRGB(0, 1, 30, 180, -1)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineColorRGB(0, 1, 30, 180, 256)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(
            hex(IodineAPI.getNodeOutlineColorRGB(0, 1)), '0xff6450')
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(
            hex(IodineAPI.getNodeOutlineColorRGB(0, 1)), '0x1eb4a0')

    def test_setNodeOutlineColorAlpha(self):
        self.assertAlmostEqual(IodineAPI.getNodeOutlineColorAlpha(0, 1), 1, 2)
        self.assertEqual(IodineAPI.setNodeOutlineColorAlpha(0, 1, 0.5), None)
        self.assertAlmostEqual(IodineAPI.getNodeOutlineColorAlpha(0, 1), 0.5, 2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeOutlineColorAlpha(-1, 1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeOutlineColorAlpha(3, 1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeOutlineColorAlpha(1, -1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeOutlineColorAlpha(1, 4, 1)

        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineColorAlpha(0, 1, -0.1)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineColorAlpha(0, 1, 1.1)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertAlmostEqual(IodineAPI.getNodeOutlineColorAlpha(0, 1), 1, 2)
        self.assertEqual(IodineAPI.redo(), None)
        self.assertAlmostEqual(IodineAPI.getNodeOutlineColorAlpha(0, 1), 0.5, 2)

    def test_setNodeOutlineThickness(self):
        self.assertEqual(IodineAPI.getNodeOutlineThickness(0, 1), 3)
        self.assertEqual(IodineAPI.setNodeOutlineThickness(0, 1, 1), None)
        self.assertEqual(IodineAPI.getNodeOutlineThickness(0, 1), 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeOutlineThickness(-1, 1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeOutlineThickness(3, 1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeOutlineThickness(1, -1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeOutlineThickness(1, 4, 1)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineThickness(0, 1, 0)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeOutlineThickness(0, 1, -1)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getNodeOutlineThickness(0, 1), 3)
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getNodeOutlineThickness(0, 1), 1)

    def test_setNodeFontPointSize(self):
        self.assertEqual(IodineAPI.getNodeFontPointSize(0, 1), 20)
        self.assertEqual(IodineAPI.setNodeFontPointSize(0, 1, 10), None)
        self.assertEqual(IodineAPI.getNodeFontPointSize(0, 1), 10)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontPointSize(-1, 1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontPointSize(3, 1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontPointSize(1, -1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontPointSize(1, 4, 1)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontPointSize(0, 1, 0)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontPointSize(0, 1, -1)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getNodeFontPointSize(0, 1), 20)
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getNodeFontPointSize(0, 1), 10)

    def test_setNodeFontFamily(self):
        self.assertEqual(IodineAPI.getNodeFontFamily(0, 1), "default")
        self.assertEqual(IodineAPI.setNodeFontFamily(0, 1, "decorative"), None)
        self.assertEqual(IodineAPI.getNodeFontFamily(0, 1), "decorative")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontFamily(-1, 1, "default")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontFamily(3, 1, "default")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontFamily(1, -1, "default")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontFamily(1, 1, "default")
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontFamily(0, 1, "Aefault")
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontFamily(0, 1, "normal")

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getNodeFontFamily(0, 1), "default")
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getNodeFontFamily(0, 1), "decorative")

    def test_setNodeFontStyle(self):
        self.assertEqual(IodineAPI.getNodeFontStyle(0, 1), "normal")
        self.assertEqual(IodineAPI.setNodeFontStyle(0, 1, "italic"), None)
        self.assertEqual(IodineAPI.getNodeFontStyle(0, 1), "italic")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontStyle(-1, 1, "normal")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontStyle(3, 1, "normal")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontStyle(1, -1, "normal")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontStyle(1, 1, "normal")
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontStyle(0, 1, "default")
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontStyle(0, 1, "Normal")

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getNodeFontStyle(0, 1), "normal")
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getNodeFontStyle(0, 1), "italic")

    def test_setNodeFontWeight(self):
        self.assertEqual(IodineAPI.getNodeFontWeight(0, 1), "default")
        self.assertEqual(IodineAPI.setNodeFontWeight(0, 1, "bold"), None)
        self.assertEqual(IodineAPI.getNodeFontWeight(0, 1), "bold")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontWeight(-1, 1, "default")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontWeight(3, 1, "default")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontWeight(1, -1, "default")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontWeight(1, 1, "default")
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontWeight(0, 1, "Default")
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontWeight(0, 1, "normal")

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getNodeFontWeight(0, 1), "default")
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getNodeFontWeight(0, 1), "bold")

    def test_setNodeFontName(self):
        self.assertEqual(IodineAPI.getNodeFontName(0, 1), "")
        self.assertEqual(IodineAPI.setNodeFontName(0, 1, "name1"), None)
        self.assertEqual(IodineAPI.getNodeFontName(0, 1), "name1")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontName(-1, 1, "")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontName(3, 1, "")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontName(1, -1, "")
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontName(1, 1, "")

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getNodeFontName(0, 1), "")
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getNodeFontName(0, 1), "name1")

    def test_setNodeFontColorRGB(self):
        self.assertEqual(
            hex(IodineAPI.getNodeFontColorRGB(0, 1)), '0x0')
        self.assertEqual(IodineAPI.setNodeFontColorRGB(
            0, 1, 30, 180, 160), None)
        self.assertEqual(
            hex(IodineAPI.getNodeFontColorRGB(0, 1)), '0x1eb4a0')
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontColorRGB(-1, 1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontColorRGB(3, 1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontColorRGB(1, -1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontColorRGB(1, 4, 30, 180, 160)

        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontColorRGB(0, 1, -1, 180, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontColorRGB(0, 1, 256, 180, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontColorRGB(0, 1, 30, -1, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontColorRGB(0, 1, 30, 256, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontColorRGB(0, 1, 30, 180, -1)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontColorRGB(0, 1, 30, 180, 256)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(
            hex(IodineAPI.getNodeFontColorRGB(0, 1)), '0x0')
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(
            hex(IodineAPI.getNodeFontColorRGB(0, 1)), '0x1eb4a0')

    def test_setNodeFontColorAlpha(self):
        self.assertAlmostEqual(IodineAPI.getNodeFontColorAlpha(0, 1), 1, 2)
        self.assertEqual(IodineAPI.setNodeFontColorAlpha(0, 1, 0.5), None)
        self.assertAlmostEqual(
            IodineAPI.getNodeFontColorAlpha(0, 1), 0.5, 2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontColorAlpha(-1, 1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setNodeFontColorAlpha(3, 1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontColorAlpha(1, -1, 1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.setNodeFontColorAlpha(1, 4, 1)

        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontColorAlpha(0, 1, -0.1)
        with self.assertRaises(ValueError):
            IodineAPI.setNodeFontColorAlpha(0, 1, 1.1)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertAlmostEqual(IodineAPI.getNodeFontColorAlpha(0, 1), 1, 2)
        self.assertEqual(IodineAPI.redo(), None)
        self.assertAlmostEqual(
            IodineAPI.getNodeFontColorAlpha(0, 1), 0.5, 2)


class TestReactionFunc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        IodineAPI.newNetwork("network1")
        IodineAPI.addNode(0, "node1", 1.1, 2.5, 5.4, 6.4)
        IodineAPI.addNode(0, "node2", 1.2, 3.2, 2.5, 4.1)
        IodineAPI.addNode(0, "node3", 2.2, 3.1, 1.5, 4.5)
        IodineAPI.addNode(0, "node4", 7.2, 3.5, 1.6, 4.8)
        IodineAPI.CreateBiBi(0, "Rea1", "k1*A",
                             0, 1, 2, 3, 1.1, 2.2, 3.3, 4.4)
        IodineAPI.CreateBiBi(0, "Rea2", "k2*A",
                             1, 3, 0, 2, 2.1, 5.2, 8.3, 7.4)

    def tearDown(self):
        IodineAPI.clearNetworks()

    def test_createReaction(self):
        self.assertEqual(IodineAPI.createReaction(0, "Rea3"), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(
            0), ["Rea1", "Rea2", "Rea3"])
        with self.assertRaises(IodineAPI.IDRepeatError):
            IodineAPI.createReaction(0, "Rea1")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.createReaction(-1, "Rea4")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.createReaction(1, "Rea4")
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0),
                         ["Rea1", "Rea2"])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0),
                         ["Rea1", "Rea2", "Rea3"])

    def test_getReactionIndex(self):
        self.assertEqual(IodineAPI.getReactionIndex(0, "Rea1"), 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionIndex(-1, "Rea1")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionIndex(1, "Rea1")
        with self.assertRaises(IodineAPI.IDNotFoundError):
            IodineAPI.getReactionIndex(0, "Rea3")

    def test_deleteReaction(self):
        self.assertEqual(IodineAPI.deleteReaction(0, 0), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), ["Rea2"])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.deleteReaction(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.deleteReaction(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.deleteReaction(0, -1)
        IodineAPI.deleteReaction(0, 1)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0),
                         ["Rea1", "Rea2"])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0),
                         ["Rea2"])

    def test_clearReactions(self):
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), ["Rea1", "Rea2"])
        self.assertEqual(IodineAPI.clearReactions(0), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), [])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.clearReactions(-1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.clearReactions(1)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0),
                         ["Rea1", "Rea2"])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), [])

    def test_getNumberOfReactions(self):
        self.assertEqual(IodineAPI.getNumberOfReactions(0), 2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNumberOfReactions(-1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNumberOfReactions(1)

    def test_getReactionID(self):
        self.assertEqual(IodineAPI.getReactionID(0, 0), "Rea1")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionID(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionID(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionID(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionID(0, 2)

    def test_getListOfReactionIDs(self):
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), ["Rea1", "Rea2"])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionIDs(-1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionIDs(1)

    def test_getReactionRateLaw(self):
        self.assertEqual(IodineAPI.getReactionRateLaw(0, 0), "k1*A")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionRateLaw(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionRateLaw(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionRateLaw(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionRateLaw(0, 2)

    def test_getReactionFillColor(self):
        self.assertEqual(
            IodineAPI.getReactionFillColor(0, 0), (255, 150, 80, 1.0))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionFillColor(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionFillColor(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionFillColor(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionFillColor(0, 2)

    def test_getReactionFillColorRGB(self):
        self.assertEqual(
            hex(IodineAPI.getReactionFillColorRGB(0, 0)), '0xff9650')
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionFillColorRGB(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionFillColorRGB(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionFillColorRGB(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionFillColorRGB(0, 2)

    def test_getReactionFillColorAlpha(self):
        self.assertAlmostEqual(IodineAPI.getReactionFillColorAlpha(0, 0), 1, 2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionFillColorAlpha(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionFillColorAlpha(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionFillColorAlpha(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionFillColorAlpha(0, 2)

    def test_getReactionLineThickness(self):
        self.assertEqual(IodineAPI.getReactionLineThickness(0, 0), 3)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionLineThickness(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionLineThickness(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionLineThickness(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionLineThickness(0, 2)

    def test_getReactionCenterHandlePosition(self):
        self.assertEqual(IodineAPI.getReactionCenterHandlePosition(0, 0), (0, 0))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionCenterHandlePosition(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionCenterHandlePosition(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionCenterHandlePosition(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionCenterHandlePosition(0, 2)

    def test_getReactionSrcNodeStoich(self):
        self.assertEqual(IodineAPI.getReactionSrcNodeStoich(0, 1, 3), 5.2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionSrcNodeStoich(-1, 0, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionSrcNodeStoich(1, 0, 1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionSrcNodeStoich(0, -1, 1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionSrcNodeStoich(0, 2, 1)

    def test_getReactionDestNodeStoich(self):
        self.assertEqual(IodineAPI.getReactionDestNodeStoich(0, 1, 2), 7.4)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionDestNodeStoich(-1, 0, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionDestNodeStoich(1, 0, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionDestNodeStoich(0, -1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionDestNodeStoich(0, 2, 0)

    def test_getReactionSrcNodeHandlePosition(self):
        self.assertEqual(IodineAPI.getReactionSrcNodeHandlePosition(0, 1, 3), (0, 0))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionSrcNodeHandlePosition(-1, 0, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionSrcNodeHandlePosition(1, 0, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionSrcNodeHandlePosition(0, -1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionSrcNodeHandlePosition(0, 2, 0)

    def test_getReactionDestNodeHandlePosition(self):
        self.assertEqual(IodineAPI.getReactionDestNodeHandlePosition(0, 1, 2), (0, 0))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionDestNodeHandlePosition(-1, 0, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getReactionDestNodeHandlePosition(1, 0, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionDestNodeHandlePosition(0, -1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getReactionDestNodeHandlePosition(0, 2, 0)

    def test_getNumberOfSrcNodes(self):
        self.assertEqual(IodineAPI.getNumberOfSrcNodes(0, 1), 2)
        IodineAPI.addSrcNode(0, 1, 2, 3.1)
        self.assertEqual(IodineAPI.getNumberOfSrcNodes(0, 1), 3)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNumberOfSrcNodes(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNumberOfSrcNodes(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getNumberOfSrcNodes(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getNumberOfSrcNodes(0, 2)

    def test_getNumberOfDestNodes(self):
        self.assertEqual(IodineAPI.getNumberOfDestNodes(0, 1), 2)
        IodineAPI.addDestNode(0, 1, 1, 5.5)
        self.assertEqual(IodineAPI.getNumberOfDestNodes(0, 1), 3)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNumberOfDestNodes(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getNumberOfDestNodes(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getNumberOfDestNodes(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getNumberOfDestNodes(0, 2)

    def test_getListOfReactionSrcNodes(self):
        self.assertEqual(IodineAPI.getListOfReactionSrcNodes(
            0, 1), [1, 3])
        IodineAPI.addSrcNode(0, 1, 2, 3.1)
        self.assertEqual(IodineAPI.getListOfReactionSrcNodes(
            0, 1), [1, 2, 3])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionSrcNodes(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionSrcNodes(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getListOfReactionSrcNodes(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getListOfReactionSrcNodes(0, 2)

    def test_getListOfReactionDestNodes(self):
        self.assertEqual(IodineAPI.getListOfReactionDestNodes(
            0, 1), [0, 2])
        IodineAPI.addDestNode(0, 1, 1, 5.5)
        self.assertEqual(IodineAPI.getListOfReactionDestNodes(
            0, 1), [0, 1, 2])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionDestNodes(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionDestNodes(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getListOfReactionDestNodes(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getListOfReactionDestNodes(0, 2)

    def test_getListOfReactionSrcStoich(self):
        self.assertEqual(IodineAPI.getListOfReactionSrcStoich(
            0, 1), [2.1, 5.2])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionSrcStoich(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionSrcStoich(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getListOfReactionSrcStoich(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getListOfReactionSrcStoich(0, 2)

    def test_getListOfReactionDestStoich(self):
        self.assertEqual(IodineAPI.getListOfReactionDestStoich(
            0, 1), [8.3, 7.4])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionDestStoich(-1, 0)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.getListOfReactionDestStoich(1, 0)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getListOfReactionDestStoich(0, -1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.getListOfReactionDestStoich(0, 2)


class TestReactionNodeFunc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        IodineAPI.newNetwork("network1")
        IodineAPI.addNode(0, "node1", 1.1, 2.5, 5.4, 6.4)
        IodineAPI.addNode(0, "node2", 1.2, 3.2, 2.5, 4.1)
        IodineAPI.addNode(0, "node3", 2.2, 3.1, 1.5, 4.5)
        IodineAPI.addNode(0, "node4", 7.2, 3.5, 1.6, 4.8)
        IodineAPI.addNode(0, "node5", 6.4, 7.1, 9.9, 1.2)
        IodineAPI.addNode(0, "node6", 5.8, 7.3, 4.5, 6.2)
        IodineAPI.CreateBiBi(0, "Rea1", "k1*A",
                             0, 1, 2, 3, 1.1, 2.2, 3.3, 4.4)
        IodineAPI.CreateBiBi(0, "Rea2", "k2*A",
                             3, 1, 2, 0, 2.1, 5.2, 8.3, 7.4)

    def tearDown(self):
        IodineAPI.clearNetworks()

    def test_addSrcNode(self):
        self.assertEqual(IodineAPI.addSrcNode(0, 0, 4, 5.1), None)
        self.assertEqual(IodineAPI.getListOfReactionSrcNodes(
            0, 0), [0, 1, 4])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.addSrcNode(-1, 0, 3, 1.1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.addSrcNode(1, 0, 3, 1.1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.addSrcNode(0, -1, 3, 1.1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.addSrcNode(0, 2, 3, 1.1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.addSrcNode(0, 0, -1, 1.1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.addSrcNode(0, 0, 6, 1.1)
        with self.assertRaises(IodineAPI.StoichError):
            IodineAPI.addSrcNode(0, 0, 3, -1)
        with self.assertRaises(IodineAPI.StoichError):
            IodineAPI.addSrcNode(0, 0, 3, 0)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfReactionSrcNodes(0, 0),
                         [0, 1])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfReactionSrcNodes(0, 0),
                         [0, 1, 4])

    def test_addDestNode(self):
        self.assertEqual(IodineAPI.addDestNode(0, 0, 4, 5.1), None)
        self.assertEqual(IodineAPI.getListOfReactionDestNodes(
            0, 0), [2, 3, 4])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.addDestNode(-1, 0, 3, 1.1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.addDestNode(1, 0, 3, 1.1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.addDestNode(0, -1, 3, 1.1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.addDestNode(0, 2, 3, 1.1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.addDestNode(0, 0, -1, 1.1)
        with self.assertRaises(IodineAPI.NodeIndexNotFoundError):
            IodineAPI.addDestNode(0, 0, 6, 1.1)
        with self.assertRaises(IodineAPI.StoichError):
            IodineAPI.addDestNode(0, 0, 3, -1.1)
        with self.assertRaises(IodineAPI.StoichError):
            IodineAPI.addDestNode(0, 0, 3, 0.0)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfReactionDestNodes(0, 0),
                         [2, 3])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfReactionDestNodes(0, 0),
                         [2, 3, 4])

    def test_deleteSrcNode(self):
        IodineAPI.addSrcNode(0, 1, 4, 5.5)
        IodineAPI.addSrcNode(0, 1, 2, 5.6)
        self.assertEqual(IodineAPI.getListOfReactionSrcNodes(0, 1),
                         [1, 2, 3, 4])
        self.assertEqual(IodineAPI.deleteSrcNode(0, 1, 1), None)
        self.assertEqual(IodineAPI.getListOfReactionSrcNodes(0, 1),
                         [2, 3, 4])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.deleteSrcNode(-1, 1, 3)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.deleteSrcNode(1, 1, 3)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.deleteSrcNode(0, -1, 3)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.deleteSrcNode(0, 2, 3)
        with self.assertRaises(IodineAPI.IDNotFoundError):
            IodineAPI.deleteSrcNode(0, 1, 1)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfReactionSrcNodes(0, 1),
                         [1, 2, 3, 4])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfReactionSrcNodes(0, 1),
                         [2, 3, 4])

    def test_deleteDestNode(self):
        IodineAPI.addDestNode(0, 1, 5, 5.3)
        self.assertEqual(IodineAPI.getListOfReactionDestNodes(0, 1), [0, 2, 5])
        self.assertEqual(IodineAPI.deleteDestNode(0, 1, 0), None)
        self.assertEqual(IodineAPI.getListOfReactionDestNodes(0, 1), [2, 5])
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.deleteDestNode(-1, 1, 3)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.deleteDestNode(1, 1, 3)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.deleteDestNode(0, -1, 3)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.deleteDestNode(0, 2, 3)
        with self.assertRaises(IodineAPI.IDNotFoundError):
            IodineAPI.deleteDestNode(0, 1, 4)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfReactionDestNodes(0, 1),
                         [0, 2, 5])
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getListOfReactionDestNodes(0, 1),
                         [2, 5])

    def test_setReactionID(self):
        self.assertEqual(IodineAPI.getReactionID(0, 1), "Rea2")
        self.assertEqual(IodineAPI.setReactionID(0, 1,  "ABC"), None)
        self.assertEqual(IodineAPI.getReactionID(0, 1), "ABC")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionID(-1, 1, "ABC")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionID(1, 1, "ABC")
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionID(0, -1, "ABC")
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionID(0, 2, "ABC")
        with self.assertRaises(IodineAPI.IDRepeatError):
            IodineAPI.setReactionID(0, 1, "Rea1")
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getReactionID(0, 1), "Rea2")
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getReactionID(0, 1), "ABC")

    def test_setRateLaw(self):
        self.assertEqual(IodineAPI.getReactionRateLaw(
            0, 1), "k2*A")
        self.assertEqual(IodineAPI.setRateLaw(
            0, 1,  "ABC"), None)
        self.assertEqual(IodineAPI.getReactionRateLaw(
            0, 1), "ABC")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setRateLaw(-1, 1, "ABC")
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setRateLaw(1, 1, "ABC")
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setRateLaw(0, -1, "ABC")
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setRateLaw(0, 2, "ABC")
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getReactionRateLaw(0, 1), "k2*A")
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getReactionRateLaw(0, 1), "ABC")

    def test_setReactionSrcNodeStoich(self):
        self.assertEqual(IodineAPI.getReactionSrcNodeStoich(0, 0, 0), 1.1)
        self.assertEqual(IodineAPI.setReactionSrcNodeStoich(
            0, 0,  1, 3.1), None)
        self.assertEqual(IodineAPI.getReactionSrcNodeStoich(
            0, 0, 1), 3.1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionSrcNodeStoich(-1, 0, 1, 3.1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionSrcNodeStoich(1, 0, 1, 3.1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionSrcNodeStoich(0, -1, 1, 3.1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionSrcNodeStoich(0, 2, 1, 3.1)
        with self.assertRaises(IodineAPI.StoichError):
            IodineAPI.setReactionSrcNodeStoich(0, 0, 1, 0)
        with self.assertRaises(IodineAPI.StoichError):
            IodineAPI.setReactionSrcNodeStoich(0, 0, 1, -3.1)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(
            IodineAPI.getReactionSrcNodeStoich(0, 0, 0), 1.1)
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getReactionSrcNodeStoich(0, 0, 1), 3.1)

    def test_setReactionDestNodeStoich(self):
        self.assertEqual(IodineAPI.getReactionDestNodeStoich(
            0, 0, 2), 3.3)
        self.assertEqual(IodineAPI.setReactionDestNodeStoich(
            0, 0, 2, 3.1), None)
        self.assertEqual(IodineAPI.getReactionDestNodeStoich(
            0, 0, 2), 3.1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionDestNodeStoich(-1, 0, 3, 3.1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionDestNodeStoich(1, 0, 3, 3.1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionDestNodeStoich(0, -1, 3, 3.1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionDestNodeStoich(0, 2, 3, 3.1)
        with self.assertRaises(IodineAPI.StoichError):
            IodineAPI.setReactionDestNodeStoich(0, 0, 3, 0)
        with self.assertRaises(IodineAPI.StoichError):
            IodineAPI.setReactionDestNodeStoich(0, 0, 3, -3.1)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(
            IodineAPI.getReactionDestNodeStoich(0, 0, 2), 3.3)
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(
            IodineAPI.getReactionDestNodeStoich(0, 0, 2), 3.1)

    def test_setReactionSrcNodeHandlePosition(self):
        self.assertEqual(IodineAPI.getReactionSrcNodeHandlePosition(
            0, 0, 1), (0, 0))
        self.assertEqual(IodineAPI.setReactionSrcNodeHandlePosition(
            0, 0,  1, 2.1, 3.2), None)
        self.assertEqual(IodineAPI.getReactionSrcNodeHandlePosition(
            0, 0, 1), (2.1, 3.2))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionSrcNodeHandlePosition(-1, 0, 1, 2.1, 3.2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionSrcNodeHandlePosition(1, 0, 1, 2.1, 3.2)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionSrcNodeHandlePosition(0, -1, 1, 2.1, 3.2)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(
            IodineAPI.getReactionSrcNodeHandlePosition(0, 0, 1), (0, 0))
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(
            IodineAPI.getReactionSrcNodeHandlePosition(0, 0, 1), (2.1, 3.2))

    def test_setReactionDestNodeHandlePosition(self):
        self.assertEqual(IodineAPI.getReactionDestNodeHandlePosition(
            0, 0, 3), (0, 0))
        self.assertEqual(IodineAPI.setReactionDestNodeHandlePosition(
            0, 0,  3, 2.1, 3.2), None)
        self.assertEqual(IodineAPI.getReactionDestNodeHandlePosition(
            0, 0, 3), (2.1, 3.2))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionDestNodeHandlePosition(
                -1, 0, 3, 2.1, 3.2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionDestNodeHandlePosition(
                1, 0, 3, 2.1, 3.2)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionDestNodeHandlePosition(
                0, -1, 3, 2.1, 3.2)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionDestNodeHandlePosition(
                0, 2, 3, 2.1, 3.2)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(
            IodineAPI.getReactionDestNodeHandlePosition(0, 0, 3), (0, 0))
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(
            IodineAPI.getReactionDestNodeHandlePosition(0, 0, 3), (2.1, 3.2))

    def test_setReactionFillColorRGB(self):
        self.assertEqual(
            hex(IodineAPI.getReactionFillColorRGB(0, 1)), '0xff9650')
        self.assertEqual(IodineAPI.setReactionFillColorRGB(
            0, 1, 30, 180, 160), None)
        self.assertEqual(
            hex(IodineAPI.getReactionFillColorRGB(0, 1)), '0x1eb4a0')
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionFillColorRGB(-1, 1, 30, 180, 160)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionFillColorRGB(3, 1, 30, 180, 160)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionFillColorRGB(0, -1, 30, 180, 160)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionFillColorRGB(0, 4, 30, 180, 160)

        with self.assertRaises(ValueError):
            IodineAPI.setReactionFillColorRGB(0, 1, -1, 180, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setReactionFillColorRGB(0, 1, 256, 180, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setReactionFillColorRGB(0, 1, 30, -1, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setReactionFillColorRGB(0, 1, 30, 256, 160)
        with self.assertRaises(ValueError):
            IodineAPI.setReactionFillColorRGB(0, 1, 30, 180, -1)
        with self.assertRaises(ValueError):
            IodineAPI.setReactionFillColorRGB(0, 1, 30, 180, 256)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(
            hex(IodineAPI.getReactionFillColorRGB(0, 1)), '0xff9650')
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(
            hex(IodineAPI.getReactionFillColorRGB(0, 1)), '0x1eb4a0')

    def test_setReactionFillColorAlpha(self):
        self.assertAlmostEqual(IodineAPI.getReactionFillColorAlpha(0, 1), 1, 2)
        self.assertEqual(IodineAPI.setReactionFillColorAlpha(
            0, 1, 0.5), None)
        self.assertAlmostEqual(IodineAPI.getReactionFillColorAlpha(0, 1), 0.5, 2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionFillColorAlpha(-1, 1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionFillColorAlpha(3, 1, 1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionFillColorAlpha(0, -1, 1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionFillColorAlpha(0, 4, 1)

        with self.assertRaises(ValueError):
            IodineAPI.setReactionFillColorAlpha(0, 1, -0.1)
        with self.assertRaises(ValueError):
            IodineAPI.setReactionFillColorAlpha(0, 1, 1.1)

        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertAlmostEqual(IodineAPI.getReactionFillColorAlpha(0, 1), 1, 2)
        self.assertEqual(IodineAPI.redo(), None)
        self.assertAlmostEqual(IodineAPI.getReactionFillColorAlpha(0, 1), 0.5, 2)

    def test_setReactionLineThickness(self):
        self.assertEqual(IodineAPI.getReactionLineThickness(0, 1), 3)
        self.assertEqual(IodineAPI.setReactionLineThickness(0, 1, 1), None)
        self.assertEqual(IodineAPI.getReactionLineThickness(0, 1), 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionLineThickness(-1, 1, 1)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionLineThickness(3, 1, 1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionLineThickness(0, -1, 1)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionLineThickness(0, 4, 1)
        with self.assertRaises(ValueError):
            IodineAPI.setReactionLineThickness(0, 1, 0)
        with self.assertRaises(ValueError):
            IodineAPI.setReactionLineThickness(0, 1, -1)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getReactionLineThickness(0, 1), 3)
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getReactionLineThickness(0, 1), 1)

    def test_setReactionCenterHandlePosition(self):
        self.assertEqual(IodineAPI.getReactionCenterHandlePosition(0, 1), (0, 0))
        self.assertEqual(IodineAPI.setReactionCenterHandlePosition(0, 1, 2.1, 3.2), None)
        self.assertEqual(
            IodineAPI.getReactionCenterHandlePosition(0, 1), (2.1, 3.2))
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionCenterHandlePosition(-1, 1, 2.1, 3.2)
        with self.assertRaises(IodineAPI.NetIndexNotFoundError):
            IodineAPI.setReactionCenterHandlePosition(3, 1, 2.1, 3.2)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionCenterHandlePosition(0, -1, 2.1, 3.2)
        with self.assertRaises(IodineAPI.ReactionIndexError):
            IodineAPI.setReactionCenterHandlePosition(0, 4, 2.1, 3.2)
        with self.assertRaises(IodineAPI.StackEmptyError):
            IodineAPI.redo()
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getReactionCenterHandlePosition(0, 1), (0, 0))
        self.assertEqual(IodineAPI.redo(), None)
        self.assertEqual(IodineAPI.getReactionCenterHandlePosition(0, 1), (2.1, 3.2))

    '''
    def test_saveNetworkAsJSON_readNetworkFromJSON(self):
        self.assertEqual(IodineAPI.saveNetworkAsJSON(0, "../JSON_files/testfile.json"), None)
        self.assertEqual(IodineAPI.readNetworkFromJSON(
            "../JSON_files/testfile1.json"), None)
        with self.assertRaises(IodineAPI.FileError):
            IodineAPI.readNetworkFromJSON("testfdfjsd.json")
        with self.assertRaises(IodineAPI.IDRepeatError):
            IodineAPI.readNetworkFromJSON("../JSON_files/testfile1.json")
    '''

    def test_startGroup_endGroup(self):
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), ["Rea1", "Rea2"])
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), ["Rea1"])
        self.assertEqual(IodineAPI.startGroup(), None)
        self.assertEqual(IodineAPI.createReaction(0, "rea2"), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), ["Rea1", "rea2"])
        self.assertEqual(IodineAPI.addSrcNode(0, 0, 4, 5.1), None)
        self.assertEqual(IodineAPI.endGroup(), None)
        self.assertEqual(IodineAPI.undo(), None)
        self.assertEqual(IodineAPI.getListOfReactionIDs(0), ["Rea1"])


class TestCompartmentFunc(unittest.TestCase):
    def setUp(self):
        IodineAPI.newNetwork("network1")
        IodineAPI.newNetwork("network2")
        IodineAPI.addNode(neti=0, nodeID="node1", x=1.1, y=2.5, w=5.4, h=6.4)
        IodineAPI.addNode(0, "node2", 1.2, 3.2, 2.5, 4.1)
        IodineAPI.addNode(0, "node3", 2.2, 3.1, 1.5, 4.5)
        IodineAPI.addNode(0, "node4", 7.2, 3.5, 1.6, 4.8)
        IodineAPI.addNode(0, "node5", 10.2, 3.5, 1.6, 4.8)
        IodineAPI.CreateBiBi(0, "Rea1", "k1*A",
                             0, 1, 2, 3, 1.1, 2.2, 3.3, 4.4)
        IodineAPI.addCompartment(neti=0, compID="comp1", x=4.2, y=5.3, w=12.3, h=7.1)
        IodineAPI.addCompartment(neti=0, compID="comp2", x=3.1, y=0.1, w=2.3, h=8.1)

    def tearDown(self):
        IodineAPI.clearNetworks()

    def test_addCompartment(self):
        IodineAPI.addCompartment(0, "comp3", x=0.1, y=12, w=124.2, h=200)
        self.assertEqual([0, 1, 2], IodineAPI.getListOfCompartments(0))
        self.assertEqual(IodineAPI.getCompartmentID(0, 2), "comp3")
        self.assertEqual(IodineAPI.getCompartmentID(0, 2), "comp3")
        self.assertEqual(IodineAPI.getCompartmentPosition(0, 2), (0.1, 12))
        self.assertEqual(IodineAPI.getCompartmentSize(0, 1), (2.3, 8.1))
        with self.assertRaises(NetIndexNotFoundError):
            IodineAPI.addCompartment(12, "Adam", x=2, y=3, w=4, h=6)
        with self.assertRaises(ValueError):
            IodineAPI.addCompartment(0, "comp4", x=-1, y=3, w=32, h=10)
        with self.assertRaises(ValueError):
            IodineAPI.addCompartment(0, "comp4", x=0.6, y=0.2, w=-9, h=-12)
        with self.assertRaises(IDRepeatError):
            IodineAPI.addCompartment(0, "comp2", x=0.6, y=0.2, w=9, h=12)
        IodineAPI.addCompartment(0, "comp4", x=0, y=0, w=0, h=0)

    def test_deleteCompartment(self):
        IodineAPI.deleteCompartment(0, 0)
        self.assertEqual([1], IodineAPI.getListOfCompartments(0))
        IodineAPI.addCompartment(0, "comp3", x=0.2, y=3.4, w=2.3, h=5.2)
        self.assertEqual(IodineAPI.getListOfCompartments(0), [1, 2])
        with self.assertRaises(NetIndexNotFoundError):
            IodineAPI.deleteCompartment(3, 1)
        with self.assertRaises(CompartmentIndexError):
            IodineAPI.deleteCompartment(0, 4)

    def test_addNodeToCompartment(self):
        self.assertEqual(IodineAPI.getNodesInCompartment(0, 0), [])
        self.assertEqual(IodineAPI.getNodesInCompartment(0, -1), [0, 1, 2, 3, 4])
        self.assertEqual(IodineAPI.getCompartmentOfNode(0, 0), -1)

        IodineAPI.setCompartmentOfNode(neti=0, nodei=0, compi=0)
        self.assertEqual(IodineAPI.getCompartmentOfNode(0, 0), 0)
        self.assertEqual(IodineAPI.getNodesInCompartment(0, 0), [0])
        self.assertEqual(IodineAPI.getNodesInCompartment(0, -1), [1, 2, 3, 4])

        IodineAPI.setCompartmentOfNode(neti=0, nodei=0, compi=1)
        self.assertEqual(IodineAPI.getCompartmentOfNode(0, 0), 1)
        self.assertEqual(IodineAPI.getNodesInCompartment(0, 1), [0])
        self.assertEqual(IodineAPI.getNodesInCompartment(0, 0), [])
        self.assertEqual(IodineAPI.getNodesInCompartment(0, -1), [1, 2, 3, 4])

        IodineAPI.setCompartmentOfNode(neti=0, nodei=2, compi=1)
        self.assertEqual(IodineAPI.getNodesInCompartment(0, 1), [0, 2])

        IodineAPI.setCompartmentOfNode(neti=0, nodei=2, compi=-1)
        self.assertEqual(IodineAPI.getNodesInCompartment(0, 1), [0])
        self.assertEqual(IodineAPI.getNodesInCompartment(0, -1), [1, 2, 3, 4])

    def test_deleteNodeInCompartment(self):
        IodineAPI.deleteNode(0, 4)
        self.assertEqual(IodineAPI.getNodesInCompartment(0, -1), [0, 1, 2, 3])

        IodineAPI.setCompartmentOfNode(0, nodei=2, compi=1)
        self.assertEqual(IodineAPI.getNodesInCompartment(0, 1), [2])
        self.assertEqual(IodineAPI.getNodesInCompartment(0, -1), [0, 1, 3])

        IodineAPI.deleteReaction(0, 0)
        IodineAPI.deleteNode(0, 2)
        self.assertEqual(IodineAPI.getNodesInCompartment(0, 1), [])
        self.assertEqual(IodineAPI.getNodesInCompartment(0, -1), [0, 1, 3])

    def test_compartmentNotFound(self):
        with self.assertRaises(CompartmentIndexError):
            IodineAPI.deleteCompartment(0, 5)
        
        with self.assertRaises(CompartmentIndexError):
            IodineAPI.setCompartmentOfNode(0, 0, 7)

        with self.assertRaises(CompartmentIndexError):
            IodineAPI.getNodesInCompartment(0, -2)

    def test_compartmentUndoAndRedo(self):
        self.assertEqual(IodineAPI.getListOfCompartments(0), [0, 1])
        IodineAPI.addCompartment(0, "Alexander", 12, 43, 21, 10)
        self.assertEqual(IodineAPI.getListOfCompartments(0), [0, 1, 2])
        IodineAPI.undo()
        self.assertEqual(IodineAPI.getListOfCompartments(0), [0, 1])

        IodineAPI.setCompartmentOfNode(0, 2, 1)
        IodineAPI.undo()
        self.assertEqual(IodineAPI.getCompartmentOfNode(0, 2), -1)
        IodineAPI.redo()
        self.assertEqual(IodineAPI.getCompartmentOfNode(0, 2), 1)

    # TODO more tests can be added for undo/redo, and also for the fill/stroke/etc. functions.


if __name__ == '__main__':
    unittest.main()
