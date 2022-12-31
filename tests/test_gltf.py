try:
    from . import generic as g
except BaseException:
    import generic as g

# Khronos' official file validator
# can be installed with the helper script:
# `trimesh/docker/builds/gltf_validator.bash`
_gltf_validator = g.trimesh.util.which('gltf_validator')


def validate_glb(data, name=None):
    """
    Run the Khronos validator on GLB files using
    subprocess.

    Parameters
    ------------
    data : bytes
      GLB export
    name : str or None
      Hint to log.

    Raises
    ------------
    ValueError
      If Khronos validator reports errors.
    """
    # subprocess options not in old python
    if g.PY_VER < (3, 7):
        return
    if _gltf_validator is None:
        g.log.warning('no gltf_validator!')
        return

    with g.tempfile.NamedTemporaryFile(suffix='.glb') as f:
        f.write(data)
        f.flush()
        # run the khronos gltf-validator
        report = g.subprocess.run(
            [_gltf_validator, f.name, '-o'],
            capture_output=True)
        # -o prints JSON to stdout
        content = report.stdout.decode('utf-8')
        # log the GLTF validator report if
        # there are any warnings or hints
        decode = g.json.loads(content)

        if (decode['issues']['numErrors'] > 0 or
                report.returncode != 0):
            # log the whole error report
            g.log.error(content)
            if name is not None:
                g.log.error('failed on: %s', name)
            raise ValueError(content)

        if any(decode['issues'][i] > 0 for i in
               ['numWarnings', 'numInfos', 'numHints']):
            g.log.debug(content)


