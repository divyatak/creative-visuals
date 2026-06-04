"""
Preview all rock models — solid with light background.
"""
import bpy
import os
import glob

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rocks_preview.png")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# import all and arrange
files = sorted(glob.glob(os.path.join(MODEL_DIR, "*.glb")))
x = 0

for f in files:
    bpy.ops.import_scene.gltf(filepath=f)
    obj = bpy.context.selected_objects[0]
    obj.location = (x, 0, 0)
    # simple grey material
    mat = bpy.data.materials.new(name=f"m_{obj.name}")
    mat.diffuse_color = (0.4, 0.5, 0.6, 1)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    x += 3.0

# add label text below each
names = sorted([os.path.splitext(os.path.basename(f))[0] for f in files])

# camera — orthographic for clean lineup view
bpy.ops.object.camera_add(location=(x/2 - 1.5, -8, 3), rotation=(1.4, 0, 0))
cam = bpy.context.active_object
cam.data.type = 'ORTHO'
cam.data.ortho_scale = x + 4
bpy.context.scene.camera = cam

# light
bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
bpy.context.active_object.data.energy = 3

# light background
world = bpy.data.worlds.new("BG")
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.85, 0.85, 0.88, 1)
bpy.context.scene.world = world

# render with EEVEE (fast)
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.render.resolution_x = 1800
bpy.context.scene.render.resolution_y = 500
bpy.context.scene.render.filepath = OUT_PATH
bpy.context.scene.render.image_settings.file_format = 'PNG'

bpy.ops.render.render(write_still=True)
print(f"Saved: {OUT_PATH}")
