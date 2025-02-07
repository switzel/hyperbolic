import math, cmath
import numpy as np

from .. import util
from ..euclid import Circle, Arc, Line, intersection
from . import Point, Ideal


class Transform:
    def __init__(self, a,b,c,d,e=1,conj=False):
        self.abcd = a*e,b*e,c,d
        self.conj = conj
    def __repr__(self):
        return '{}({}, {}, {}, {}{})'.format(type(self).__name__,
                *map(lambda z:complex(round(z.real,3),round(z.imag,3)),
                     self.abcd),
                ', conj' if self.conj else '')
    def apply_to_tuple(self, point):
        z = complex(*point)
        if self.conj:
            z = z.conjugate()
        a,b,c,d = self.abcd
        numer = a*z + b
        denom = c*z + d
        if util.near_zero(abs(denom)):
            zt = numer * 1e5
        else:
            zt = numer / denom
        return zt.real, zt.imag
    def apply_to_point(self, point):
        return Point(*self.apply_to_tuple(point))
    def apply_to_ideal(self, point, verify=False):
        x, y = self.apply_to_tuple(point)
        if verify and not util.near_zero(math.hypot(x, y) - 1):
            raise ValueError('Invalid transform')
        return Ideal(math.atan2(y, x))
    def apply_to_list(self, points, verify=False):
        def apply(pt):
            if isinstance(pt, Ideal):
                if verify:
                    return self.apply_to_ideal(pt, verify=True)
                else:
                    return self.apply_to_ideal(pt)
            elif isinstance(pt, Point):
                return self.apply_to_point(pt)
            else:
                return self.apply_to_tuple(pt)
        return [apply(p) for p in points]
    def apply_to_shape(self, shape):
        '''Transform a euclidean shape.

        Supports euclidean Circle, Arc, and Line.
        '''
        if isinstance(shape, (Arc, Line)):
            closed = False
            p1 = shape.start_point()
            p2 = shape.midpoint()
            p3 = shape.end_point()
        elif isinstance(shape, Circle):
            closed = True
            p1 = shape.cx+shape.r, shape.cy
            p2 = shape.cx, shape.cy+shape.r
            p3 = shape.cx-shape.r, shape.cy
            if not shape.cw:
                p1, p3 = p3, p1
        else:
            raise TypeError('Unsupported shape: {}'.format(shape))
        # Transform
        p1, p2, p3 = self.apply_to_list((p1, p2, p3))
        # Create shape
        try:
            # See if it is an arc or circle
            out = Arc.from_points(*p1, *p3, *p2)
            if closed:  # It's a circle
                out = Circle(out.cx, out.cy, out.r, cw=out.cw)
            return out
        except (intersection.InfiniteIntersections, np.linalg.LinAlgError):
            # It is a line
            return Line(*p1, *p3)
    def __call__(self, *points, verify=False):
        return self.apply_to_list(points, verify=verify)
    def inverted(self):
        a,b,c,d = self.abcd
        if self.conj:
            a,b,c,d = a.conjugate(), b.conjugate(), c.conjugate(), d.conjugate()
        return Transform(-d,b,c,-a,conj=self.conj)
    def conjugate(self):
        a, b, c, d = self.abcd
        return Transform(a.conjugate(), b.conjugate(),
                         c.conjugate(), d.conjugate(), conj=not self.conj)
    @staticmethod
    def identity():
        return Transform(1,0,0,1,1)
    @staticmethod
    def merge(*transfoms):
        a,b,c,d = 1,0,0,1
        conj = False
        for i, trans in enumerate(transfoms):
            a2,b2,c2,d2 = trans.abcd
            if trans.conj:
                a,b,c,d = (a.conjugate(), b.conjugate(), c.conjugate(),
                        d.conjugate())
                conj = not conj
            a,b,c,d = a*a2+c*b2, b*a2+d*b2, a*c2+c*d2, b*c2+d*d2
        return Transform(a,b,c,d,conj=conj)
    @staticmethod
    def shift_origin(new_origin, new_x=None):
        z0 = complex(*new_origin)
        a,b,c,d = 1,-z0,(-z0).conjugate(),1
        if new_x is not None:
            z1 = complex(*new_x)
            e = (c*z1 + d) / (a*z1 + b)
            e /= abs(e)
        else:
            e = 1
        return Transform(a,b,c,d,e)
    @classmethod
    def translation(cls, offset, rotation=None):
        return cls.shift_origin(offset, new_x=rotation).inverted()
    @staticmethod
    def rotation(rad=None, deg=None, vec=None):
        assert (rad is None) + (deg is None) + (vec is None) == 2
        if vec is not None:
            z = complex(*vec)
            e = z / abs(z)
        else:
            if deg is not None:
                rad = math.radians(deg)
            e = cmath.rect(1, rad)
        return Transform(1,0,0,1,e)
    @staticmethod
    def mirror(p1=None, p2=(0,0)):
        if p1 is None:
            p1, p2 = p2, (1,0)
        z1, z2 = complex(*p1), complex(*p2)
        z1c, z2c = z1.conjugate(), z2.conjugate()
        a = z1*z2*z1c - z1*z2*z2c - z1 + z2
        b = z1*z2c - z2*z1c
        return Transform(a, b, -b, a.conjugate(), conj=True)

    @staticmethod
    def disk_to_half():
        return Transform(1j, -1, -1, 1j)
    @staticmethod
    def half_to_disk():
        return Transform.disk_to_half().inverted()
