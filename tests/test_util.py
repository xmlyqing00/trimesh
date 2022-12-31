import trimesh
import unittest
import logging
import numpy as np

try:
    from . import generic as g
except BaseException:
    import generic as g

TEST_DIM = (100, 3)
TOL_ZERO = 1e-9
TOL_CHECK = 1e-2

log = logging.getLogger('trimesh')
log.addHandler(logging.NullHandler())


class VectorTests(unittest.TestCase):

    def setUp(self):
        self.test_dim = TEST_DIM

    def test_unitize_multi(self):
        vectors = np.ones(self.test_dim)
        vectors[0] = [0, 0, 0]
        vectors, valid = trimesh.unitize(vectors, check_valid=True)

        assert not valid[0]
        assert valid[1:].all()

        length = np.sum(vectors[1:] ** 2, axis=1) ** .5
        assert np.allclose(length, 1.0)

    def test_align(self):
        log.info('Testing vector alignment')
        target = np.array([0, 0, 1])
        for i in range(100):
            vector = trimesh.unitize(np.random.random(3) - .5)
            T = trimesh.geometry.align_vectors(vector, target)
            result = np.dot(T, np.append(vector, 1))[0:3]
            aligned = np.abs(result - target).sum() < TOL_ZERO
            self.assertTrue(aligned)


class UtilTests(unittest.TestCase):

    def test_bounds_tree(self):
        for attempt in range(3):
            for dimension in [2, 3]:
                t = g.np.random.random((1000, 3, dimension))
                bounds = g.np.column_stack((t.min(axis=1), t.max(axis=1)))
                tree = g.trimesh.util.bounds_tree(bounds)
                self.assertTrue(0 in tree.intersection(bounds[0]))

    def test_stack(self):
        # shortcut to the function
        f = g.trimesh.util.stack_3D
        # start with some random points
        p = g.np.random.random((100, 2))
        stack = f(p)
        # shape should be 3D
        assert stack.shape == (100, 3)
        # points should be equal
        assert g.np.allclose(p, stack[:, :2])

        # check an empty array
        assert f([]).shape == (0,)

        try:
            # try with 4D points
            f(g.np.ones((100, 4)))
            assert False
        except ValueError:
            # this is what should happen
            pass

    def test_has_module(self):

        assert g.trimesh.util.has_module('collections')
        assert not g.trimesh.util.has_module('foobarrionananan')

    def test_strips(self):
        """
        Test our conversion of triangle strips to face indexes.
        """

        def strips_to_faces(strips):
            """
            A slow but straightforward version of the function to test against
            """
            faces = g.collections.deque()
            for s in strips:
                s = g.np.asanyarray(s, dtype=g.np.int64)
                # each triangle is defined by one new vertex
                tri = g.np.column_stack([g.np.roll(s, -i)
                                         for i in range(3)])[:-2]
                # we need to flip ever other triangle
                idx = (g.np.arange(len(tri)) % 2).astype(bool)
                tri[idx] = g.np.fliplr(tri[idx])
                faces.append(tri)
            # stack into one (m,3) array
            faces = g.np.vstack(faces)
            return faces

        # test 4- triangle strip
        s = [g.np.arange(6)]
        f = g.trimesh.util.triangle_strips_to_faces(s)
        assert (f == g.np.array([[0, 1, 2],
                                 [3, 2, 1],
                                 [2, 3, 4],
                                 [5, 4, 3]])).all()
        assert len(f) + 2 == len(s[0])
        assert (f == strips_to_faces(s)).all()

        # test single triangle
        s = [g.np.arange(3)]
        f = g.trimesh.util.triangle_strips_to_faces(s)
        assert (f == g.np.array([[0, 1, 2]])).all()
        assert len(f) + 2 == len(s[0])
        assert (f == strips_to_faces(s)).all()

        s = [g.np.arange(100)]
        f = g.trimesh.util.triangle_strips_to_faces(s)
        assert len(f) + 2 == len(s[0])
        assert (f == strips_to_faces(s)).all()

    def test_pairwise(self):
        # check to make sure both itertools and numpy
        # methods return the same result
        pa = np.array(list(g.trimesh.util.pairwise(range(5))))
        pb = g.trimesh.util.pairwise(np.arange(5))

        # make sure results are the same from both methods
        assert (pa == pb).all()
        # make sure we have 4 pairs for 5 values
        assert len(pa) == 4
        # make sure all pairs are length 2
        assert all(len(i) == 2 for i in pa)

    def test_concat(self):

        a = g.get_mesh('ballA.off')
        b = g.get_mesh('ballB.off')

        hA = a.__hash__()
        hB = b.__hash__()

        # make sure we're not mutating original mesh
        for i in range(4):
            c = a + b
            assert g.np.isclose(c.volume,
                                a.volume + b.volume)
            assert a.__hash__() == hA
            assert b.__hash__() == hB

        count = 5
        meshes = []
        for i in range(count):
            m = a.copy()
            m.apply_translation([a.scale, 0, 0])
            meshes.append(m)

        # do a multimesh concatenate
        r = g.trimesh.util.concatenate(meshes)
        assert g.np.isclose(r.volume,
                            a.volume * count)
        assert a.__hash__() == hA

    def test_unique_id(self):
        num_ids = 10000

        g.trimesh.util.random.seed(0)
        unique_ids_0 = []
        for i in range(num_ids):
            s = g.trimesh.util.unique_id()
            unique_ids_0.append(s)

        # make sure every id is truly unique
        assert len(unique_ids_0) == len(g.np.unique(unique_ids_0))

        g.trimesh.util.random.seed(0)
        unique_ids_1 = []
        for i in range(num_ids):
            s = g.trimesh.util.unique_id()
            unique_ids_1.append(s)

            # make sure id's can be reproduced
            assert s == unique_ids_0[i]

    def test_unique_name(self):
        from trimesh.util import unique_name

        assert len(unique_name(None, {})) > 0
        assert len(unique_name('', {})) > 0

        count = 10
        names = set()
        for i in range(count):
            names.add(unique_name('hi', names))
        assert len(names) == count

        names = set()
        for i in range(count):
            names.add(unique_name('', names))
        assert len(names) == count


