from src.embed.presets import EMBED_PRESETS, resolve_embed_model


def test_resolve_preset_mini():
    assert "MiniLM" in resolve_embed_model("mini")


def test_resolve_explicit_model():
    assert resolve_embed_model("custom/model") == "custom/model"


def test_presets_have_dimensions():
    assert EMBED_PRESETS["mini"].dimensions == 384
    assert EMBED_PRESETS["bge-base"].dimensions == 768
