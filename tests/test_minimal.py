"""
test_minimal.py
--------------

Test things that should work with a *minimal* trimesh install.


"""
import os

import unittest
import trimesh
import numpy as np

# the path of the current directory
_pwd = os.path.dirname(
    os.path.abspath(os.path.expanduser(__file__)))
# the absolute path for our reference models
_mwd = os.path.abspath(
    os.path.join(_pwd, '..', 'models'))


def get_mesh(file_name, **kwargs):
    return trimesh.load(os.path.join(_mwd, file_name),
                        **kwargs)


class MinimalTest(unittest.TestCase):

    def test_path_exc(self):
        # this should require *no deps*
        from trimesh.path import packing
        (density,
         offset,
         inserted,
         box) = packing.rectangles_single(
            [[1, 1], [2, 2]],
            sheet_size=[2, 4])
        assert inserted.all()
        assert np.allclose(box, [2, 3])
        assert offset.shape == (2, 2)
        assert density > .833

    def test_load(self):
        # kinds of files we should be able to
        # load even with a minimal install
        kinds = 'stl ply obj off gltf glb'.split()

        for file_name in os.listdir(_mwd):
            ext = os.path.splitext(file_name)[-1].lower()[1:]
            if ext not in kinds:
                continue

            print(file_name)
            m = get_mesh(file_name)
            if isinstance(m, trimesh.Trimesh):
                assert len(m.face_adjacency.shape) == 2
                assert len(m.vertices.shape) == 2

                # make sure hash changes
                initial = hash(m)
                m.faces += 0

                assert hash(m) == initial
                m.vertices[:, 0] += 1.0
                assert hash(m) != initial

    def test_load_path(self):
        # should be able to load a path and export it as a GLB
        # try with a Path3D
        path = trimesh.load_path(np.asarray([(0, 0, 0), (1, 0, 0), (1, 1, 0)]))
        assert isinstance(path, trimesh.path.Path3D)
        scene = trimesh.Scene(path)
        assert len(scene.geometry) == 1
        glb = scene.export(file_type='glb')
        assert len(glb) > 0

        # now create a Path2D
        path = trimesh.load_path(np.asarray([(0, 0), (1, 0), (1, 1)]))
        assert isinstance(path, trimesh.path.Path2D)

        # export to an SVG
        svg = path.export(file_type='svg')
        assert len(svg) > 0

        dxf = path.export(file_type='dxf')
        assert len(dxf) > 0

        scene = trimesh.Scene(path)
        assert len(scene.geometry) == 1
        glb = scene.export(file_type='glb')
        assert len(glb) > 0


if __name__ == '__main__':
    trimesh.util.attach_to_log()
    unittest.main()