class GLTFTest(g.unittest.TestCase):

    def test_duck(self):
        scene = g.get_mesh('Duck.glb', process=False)

        # should have one mesh
        assert len(scene.geometry) == 1

        # get the mesh
        geom = next(iter(scene.geometry.values()))

        # vertex normals should have been loaded
        assert 'vertex_normals' in geom._cache.cache

        # should not be watertight
        assert not geom.is_volume
        # make sure export doesn't crash
        export = scene.export(file_type='glb')
        validate_glb(export)

        # check a roundtrip
        reloaded = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb')
        # make basic assertions
        g.scene_equal(scene, reloaded)

        # if we merge ugly it should now be watertight
        geom.merge_vertices(
            merge_tex=True, merge_norm=True)
        assert geom.is_volume

    def test_strips(self):
        a = g.get_mesh('mode5.gltf')
        assert len(a.geometry) > 0

        b = g.get_mesh('mode5.gltf', merge_primitives=True)
        assert len(b.geometry) > 0

    def test_buffer_dedupe(self):
        scene = g.trimesh.Scene()
        box_1 = g.trimesh.creation.box()
        box_2 = g.trimesh.creation.box()
        box_3 = g.trimesh.creation.box()
        box_3.visual.face_colors = [0, 255, 0, 255]

        tm = g.trimesh.transformations.translation_matrix
        scene.add_geometry(
            box_1, 'box_1',
            transform=tm((1, 1, 1)))
        scene.add_geometry(
            box_2, 'box_2',
            transform=tm((-1, -1, -1)))
        scene.add_geometry(
            box_3, 'box_3',
            transform=tm((-1, 20, -1)))
        a = g.json.loads(scene.export(
            file_type='gltf')['model.gltf'].decode('utf-8'))
        assert len(a['buffers']) <= 3

    def test_tex_export(self):
        # load textured PLY
        mesh = g.get_mesh('fuze.ply')
        assert hasattr(mesh.visual, 'uv')

        # make sure export as GLB doesn't crash on scenes
        export = mesh.scene().export(file_type='glb', unitize_normals=True)
        validate_glb(export)
        # make sure it works on meshes
        export = mesh.export(file_type='glb', unitize_normals=True)
        validate_glb(export)

    def test_cesium(self):
        # A GLTF with a multi- primitive mesh

        s = g.get_mesh('CesiumMilkTruck.glb')
        # should be one Trimesh object per GLTF "primitive"
        assert len(s.geometry) == 4
        # every geometry displayed once, except wheels twice
        assert len(s.graph.nodes_geometry) == 5

        # make sure export doesn't crash
        export = s.export(file_type='glb')
        validate_glb(export)

        reloaded = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb')
        # make basic assertions
        g.scene_equal(s, reloaded)

    def test_alphamode(self):
        # A GLTF with combinations of AlphaMode and AlphaCutoff
        s = g.get_mesh('AlphaBlendModeTest.glb')
        # should be 5 test geometries
        assert len([geom for geom in
                    s.geometry if geom.startswith('Test')]) == 5
        assert s.geometry['TestCutoffDefaultMesh'].visual.material.alphaMode == 'MASK'
        assert s.geometry['TestCutoff25Mesh'].visual.material.alphaMode == 'MASK'
        assert s.geometry['TestCutoff25Mesh'].visual.material.alphaCutoff == 0.25
        assert s.geometry['TestCutoff75Mesh'].visual.material.alphaMode == 'MASK'
        assert s.geometry['TestCutoff75Mesh'].visual.material.alphaCutoff == 0.75
        assert s.geometry['TestBlendMesh'].visual.material.alphaMode == 'BLEND'
        # defaults OPAQUE
        assert s.geometry['TestOpaqueMesh'].visual.material.alphaMode is None

        export = s.export(file_type='glb')
        validate_glb(export)

        # roundtrip it
        rs = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb')

        # make basic assertions
        g.scene_equal(s, rs)

        # make sure export keeps alpha modes
        # should be the same
        assert len([geom for geom in rs.geometry if geom.startswith('Test')]) == 5
        assert rs.geometry['TestCutoffDefaultMesh'].visual.material.alphaMode == 'MASK'
        assert rs.geometry['TestCutoff25Mesh'].visual.material.alphaMode == 'MASK'
        assert rs.geometry['TestCutoff25Mesh'].visual.material.alphaCutoff == 0.25
        assert rs.geometry['TestCutoff75Mesh'].visual.material.alphaMode == 'MASK'
        assert rs.geometry['TestCutoff75Mesh'].visual.material.alphaCutoff == 0.75
        assert rs.geometry['TestBlendMesh'].visual.material.alphaMode == 'BLEND'
        # defaults OPAQUE
        assert rs.geometry['TestOpaqueMesh'].visual.material.alphaMode is None

    def test_units(self):

        # Trimesh will store units as a GLTF extra if they
        # are defined so check that.

        original = g.get_mesh('pins.glb')

        # export it as a a GLB file
        export = original.export(file_type='glb')
        validate_glb(export)

        kwargs = g.trimesh.exchange.gltf.load_glb(
            g.trimesh.util.wrap_as_stream(export))
        # roundtrip it
        reloaded = g.trimesh.exchange.load.load_kwargs(kwargs)
        # make basic assertions
        g.scene_equal(original, reloaded)

        # make assertions on original and reloaded
        for scene in [original, reloaded]:
            # units should be stored as an extra
            assert scene.units == 'mm'

            # make sure we have two unique geometries
            assert len(scene.geometry) == 2
            # that should have seven instances
            assert len(scene.graph.nodes_geometry) == 7

            # all meshes should be well constructed
            assert all(m.is_volume for m in
                       scene.geometry.values())

            # check unit conversions for fun
            extents = scene.extents.copy()
            as_in = scene.convert_units('in')
            # should all be exactly mm -> in conversion factor
            assert g.np.allclose(
                extents / as_in.extents, 25.4, atol=.001)

        m = g.get_mesh('testplate.glb')
        assert m.units == 'meters'

    def test_basic(self):
        # split a multibody mesh into a scene
        scene = g.trimesh.scene.split_scene(
            g.get_mesh('cycloidal.ply'))
        # should be 117 geometries
        assert len(scene.geometry) >= 117

        # a dict with {file name: str}
        export = scene.export(file_type='gltf')
        # load from just resolver
        r = g.trimesh.load(file_obj=None,
                           file_type='gltf',
                           resolver=export)

        # will assert round trip is roughly equal
        g.scene_equal(r, scene)

        # try loading from a ZIP archive
        zipped = g.trimesh.util.compress(export)
        r = g.trimesh.load(
            file_obj=g.trimesh.util.wrap_as_stream(zipped),
            file_type='zip')

        # try loading from a file name
        # will require a file path resolver
        with g.TemporaryDirectory() as d:
            for file_name, data in export.items():
                with open(g.os.path.join(d, file_name), 'wb') as f:
                    f.write(data)
            # load from file path of header GLTF
            rd = g.trimesh.load(
                g.os.path.join(d, 'model.gltf'))
            # will assert round trip is roughly equal
            g.scene_equal(rd, scene)

    def test_merge_buffers(self):
        # split a multibody mesh into a scene
        scene = g.trimesh.scene.split_scene(
            g.get_mesh('cycloidal.ply'))

        # export a gltf with the merge_buffers option set to true
        export = scene.export(file_type='gltf', merge_buffers=True)

        # We should end up with a single .bin and scene.gltf
        assert len(export.keys()) == 2

        # reload the export
        reloaded = g.trimesh.exchange.load.load_kwargs(
            g.trimesh.exchange.gltf.load_gltf(
                file_obj=None,
                resolver=g.trimesh.visual.resolvers.ZipResolver(export)))

        # check to make sure the geometry keys are the same
        assert set(reloaded.geometry.keys()) == set(scene.geometry.keys())

    def test_merge_primitives(self):
        # test to see if the `merge_primitives` logic is working
        a = g.get_mesh('CesiumMilkTruck.glb')
        assert len(a.geometry) == 4

        # should combine the multiple primitives into a single mesh
        b = g.get_mesh(
            'CesiumMilkTruck.glb', merge_primitives=True)
        assert len(b.geometry) == 2

    def test_specular_glossiness(self):
        s = g.get_mesh('pyramid.zip')
        assert len(s.geometry) > 0

    def test_write_dir(self):
        # try loading from a file name
        # will require a file path resolver
        original = g.get_mesh('fuze.obj')
        assert isinstance(original, g.trimesh.Trimesh)
        s = original.scene()
        with g.TemporaryDirectory() as d:
            path = g.os.path.join(d, 'heyy.gltf')
            s.export(file_obj=path)
            r = g.trimesh.load(path)
            assert isinstance(r, g.trimesh.Scene)
            assert len(r.geometry) == 1
            m = next(iter(r.geometry.values()))
            assert g.np.isclose(original.area, m.area)

    def test_merge_primitives_materials(self):
        # test to see if the `merge_primitives` logic is working
        a = g.get_mesh('rgb_cube_with_primitives.gltf',
                       merge_primitives=True)
        assert len(a.geometry['Cube'].visual.material) == 3
        # what the face materials should be
        truth = [0, 0, 0, 0, 1, 1,
                 1, 1, 2, 2, 2, 2]
        assert g.np.allclose(
            a.geometry['Cube'].visual.face_materials,
            truth)
        # make sure copying did the things correctly
        c = a.copy()
        assert g.np.allclose(
            c.geometry['Cube'].visual.face_materials,
            truth)

    def test_merge_primitives_materials_roundtrip(self):
        # test to see if gltf loaded with `merge_primitives`
        # and then exported back
        # to gltf, produces a valid gltf.
        a = g.get_mesh('rgb_cube_with_primitives.gltf',
                       merge_primitives=True)
        result = a.export(file_type='gltf', merge_buffers=True)
        with g.TemporaryDirectory() as d:
            for file_name, data in result.items():
                with open(g.os.path.join(d, file_name), 'wb') as f:
                    f.write(data)

            rd = g.trimesh.load(
                g.os.path.join(d, 'model.gltf'), merge_primitives=True)
            assert isinstance(rd, g.trimesh.Scene)
            # will assert round trip is roughly equal
            # TODO : restore
            # g.scene_equal(rd, a)

    def test_optional_camera(self):
        gltf_cameras_key = 'cameras'

        # if there's no camera in the scene, then it shouldn't be added to the gltf
        box = g.trimesh.creation.box([1, 1, 1])
        scene = g.trimesh.Scene(box)
        export = scene.export(file_type='gltf')
        assert gltf_cameras_key not in g.json.loads(export['model.gltf'].decode('utf8'))

        # `scene.camera` creates a camera if it does not exist.
        # once in the scene, it should be added to the gltf.
        box = g.trimesh.creation.box([1, 1, 1])
        scene = g.trimesh.Scene(box)
        scene.set_camera()
        export = scene.export(file_type='gltf')
        assert gltf_cameras_key in g.json.loads(export['model.gltf'].decode('utf8'))

    def test_gltf_pole(self):
        scene = g.get_mesh('simple_pole.glb')

        # should have multiple primitives
        assert len(scene.geometry) == 11

        export = scene.export(file_type='glb')
        validate_glb(export)
        # check a roundtrip
        reloaded = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb')
        # make basic assertions
        g.scene_equal(scene, reloaded)

    def test_material_hash(self):

        # load mesh twice independently
        a = g.get_mesh('fuze.obj')
        b = g.get_mesh('fuze.obj')
        # move one of the meshes away from the other
        a.apply_translation([a.scale, 0, 0])

        # materials should not be the same object
        assert id(a.visual.material) != id(b.visual.material)
        # despite being loaded separately material hash should match
        assert hash(a.visual.material) == hash(b.visual.material)

        # create a scene with two meshes
        scene = g.trimesh.Scene([a, b])
        # get the exported GLTF header of a scene with both meshes
        header = g.json.loads(scene.export(
            file_type='gltf', unitize_normals=True)['model.gltf'].decode('utf-8'))
        # header should contain exactly one material
        assert len(header['materials']) == 1
        # both meshes should be contained in the export
        assert len(header['meshes']) == 2

        # get a reloaded version
        export = scene.export(file_type='glb', unitize_normals=True)
        validate_glb(export)
        reloaded = g.trimesh.load(
            file_obj=g.trimesh.util.wrap_as_stream(export),
            file_type='glb')

        # meshes should have survived
        assert len(reloaded.geometry) == 2
        # get meshes back
        ar, br = reloaded.geometry.values()

        # should have been loaded as a PBR material
        assert isinstance(ar.visual.material,
                          g.trimesh.visual.material.PBRMaterial)

        # materials should have the same memory location
        assert id(ar.visual.material) == id(br.visual.material)

        # make sure hash is returning something
        ahash = hash(ar.visual.material)
        # should be returning valid material hashes
        assert isinstance(ahash, int)
        assert ahash != 0

    def test_node_name(self):
        # Test to see if node names generally survive
        # an export-import cycle.

        # a scene
        s = g.get_mesh('cycloidal.3DXML')
        # export as GLB then re-load
        export = s.export(file_type='glb')
        validate_glb(export)
        r = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb')
        # make sure we have the same geometries before and after
        assert set(s.geometry.keys()) == set(r.geometry.keys())
        # make sure the node names are the same before and after
        assert (set(s.graph.nodes_geometry) ==
                set(r.graph.nodes_geometry))

    def test_nested_scale(self):
        # nested transforms with scale
        s = g.get_mesh('nested.glb')
        assert len(s.graph.nodes_geometry) == 3
        assert g.np.allclose(
            [[-1.16701, -2.3366, -0.26938],
             [0.26938, 1., 0.26938]],
            s.bounds, atol=1e-4)

    def test_schema(self):
        # get a copy of the GLTF schema and do simple checks
        s = g.trimesh.exchange.gltf.get_schema()

        # make sure it has at least the keys we expect
        assert set(s['properties'].keys()).issuperset(
            {'accessors',
             'animations',
             'asset',
             'buffers',
             'bufferViews',
             'cameras',
             'images',
             'materials',
             'meshes',
             'nodes',
             'samplers',
             'scene',
             'scenes',
             'skins',
             'textures',
             'extensions',
             'extras'})

        # lightly check to see that no references exist
        assert '$ref' not in g.json.dumps(s)

    def test_export_custom_attributes(self):
        # Write and read custom vertex attributes to gltf
        sphere = g.trimesh.primitives.Sphere()
        v_count, _ = sphere.vertices.shape

        sphere.vertex_attributes[
            '_CustomFloat32Scalar'] = g.np.random.rand(
                v_count, 1).astype(g.np.float32)
        sphere.vertex_attributes[
            '_CustomFloat32Vec3'] = g.np.random.rand(
                v_count, 3).astype(g.np.float32)
        sphere.vertex_attributes[
            '_CustomFloat32Mat4'] = g.np.random.rand(
            v_count, 4, 4).astype(g.np.float32)

        # export as GLB bytes
        export = sphere.export(file_type='glb')
        # this should validate just fine
        validate_glb(export)

        # uint32 is slightly off-label and may cause
        # validators to fail but if you're a bad larry who
        # doesn't follow the rules it should be fine
        sphere.vertex_attributes[
            '_CustomUInt32Scalar'] = g.np.random.randint(
                0, 1000, size=(v_count, 1)).astype(g.np.uint32)

        # when you add a uint16/int16 the gltf-validator
        # complains about the 4-byte boundaries even though
        # all their lengths and offsets mod 4 are zero
        # not sure if that's a validator bug or what
        sphere.vertex_attributes[
            '_CustomUInt16Scalar'] = g.np.random.randint(
                0, 1000, size=(v_count, 1)).astype(g.np.uint16)
        sphere.vertex_attributes[
            '_CustomInt16Scalar'] = g.np.random.randint(
            0, 1000, size=(v_count, 1)).astype(g.np.int16)

        # export as GLB then re-load
        export = sphere.export(file_type='glb')

        r = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb')

        for _, val in r.geometry.items():
            assert set(
                val.vertex_attributes.keys()) == set(
                sphere.vertex_attributes.keys())
            for key in val.vertex_attributes:
                is_same = g.np.array_equal(
                    val.vertex_attributes[key],
                    sphere.vertex_attributes[key])
                assert is_same is True

    def test_extras(self):
        # if GLTF extras are defined, make sure they survive a round trip
        s = g.get_mesh('cycloidal.3DXML')

        # some dummy data
        dummy = {'who': 'likes cheese', 'potatoes': 25}

        # export as GLB with extras passed to the exporter then re-load
        s.metadata = dummy
        export = s.export(file_type='glb')
        validate_glb(export)
        r = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb')

        # make sure extras survived a round trip
        assert all(r.metadata[k] == v
                   for k, v in dummy.items())

    def test_extras_nodes(self):

        test_metadata = {
            'test_str': 'test_value',
            'test_int': 1,
            'test_float': 0.123456789,
            'test_bool': True,
            'test_array': [1, 2, 3],
            'test_dict': {'a': 1, 'b': 2}}

        sphere1 = g.trimesh.primitives.Sphere(radius=1.0)
        sphere1.metadata.update(test_metadata)
        sphere2 = g.trimesh.primitives.Sphere(radius=2.0)
        sphere2.metadata.update(test_metadata)

        tf1 = g.trimesh.transformations.translation_matrix([0, 0, -2])
        tf2 = g.trimesh.transformations.translation_matrix([5, 5, 5])

        s = g.trimesh.scene.Scene()
        s.add_geometry(
            sphere1,
            node_name="Sphere1",
            geom_name="Geom Sphere1",
            transform=tf1)
        s.add_geometry(sphere2,
                       node_name="Sphere2",
                       geom_name="Geom Sphere2",
                       parent_node_name="Sphere1",
                       transform=tf2)

        # Test extras appear in the exported model nodes
        files = s.export(None, "gltf")
        gltf_data = files["model.gltf"]
        assert 'test_value' in gltf_data.decode('utf8')

        # Check node extras survive a round trip
        export = s.export(file_type='glb')
        validate_glb(export)
        r = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb')
        files = r.export(None, "gltf")
        gltf_data = files["model.gltf"]
        assert 'test_value' in gltf_data.decode('utf8')
        edge = r.graph.transforms.edge_data[("world", "Sphere1")]
        assert g.np.allclose(edge['matrix'], tf1)

        # all geometry should be the same
        assert set(r.geometry.keys()) == set(s.geometry.keys())
        for mesh in r.geometry.values():
            # metadata should have all survived
            assert all(mesh.metadata[k] == v
                       for k, v in test_metadata.items())

    def test_read_scene_extras(self):
        # loads a glb with scene extras
        scene = g.get_mesh('monkey.glb', process=False)

        # expected data
        check = {'name': 'monkey', 'age': 32, 'height': 0.987}

        meta = scene.metadata
        for key in check:
            # \check key existence and value
            assert key in meta
            assert meta[key] == check[key]

    def test_load_empty_nodes(self):
        # loads a glb with no meshes
        scene = g.get_mesh('empty_nodes.glb', process=False)

        # expected data
        check = {"parent": [[1.0, 0.0, 0.0, 0.0],
                            [0.0, 1.0, 0.0, 0.0],
                            [0.0, 0.0, 1.0, 0.0],
                            [0.0, 0.0, 0.0, 1.0]],
                 "children_1": [[1.0, 0.0, 0.0, -5.0],
                                [0.0, 1.0, 0.0, 5.0],
                                [0.0, 0.0, 1.0, 0.0],
                                [0.0, 0.0, 0.0, 1.0]],
                 "children_2": [[1.0, 0.0, 0.0, 5.0],
                                [0.0, 1.0, 0.0, 5.0],
                                [0.0, 0.0, 1.0, 0.0],
                                [0.0, 0.0, 0.0, 1.0]]}

        # get the scene nodes
        objs = scene.graph.to_flattened()

        # check number
        assert len(objs) == 3

        for key in check:
            assert key in objs
            assert objs[key]["transform"] == check[key]

    def test_same_name(self):
        s = g.get_mesh('TestScene.gltf')
        # hardcode correct bounds to check against
        bounds = s.dump(concatenate=True).bounds

        # icosahedrons have two primitives each
        print(len(s.geometry), len(s.graph.nodes_geometry))
        assert len(s.graph.nodes_geometry) == 9
        assert len(s.geometry) == 7
        assert g.np.allclose(s.bounds, bounds, atol=1e-3)

        # if merged should have combined the icosahedrons
        s = g.get_mesh('TestScene.gltf', merge_primitives=True)
        assert len(s.graph.nodes_geometry) == 7
        assert len(s.geometry) == 6
        assert g.np.allclose(s.bounds, bounds, atol=1e-3)

    def test_vertex_colors(self):
        # get a mesh with face colors
        m = g.get_mesh('machinist.XAML')
        # export as GLB then re-import
        export = m.export(file_type='glb')
        validate_glb(export)
        r = next(iter(
            g.trimesh.load(g.trimesh.util.wrap_as_stream(
                export),
                file_type='glb').geometry.values()))
        # original mesh should have vertex colors
        assert m.visual.kind == 'face'
        assert m.visual.vertex_colors.ptp(axis=0).ptp() > 0
        # vertex colors should have survived import-export
        assert g.np.allclose(m.visual.vertex_colors,
                             r.visual.vertex_colors)

    def test_vertex_attrib(self):
        # test concatenation with texture
        m = g.get_mesh('fuze.obj')

        colors = (g.np.random.random(
            (len(m.vertices), 4)) * 255).astype(g.np.uint8)

        # set the color vertex attribute
        m.visual.vertex_attributes['color'] = colors
        export = m.export(file_type='glb', unitize_normals=True)
        validate_glb(export)
        r = next(iter(
            g.trimesh.load(
                g.trimesh.util.wrap_as_stream(export),
                file_type='glb').geometry.values()))

        # make sure the color vertex attributes survived the roundtrip
        assert g.np.allclose(
            r.visual.vertex_attributes['color'], colors)

    def test_export_postprocess(self):
        scene = g.trimesh.Scene()
        sphere = g.trimesh.primitives.Sphere()
        sphere.visual.material = g.trimesh.visual.material.PBRMaterial(name='unlit_test')
        scene.add_geometry(sphere)

        def add_unlit(gltf_tree):
            for material_dict in gltf_tree['materials']:
                if 'unlit' in material_dict.get('name', '').lower():
                    material_dict["extensions"] = {
                        "KHR_materials_unlit": {}
                    }
            gltf_tree["extensionsUsed"] = ["KHR_materials_unlit"]

        gltf_1 = g.trimesh.exchange.gltf.export_gltf(scene)
        gltf_2 = g.trimesh.exchange.gltf.export_gltf(scene, tree_postprocessor=add_unlit)

        def extract_materials(gltf_files):
            return g.json.loads(gltf_files['model.gltf'].decode('utf8'))['materials']

        assert "extensions" not in extract_materials(gltf_1)[-1]
        assert "extensions" in extract_materials(gltf_2)[-1]

    def test_primitive_geometry_meta(self):
        # Model with primitives
        s = g.get_mesh('CesiumMilkTruck.glb')
        # check to see if names are somewhat sane
        assert set(s.geometry.keys()) == set([
            'Cesium_Milk_Truck',
            'Cesium_Milk_Truck_1',
            'Cesium_Milk_Truck_2',
            'Wheels'])
        # Assert that primitive geometries are marked as such
        assert s.geometry['Cesium_Milk_Truck'].metadata[
            'from_gltf_primitive']
        assert s.geometry['Cesium_Milk_Truck_1'].metadata[
            'from_gltf_primitive']
        assert s.geometry['Cesium_Milk_Truck_2'].metadata[
            'from_gltf_primitive']
        # Assert that geometries that are not primitives
        # are not marked as such
        assert not s.geometry['Wheels'].metadata[
            'from_gltf_primitive']

        # make sure the flags survive being merged
        m = g.get_mesh('CesiumMilkTruck.glb',
                       merge_primitives=True)
        # names should be non-insane
        assert set(m.geometry.keys()) == set([
            'Cesium_Milk_Truck', 'Wheels'])
        assert not s.geometry['Wheels'].metadata[
            'from_gltf_primitive']
        assert s.geometry['Cesium_Milk_Truck'].metadata[
            'from_gltf_primitive']

    def test_points(self):
        # test a simple pointcloud export-import cycle
        points = g.np.arange(30).reshape((-1, 3))
        export = g.trimesh.Scene(
            g.trimesh.PointCloud(points)).export(file_type='glb')
        validate_glb(export)
        reloaded = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb')
        # make sure points survived export and reload
        assert g.np.allclose(next(iter(
            reloaded.geometry.values())).vertices, points)

    def test_bulk(self):
        # Try exporting every loadable model to GLTF and checking
        # the generated header against the schema.

        # strict mode runs a schema header validation
        assert g.trimesh.tol.strict

        # check mesh, path, pointcloud exports
        for root in [g.dir_models, g.os.path.join(g.dir_models, '2D')]:
            for fn in g.os.listdir(root):
                path_in = g.os.path.join(root, fn)
                try:
                    geom = g.trimesh.load(path_in)
                    if isinstance(geom, g.trimesh.path.path.Path):
                        geom = g.trimesh.Scene(geom)
                except BaseException as E:
                    print(E)
                    continue
                # voxels don't have an export to gltf mode
                if isinstance(geom, g.trimesh.voxel.VoxelGrid):
                    try:
                        geom.export(file_type='glb')
                    except ValueError:
                        # should have raised so all good
                        continue
                    raise ValueError(
                        'voxel was allowed to export wrong GLB!')
                if hasattr(geom, 'vertices') and len(geom.vertices) == 0:
                    continue
                if hasattr(geom, 'geometry') and len(geom.geometry) == 0:
                    continue

                g.log.info('Testing: {}'.format(fn))
                # check a roundtrip which will validate on export
                # and crash on reload if we've done anything screwey
                # unitize normals will unitize any normals to comply with
                # the validator although there are probably reasons you'd
                # want to roundtrip non-unit normals for things, stuff, and activities
                export = geom.export(file_type='glb', unitize_normals=True)
                validate_glb(export, name=fn)

                # shouldn't crash on a reload
                reloaded = g.trimesh.load(
                    file_obj=g.trimesh.util.wrap_as_stream(export),
                    file_type='glb')

                if isinstance(geom, g.trimesh.Trimesh):
                    assert g.np.isclose(geom.area, reloaded.area)

                # compute some stuff
                assert isinstance(reloaded.area, float)
                assert isinstance(reloaded.duplicate_nodes, list)

    def test_interleaved(self):
        # do a quick check on a mesh that uses byte stride
        with open(g.get_path('BoxInterleaved.glb'), 'rb') as f:
            k = g.trimesh.exchange.gltf.load_glb(f)
        # get the kwargs for the mesh constructor
        c = k['geometry']['Mesh']
        # should have vertex normals
        assert c['vertex_normals'].shape == c['vertices'].shape
        # interleaved vertex normals should all be unit vectors
        assert g.np.allclose(
            1.0, g.np.linalg.norm(c['vertex_normals'], axis=1))

        # should also load as a box
        m = g.get_mesh('BoxInterleaved.glb').geometry['Mesh']
        assert g.np.isclose(m.volume, 1.0)

    def test_equal_by_default(self):
        # all things being equal we shouldn't be moving things
        # for the usual load-export loop
        s = g.get_mesh('fuze.obj')
        # export as GLB then re-load
        export = s.export(file_type='glb', unitize_normals=True)
        validate_glb(export)
        reloaded = g.trimesh.load(
            g.trimesh.util.wrap_as_stream(export),
            file_type='glb', process=False)
        assert len(reloaded.geometry) == 1
        m = next(iter(reloaded.geometry.values()))
        assert g.np.allclose(m.visual.uv,
                             s.visual.uv)
        assert g.np.allclose(m.vertices,
                             s.vertices)
        assert g.np.allclose(m.faces,
                             s.faces)

        # will run a kdtree check
        g.texture_equal(s, m)


if __name__ == '__main__':
    g.trimesh.util.attach_to_log()
    g.unittest.main()