class ContainsTest(unittest.TestCase):

    def test_inside(self):
        sphere = g.trimesh.primitives.Sphere(radius=1.0, subdivisions=4)
        g.log.info('Testing contains function with sphere')
        samples = (np.random.random((1000, 3)) - .5) * 5
        radius = np.linalg.norm(samples, axis=1)

        margin = .05
        truth_in = radius < (1.0 - margin)
        truth_out = radius > (1.0 + margin)

        contains = sphere.contains(samples)

        if not contains[truth_in].all():
            raise ValueError('contains test does not match truth!')

        if contains[truth_out].any():
            raise ValueError('contains test does not match truth!')


class IOWrapTests(unittest.TestCase):

    def test_io_wrap(self):

        util = g.trimesh.util

        # check wrap_as_stream
        test_b = g.np.random.random(1).tobytes()
        test_s = 'this is a test yo'
        res_b = util.wrap_as_stream(test_b).read()
        res_s = util.wrap_as_stream(test_s).read()
        assert res_b == test_b
        assert res_s == test_s

        # check __enter__ and __exit__
        hi = 'hi'.encode('utf-8')
        with util.BytesIO(hi) as f:
            assert f.read() == hi

        # check __enter__ and __exit__
        hi = 'hi'
        with util.StringIO(hi) as f:
            assert f.read() == hi


class CompressTests(unittest.TestCase):

    def test_compress(self):

        source = {'hey': 'sup',
                  'naa': '2002211'}

        # will return bytes
        c = g.trimesh.util.compress(source)

        # wrap bytes as file- like object
        f = g.trimesh.util.wrap_as_stream(c)
        # try to decompress file- like object
        d = g.trimesh.util.decompress(f, file_type='zip')

        # make sure compressed- decompressed items
        # are the same after a cycle
        for key, value in source.items():
            result = d[key].read().decode('utf-8')
            assert result == value


