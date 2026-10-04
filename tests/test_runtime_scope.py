import re
import tempfile
import unittest
from pathlib import Path

from bridge.runtime import build_runtime


class RuntimeScopeTests(unittest.TestCase):
    def test_build_does_not_reexport_vanilla_effects(self):
        # Different pixels for private attachments must not hijack the effects
        # used by vanilla skin, eyes or attachments in another shader file.
        source = '''
PixelShader = {
\tMainCode PS_attachment
\t{
#ifdef VARIATIONS_ENABLED
float3 Color = CommonPixelShaderWithTwoNormal( Input );
#endif
\t}
\tMainCode PS_portrait_hair_backface
\t{ float4 Color = float4(1,1,1,1); }
}
Effect portrait_skin { Defines = { "USE_CHARACTER_DATA" } }
Effect portrait_eye { Defines = { "USE_CHARACTER_DATA" } }
Effect portrait_attachment { PixelShader = "PS_attachment" }
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            game = root / "game"
            fx = game / "gfx/FX/court_scene.shader"
            fx.parent.mkdir(parents=True)
            fx.write_text(source, encoding="utf-8")
            out = root / "runtime"
            build_runtime(game, out)
            result = (out / "gfx/FX/ck3char_avatar.shader").read_text(encoding="utf-8")
            names = re.findall(r"\bEffect\s+(\w+)\s*\{", result)
            self.assertEqual(len(names), 12)
            self.assertEqual(len(names), len(set(names)))
            self.assertTrue(all(name.startswith("ck3char_") for name in names))
            self.assertFalse({"portrait_skin", "portrait_eye", "portrait_attachment"} & set(names))
            self.assertIn("MainCode PS_attachment", result)
            self.assertIn("MainCode PS_portrait_hair_backface", result)


if __name__ == "__main__":
    unittest.main()
