"""
Generate distinct low-poly rock models.
Run: blender --background --python make_rocks.py
"""
import bpy
import bmesh
import random
import math
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(OUT_DIR, exist_ok=True)

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def deform_mesh(obj, strength=0.3, seed=42):
    random.seed(seed)
    mesh = obj.data
    for v in mesh.vertices:
        noise = random.gauss(0, strength)
        v.co.x += v.normal.x * noise + random.gauss(0, strength * 0.3)
        v.co.y += v.normal.y * noise + random.gauss(0, strength * 0.3)
        v.co.z += v.normal.z * noise + random.gauss(0, strength * 0.3)

def apply_modifiers(obj):
    bpy.context.view_layer.objects.active = obj
    for mod in obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=mod.name)

def export_glb(obj, name):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT_DIR, f"{name}.glb"),
        use_selection=True, export_format='GLB', export_apply=True,
    )
    print(f"Exported: {name}.glb")

def make_boulder(name, seed):
    """Big angular faceted rock — clearly chunky, rough, heavy"""
    clear_scene()
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.2)
    obj = bpy.context.active_object
    obj.name = name
    # squash and widen — clearly NOT a sphere
    obj.scale = (1.3, 1.0, 0.7)
    bpy.ops.object.transform_apply(scale=True)
    # heavy decimate for angular facets
    mod = obj.modifiers.new('Decimate', 'DECIMATE')
    mod.ratio = 0.35
    apply_modifiers(obj)
    # strong deformation for craggy surface
    deform_mesh(obj, strength=0.25, seed=seed)
    bpy.ops.object.shade_flat()
    export_glb(obj, name)

def make_pillar(name, seed):
    """Tall thin hexagonal column — clearly vertical, like basalt"""
    clear_scene()
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.25, depth=3.0)
    obj = bpy.context.active_object
    obj.name = name
    # taper the top to a rough point
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    for v in bm.verts:
        if v.co.z > 0.3:
            factor = 1.0 - (v.co.z - 0.3) / 2.7 * 0.7
            v.co.x *= factor
            v.co.y *= factor
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    # subtle edge cuts
    mod = obj.modifiers.new('Subsurf', 'SUBSURF')
    mod.levels = 1
    apply_modifiers(obj)
    mod = obj.modifiers.new('Decimate', 'DECIMATE')
    mod.ratio = 0.6
    apply_modifiers(obj)
    deform_mesh(obj, strength=0.05, seed=seed)
    bpy.ops.object.shade_flat()
    export_glb(obj, name)

def make_slab(name, seed):
    """Standing stone / monolith — tall, thin, flat like a tombstone"""
    clear_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = name
    # tall and thin, like a standing stone
    obj.scale = (0.8, 0.15, 1.8)
    bpy.ops.object.transform_apply(scale=True)
    # round the top edge
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    for v in bm.verts:
        if v.co.z > 0.6:
            # round the top corners inward
            dist_from_center = math.sqrt(v.co.x**2)
            if dist_from_center > 0.2:
                v.co.z -= (dist_from_center - 0.2) * 0.5
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    mod = obj.modifiers.new('Subsurf', 'SUBSURF')
    mod.levels = 2
    apply_modifiers(obj)
    mod = obj.modifiers.new('Decimate', 'DECIMATE')
    mod.ratio = 0.25
    apply_modifiers(obj)
    deform_mesh(obj, strength=0.06, seed=seed)
    bpy.ops.object.shade_flat()
    export_glb(obj, name)

def make_crystal(name, seed):
    """Sharp crystal cluster — spiky, geometric, clearly different"""
    clear_scene()
    random.seed(seed)
    # main tall crystal
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.25, radius2=0.02, depth=2.2)
    main = bpy.context.active_object
    main.name = name

    # 4 smaller crystals at various angles
    for i in range(4):
        angle = i * math.pi * 0.5 + random.random() * 0.5
        h = 0.6 + random.random() * 0.8
        r = 0.12 + random.random() * 0.08
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=r, radius2=0.01, depth=h)
        spike = bpy.context.active_object
        spike.location = (math.cos(angle)*0.2, math.sin(angle)*0.2, -0.5+random.random()*0.3)
        spike.rotation_euler = (random.gauss(0, 0.4), random.gauss(0, 0.4), angle)
        main.select_set(True)
        bpy.context.view_layer.objects.active = main
        bpy.ops.object.join()

    deform_mesh(main, strength=0.03, seed=seed)
    bpy.ops.object.shade_flat()
    export_glb(main, name)

def make_pebble(name, seed):
    """Very flat disc/river stone — clearly different from boulder"""
    clear_scene()
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.4)
    obj = bpy.context.active_object
    obj.name = name
    # extremely flat — like a river stone
    obj.scale = (1.0, 0.8, 0.25)
    bpy.ops.object.transform_apply(scale=True)
    # low-poly
    mod = obj.modifiers.new('Decimate', 'DECIMATE')
    mod.ratio = 0.4
    apply_modifiers(obj)
    deform_mesh(obj, strength=0.03, seed=seed)
    bpy.ops.object.shade_flat()
    export_glb(obj, name)

def make_orb(name, seed):
    """Smooth-ish sphere — round, almost planetary"""
    clear_scene()
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.8)
    obj = bpy.context.active_object
    obj.name = name
    # keep it round, just subtle surface noise
    deform_mesh(obj, strength=0.06, seed=seed)
    # light decimate to keep low-poly but still round
    mod = obj.modifiers.new('Decimate', 'DECIMATE')
    mod.ratio = 0.6
    apply_modifiers(obj)
    bpy.ops.object.shade_flat()
    export_glb(obj, name)

def make_cube_rock(name, seed):
    """Blocky cubic rock — like a fractured concrete block"""
    clear_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.2)
    obj = bpy.context.active_object
    obj.name = name
    # slightly non-uniform scale so it's not a perfect cube
    obj.scale = (1.0, 0.85, 0.9)
    bpy.ops.object.transform_apply(scale=True)
    # subdivide then decimate for chunky facets
    mod = obj.modifiers.new('Subsurf', 'SUBSURF')
    mod.levels = 2
    apply_modifiers(obj)
    mod = obj.modifiers.new('Decimate', 'DECIMATE')
    mod.ratio = 0.2
    apply_modifiers(obj)
    deform_mesh(obj, strength=0.1, seed=seed)
    bpy.ops.object.shade_flat()
    export_glb(obj, name)

# Generate
print("=== Generating rocks ===")

make_boulder("boulder_1", seed=1)
make_boulder("boulder_2", seed=5)
make_boulder("boulder_3", seed=9)

make_pillar("pillar_1", seed=10)
make_pillar("pillar_2", seed=14)
make_pillar("pillar_3", seed=18)

make_slab("slab_1", seed=20)
make_slab("slab_2", seed=24)

make_crystal("crystal_1", seed=30)
make_crystal("crystal_2", seed=34)

make_pebble("pebble_1", seed=40)
make_pebble("pebble_2", seed=44)
make_pebble("pebble_3", seed=48)

make_orb("orb_1", seed=50)
make_orb("orb_2", seed=54)

make_cube_rock("cube_1", seed=60)
make_cube_rock("cube_2", seed=64)

print("=== Done ===")