class UniqueTests(unittest.TestCase):

    def test_unique(self):

        options = [np.array([0, 1, 2, 3, 1, 3, 10, 20]),
                   np.arange(100),
                   np.array([], dtype=np.int64),
                   (np.random.random(1000) * 10).astype(int)]

        for values in options:
            if len(values) > 0:
                minlength = values.max()
            else:
                minlength = 10

            # try our unique bincount function
            unique, inverse, counts = g.trimesh.grouping.unique_bincount(
                values,
                minlength=minlength,
                return_inverse=True,
                return_counts=True)
            # make sure inverse is correct
            assert (unique[inverse] == values).all()

            # make sure that the number of counts matches
            # the number of unique values
            assert (len(unique) == len(counts))

            # get the truth
            truth_unique, truth_inverse, truth_counts = np.unique(values,
                                                                  return_inverse=True,
                                                                  return_counts=True)
            # make sure truth is doing what we think
            assert (truth_unique[truth_inverse] == values).all()

            # make sure we have same number of values
            assert len(truth_unique) == len(unique)

            # make sure all values are identical
            assert set(truth_unique) == set(unique)

            # make sure that the truth counts are identical to our counts
            assert np.all(truth_counts == counts)


class CommentTests(unittest.TestCase):

    def test_comment(self):
        # test our comment stripping logic
        f = g.trimesh.util.comment_strip

        text = 'hey whats up'
        assert f(text) == text

        text = '#hey whats up'
        assert f(text) == ''

        text = '   # hey whats up '
        assert f(text) == ''

        text = '# naahah\nhey whats up'
        assert f(text) == 'hey whats up'

        text = '#naahah\nhey whats up\nhi'
        assert f(text) == 'hey whats up\nhi'

        text = '#naahah\nhey whats up\n hi'
        assert f(text) == 'hey whats up\n hi'

        text = '#naahah\nhey whats up\n hi#'
        assert f(text) == 'hey whats up\n hi'

        text = 'hey whats up# see here\n hi#'
        assert f(text) == 'hey whats up\n hi'


class ArrayToString(unittest.TestCase):
    def test_converts_an_unstructured_1d_array(self):
        self.assertEqual(
            g.trimesh.util.array_to_string(np.array([1, 2, 3])),
            '1 2 3'
        )

    def test_converts_an_unstructured_int_array(self):
        self.assertEqual(
            g.trimesh.util.array_to_string(np.array([[1, 2, 3], [4, 5, 6]])),
            '1 2 3\n4 5 6'
        )

    def test_converts_an_unstructured_float_array(self):
        self.assertEqual(
            g.trimesh.util.array_to_string(
                np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float64)
            ),
            '1.00000000 2.00000000 3.00000000\n4.00000000 5.00000000 6.00000000'
        )

    def test_uses_the_specified_column_delimiter(self):
        self.assertEqual(
            g.trimesh.util.array_to_string(
                np.array([[1, 2, 3], [4, 5, 6]]), col_delim='col'),
            '1col2col3\n4col5col6'
        )

    def test_uses_the_specified_row_delimiter(self):
        self.assertEqual(
            g.trimesh.util.array_to_string(
                np.array([[1, 2, 3], [4, 5, 6]]), row_delim='row'),
            '1 2 3row4 5 6'
        )

    def test_uses_the_specified_value_format(self):
        self.assertEqual(
            g.trimesh.util.array_to_string(
                np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float64),
                value_format='{:.1f}'),
            '1.0 2.0 3.0\n4.0 5.0 6.0'
        )

    def test_supports_uints(self):
        self.assertEqual(
            g.trimesh.util.array_to_string(
                np.array([1, 2, 3], dtype=np.uint8)),
            '1 2 3'
        )

    def test_supports_repeat_format(self):
        self.assertEqual(
            g.trimesh.util.array_to_string(
                np.array([[1, 2, 3], [4, 5, 6]]), value_format='{} {}'),
            '1 1 2 2 3 3\n4 4 5 5 6 6'
        )

    def test_raises_if_array_is_structured(self):
        with self.assertRaises(ValueError):
            g.trimesh.util.array_to_string(np.array(
                [(1, 1.1), (2, 2.2)],
                dtype=[('some_int', np.int64), ('some_float', np.float64)]
            ))

    def test_raises_if_array_is_not_flat(self):
        with self.assertRaises(ValueError):
            g.trimesh.util.array_to_string(np.array([[[1, 2, 3], [4, 5, 6]]]))


