"""Synthetic import tests; no private model content."""
import bpy,sys
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.mesh.primitive_cube_add(size=1);mesh=bpy.context.object;mesh.name='FixtureBody'
bpy.ops.object.armature_add();rig=bpy.context.object;rig.name='FixtureRig';group=mesh.vertex_groups.new(name=rig.data.bones[0].name);group.add(list(range(len(mesh.data.vertices))),1,'REPLACE');mod=mesh.modifiers.new('Skin','ARMATURE');mod.object=rig;mesh.parent=rig
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fixture.blend'))
bpy.ops.export_scene.fbx(filepath=str(out/'fixture.fbx'),add_leaf_bones=False,bake_anim=False)
bpy.ops.export_scene.gltf(filepath=str(out/'fixture.glb'),export_format='GLB')
bpy.ops.export_scene.gltf(filepath=str(out/'fixture.gltf'),export_format='GLTF_SEPARATE')
bpy.ops.wm.obj_export(filepath=str(out/'fixture.obj'))
# VRM geometric intake uses glTF container decoding. This is a container test,
# not a claim that all real VRM expression or spring-bone extensions are supported.
(out/'fixture.vrm').write_bytes((out/'fixture.glb').read_bytes())
print('FORMAT_FIXTURES_READY')
