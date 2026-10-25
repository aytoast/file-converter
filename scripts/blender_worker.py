"""Factory-startup background Blender worker; never connects to a live GUI scene."""
import argparse
import json
from pathlib import Path
import sys


def load(path):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    suffix = path.suffix.lower()
    if suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    elif suffix in {".gltf", ".glb"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    elif suffix == ".stl":
        bpy.ops.wm.stl_import(filepath=str(path))
    elif suffix == ".ply":
        bpy.ops.wm.ply_import(filepath=str(path))
    else:
        raise ValueError("Unsupported Blender input")


def geometry_summary():
    import bpy
    from mathutils import Vector
    points = [obj.matrix_world @ Vector(vertex) for obj in bpy.context.scene.objects
              if obj.type == "MESH" for vertex in obj.bound_box]
    if not points:
        raise ValueError("No mesh geometry found")
    bounds = [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]
    return {"meshes": sum(obj.type == "MESH" for obj in bpy.context.scene.objects), "bounds": bounds}


def main():
    import bpy
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-loss", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source, output = Path(args.input), Path(args.output)
    load(source)
    before = geometry_summary()
    target = output.suffix.lower()
    complex_scene = any(obj.type == "ARMATURE" or obj.animation_data or obj.modifiers or obj.data.materials
                        for obj in bpy.context.scene.objects if obj.type in {"MESH", "ARMATURE"})
    if target in {".obj", ".stl", ".ply"} and complex_scene and not args.allow_loss:
        raise ValueError("Geometry-only export drops materials/rig/animation; choose --allow-layout-loss")
    if target in {".glb", ".gltf"}:
        bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB" if target == ".glb" else "GLTF_SEPARATE")
    elif target == ".obj":
        bpy.ops.wm.obj_export(filepath=str(output), export_materials=False)
    elif target == ".stl":
        bpy.ops.wm.stl_export(filepath=str(output))
    elif target == ".ply":
        bpy.ops.wm.ply_export(filepath=str(output))
    elif target == ".fbx":
        bpy.ops.export_scene.fbx(filepath=str(output), path_mode="COPY", embed_textures=True)
    elif target == ".blend":
        bpy.ops.wm.save_as_mainfile(filepath=str(output))
    elif target == ".png":
        render(output, before)
        return
    else:
        raise ValueError("Unsupported Blender target")
    load(output)
    after = geometry_summary()
    original = sorted(high - low for low, high in before["bounds"])
    restored = sorted(high - low for low, high in after["bounds"])
    if any(abs(a - b) > max(1e-4, abs(a) * 0.002) for a, b in zip(original, restored)):
        raise ValueError("Model bounds changed unexpectedly")
    print(json.dumps({"before": before, "after": after}))


def render(output, summary):
    import bpy
    from mathutils import Vector
    bounds = summary["bounds"]
    center = Vector([(a + b) / 2 for a, b in bounds])
    distance = max(b - a for a, b in bounds) * 2.6 or 3
    camera_data = bpy.data.cameras.new("ConversionPreview")
    camera = bpy.data.objects.new("ConversionPreview", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = center + Vector((distance, -distance, distance * 0.75))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene = bpy.context.scene
    scene.camera = camera
    # CPU Cycles avoids version-specific EEVEE names and a display/GPU requirement.
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    for offset in [(distance, -distance, distance), (-distance, 0, distance)]:
        data = bpy.data.lights.new("ConversionLight", "AREA")
        data.energy = 1000
        data.shape = "DISK"
        data.size = distance
        light = bpy.data.objects.new("ConversionLight", data)
        scene.collection.objects.link(light)
        light.location = center + Vector(offset)
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