class StructuredArrayToString(unittest.TestCase):

    def test_converts_a_structured_array_with_1d_elements(self):
        self.assertEqual(
            g.trimesh.util.structured_array_to_string(
                np.array(
                    [(1, 1.1), (2, 2.2)],
                    dtype=[('some_int', np.int64), ('some_float', np.float64)]
                )
            ),
            '1 1.10000000\n2 2.20000000'
        )

    def test_converts_a_structured_array_with_2d_elements(self):
        self.assertEqual(
            g.trimesh.util.structured_array_to_string(
                np.array(
                    [([1, 2], 1.1), ([3, 4], 2.2)],
                    dtype=[('some_int', np.int64, 2), ('some_float', np.float64)]
                )
            ),
            '1 2 1.10000000\n3 4 2.20000000'
        )

    def test_uses_the_specified_column_delimiter(self):
        self.assertEqual(
            g.trimesh.util.structured_array_to_string(
                np.array(
                    [(1, 1.1), (2, 2.2)],
                    dtype=[('some_int', np.int64), ('some_float', np.float64)]
                ),
                col_delim='col'
            ),
            '1col1.10000000\n2col2.20000000'
        )

    def test_uses_the_specified_row_delimiter(self):
        self.assertEqual(
            g.trimesh.util.structured_array_to_string(
                np.array(
                    [(1, 1.1), (2, 2.2)],
                    dtype=[('some_int', np.int64), ('some_float', np.float64)]
                ),
                row_delim='row'
            ),
            '1 1.10000000row2 2.20000000'
        )

    def test_uses_the_specified_value_format(self):
        self.assertEqual(
            g.trimesh.util.structured_array_to_string(
                np.array(
                    [(1, 1.1), (2, 2.2)],
                    dtype=[('some_int', np.int64), ('some_float', np.float64)]
                ),
                value_format='{:.1f}'
            ),
            '1.0 1.1\n2.0 2.2'
        )

    def test_supports_uints(self):
        self.assertEqual(
            g.trimesh.util.structured_array_to_string(
                np.array(
                    [(1, 1.1), (2, 2.2)],
                    dtype=[('some_int', np.uint8), ('some_float', np.float64)]
                )
            ),
            '1 1.10000000\n2 2.20000000'
        )

    def test_raises_if_array_is_unstructured(self):
        with self.assertRaises(ValueError):
            g.trimesh.util.structured_array_to_string(np.ndarray([1, 2, 3]))

    def test_raises_if_value_format_specifies_repeats(self):
        with self.assertRaises(ValueError):
            g.trimesh.util.structured_array_to_string(
                np.array(
                    [(1, 1.1), (2, 2.2)],
                    dtype=[('some_int', np.int64), ('some_float', np.float64)]
                ),
                value_format='{} {}'
            )

    def test_raises_if_array_is_not_flat(self):
        with self.assertRaises(ValueError):
            g.trimesh.util.structured_array_to_string(
                np.array(
                    [[(1, 1.1), (2, 2.2)], [(1, 1.1), (2, 2.2)]],
                    dtype=[('some_int', np.int64), ('some_float', np.float64)]
                )
            )


if __name__ == '__main__':
    trimesh.util.attach_to_log()
    unittest.main()
