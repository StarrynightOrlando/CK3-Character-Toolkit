from pathlib import Path
import re
from .versioning import TOOL_VERSION,supported_version
RUNTIME_NAME='CK3 Character Runtime'
def shader_mask(text):
 """Preserve offsets while masking strings and C-style comments."""
 return re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',lambda m:''.join('\n' if c=='\n' else ' ' for c in m[0]),text)
def effect_names(text):return re.findall(r'(?m)^\s*Effect\s+(\w+)\s*\{',shader_mask(text))
def without_effects(shader):
 """Keep shader programs and states, but never export stock effect names."""
 spans=[];mask=shader_mask(shader)
 for match in re.finditer(r'(?m)^\s*Effect\s+\w+\s*\{',mask):
  begin=mask.index('{',match.start(),match.end());depth=0
  for end in range(begin,len(mask)):
   char=mask[end]
   if char=='{':depth+=1
   elif char=='}':
    depth-=1
    if depth==0:spans.append((match.start(),end+1));break
  else:raise ValueError('Unclosed shader effect declaration')
 for start,end in reversed(spans):shader=shader[:start]+shader[end:]
 return shader
def build_runtime(game,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 shader=(Path(game)/'gfx/FX/court_scene.shader').read_text(encoding='utf-8-sig')
 start=shader.index('\tMainCode PS_attachment\n');end=shader.index('\tMainCode PS_portrait_hair_backface',start);section=shader[start:end]
 color=section.index('float3 Color = CommonPixelShaderWithTwoNormal');begin=section.rfind('#ifdef VARIATIONS_ENABLED',0,color);finish=section.index('#endif',color)+len('#endif')
 if begin<0:raise ValueError('Unsupported PS_attachment layout; update shader adapter')
 avatar='''float3 MbNormal = TangentSpaceToWorldNormal( Input, NormalSample );
 SLightingProperties MbLight = GetSunLightingProperties( Input.WorldSpacePos, ShadowTexture );
 float MbShade = smoothstep(0.10f,0.55f,saturate(dot(MbNormal,MbLight._ToLightDir)));
 #ifdef MB_AVATAR_FACE
 float3 Color = Diffuse.rgb * (1.1f / PI);
 #else
 float3 Color = Diffuse.rgb * (0.80f + 0.20f * MbShade) * (1.1f / PI);
 #endif
 Color *= 1.0f + saturate(AppliedHover) * 0.08f;'''
 for kind,code in [('avatar',avatar)]:
  text=without_effects(shader[:start]+section[:begin]+code+section[finish:]+shader[end:])
  for suffix,cut,face in ([('matte',False,False),('cutout',True,False),('face',False,True),('face_cutout',True,True)] if kind=='avatar' else [('surface',False,False)]):
   name=f'ck3char_{kind}_{suffix}';defines='"USE_CHARACTER_DATA" "PDX_MESH_BLENDSHAPES" "DOUBLE_SIDED_ENABLED"'+(' "MB_AVATAR_FACE"' if face else '')
   blend='BlendState = "alpha_to_coverage"' if cut else ''
   text+=f'\nEffect {name} {{ VertexShader = "VS_standard" PixelShader = "PS_attachment" {blend} Defines = {{ {defines} }} }}\nEffect {name}_selection {{ VertexShader = "VS_standard" PixelShader = "PS_court_selection" Defines = {{ "PDX_MESH_BLENDSHAPES" }} }}\nEffect {name}Shadow {{ VertexShader = "VertexPdxMeshStandardShadow" PixelShader = "PixelPdxMeshStandardShadow" RasterizerState = "ShadowRasterizerState" Defines = {{ "PDX_MESH_BLENDSHAPES" }} }}\n'
  p=out/f'gfx/FX/ck3char_{kind}.shader';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
 (out/'descriptor.mod').write_text(f'version="{TOOL_VERSION}"\nname="{RUNTIME_NAME}"\ntags={{ "Portraits" }}\nsupported_version="{supported_version(game)}"\n',encoding='utf-8')
