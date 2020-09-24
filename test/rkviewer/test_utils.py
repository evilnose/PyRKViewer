import unittest
import copy
from rkviewer.canvas.geometry import Rect, Vec2, within_rect, clamp_rect_pos, clamp_point, \
    rects_overlap, get_bounding_rect


class TestRectUtils(unittest.TestCase):
    def test_within_rect(self):
        pos = Vec2(50, 50)
        rect = Rect(Vec2(40, 40), Vec2(20, 65.0))
        self.assertTrue(within_rect(pos, rect))

        rect = Rect(Vec2(50, 45), Vec2(21, 716.0))
        self.assertTrue(within_rect(pos, rect))

        rect = Rect(Vec2(50, 50), Vec2(0, 0))
        self.assertTrue(within_rect(pos, rect))

        pos = Vec2(-12, -37)
        rect = Rect(Vec2(-40, -39), Vec2(28, 2))
        self.assertTrue(within_rect(pos, rect))

    def test_not_within_rect(self):
        pos = Vec2(40, 40)
        rect = Rect(Vec2(15, 20), Vec2(50, 12))
        self.assertFalse(within_rect(pos, rect))

        rect = Rect(Vec2(30, 12), Vec2(4, 0.53))
        self.assertFalse(within_rect(pos, rect))

        rect = Rect(Vec2(41, 20), Vec2(104134, 41414))
        self.assertFalse(within_rect(pos, rect))

    def test_get_bounding_rect(self):
        data = [
            ((12, 30), (14, 50)),
            ((27, -15), (0.4, 23)),
            ((-154, -13.311), (166, 51)),
            ((33.2, 43), (17.24, 0.1)),
        ]
        rects = [Rect(Vec2(p), Vec2(s)) for p, s in data]
        bound = get_bounding_rect(rects)
        self.assertEqual(bound.position, Vec2(-154, -15))
        self.assertEqual(bound.size, Vec2(204.44, 95))

        bound = get_bounding_rect(rects, padding=10)
        self.assertEqual(bound.position, Vec2(-164, -25))
        self.assertEqual(bound.size, Vec2(224.44, 115))

    def test_clamp_rect_pos(self):
        clamped = Rect(Vec2(-23, -44), Vec2(5, 0.4))
        clamped_copy = copy.copy(clamped)
        bounds = Rect(Vec2(), Vec2(12, 44))
        self.assertEqual(clamp_rect_pos(clamped, bounds), Vec2(0, 0))
        self.assertEqual(clamped, clamped_copy, "clamped rect was modified!")

        clamped = Rect(Vec2(15, 700), Vec2(4, 32))
        bounds = Rect(Vec2(10, 3), Vec2(20, 60))
        self.assertEqual(clamp_rect_pos(clamped, bounds), Vec2(15, 31))

    def test_clamp_rect_pos_padding(self):
        clamped = Rect(Vec2(-23, -44), Vec2(5, 0.4))
        bounds = Rect(Vec2(10, 32.67), Vec2(34, 71))
        self.assertEqual(clamp_rect_pos(clamped, bounds, padding=10), Vec2(20, 42.67))

    def test_clamp_rect_pos_exception(self):
        clamped = Rect(Vec2(43, 13), Vec2(6, 155))
        bounds = Rect(Vec2(), Vec2(12, 44))
        with self.assertRaises(ValueError):
            clamp_rect_pos(clamped, bounds)

        bounds = Rect(Vec2(179, 13), Vec2(8, 200))
        with self.assertRaises(ValueError):
            clamp_rect_pos(clamped, bounds, padding=2)

    def test_clamp_rect_pos_zero(self):
        bounds_pos = Vec2(100, 1722)
        clamped = Rect(Vec2(), Vec2(10, 10))
        bounds = Rect(bounds_pos, Vec2(10, 10))
        self.assertEqual(clamp_rect_pos(clamped, bounds), bounds_pos)

    def test_clamp_point(self):
        pos = Vec2(-17.2, 108)
        bounds = Rect(Vec2(10, 27), Vec2(178, 32.4123))
        self.assertEqual(clamp_point(pos, bounds), Vec2(10, 59.4123))

    def test_rects_overlap(self):
        rect1 = Rect(Vec2(102, 200), Vec2(50, 43))
        rect2 = Rect(Vec2(97, 88), Vec2(8, 155))
        self.assertTrue(rects_overlap(rect1, rect2))

        # rect is long and flat, and neither rect has vertices within the other.
        rect2 = Rect(Vec2(80, 210), Vec2(401, 10.2))
        self.assertTrue(rects_overlap(rect1, rect2))

        # the rects are touching
        rect2 = Rect(Vec2(92, 70), Vec2(10, 175))
        self.assertTrue(rects_overlap(rect1, rect2))

    def test_rects_not_overlap(self):
        rect1 = Rect(Vec2(43, 11), Vec2(40, 88))
        rect2 = Rect(Vec2(30, 8), Vec2(20, 0.5))
        self.assertFalse(rects_overlap(rect1, rect2))

        rect2 = Rect(Vec2(84, 99.41431), Vec2(4, 0.003))
        self.assertFalse(rects_overlap(rect1, rect2))
