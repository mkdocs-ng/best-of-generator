from addict import Dict

from best_of.integrations.mkdocs_integration import MkDocsIntegration

CONFIG = Dict(generate_install_hints=True)


def generate(project: dict, config: Dict = CONFIG):
    return MkDocsIntegration.generate_md_details(Dict(project), config)


def test_links_to_mkdocs_ng_docs_by_default():
    _, body = generate({"mkdocs_plugin": "search"})
    assert (
        "(https://mkdocs-ng.github.io/mkdocs/user-guide/configuration/#plugins)" in body
    )


def test_config_url_is_configurable():
    config = Dict(
        generate_install_hints=True,
        mkdocs_config_url="https://example.com/config/",
    )
    _, body = generate({"mkdocs_theme": "cinder"}, config)
    assert "(https://example.com/config/#theme)" in body


def test_several_themes_give_valid_yaml():
    _, body = generate({"mkdocs_theme": ["cerulean", "cosmo", "cyborg"]})
    assert body.count("theme:") == 1
    assert "theme: cerulean\n" in body
    assert "# or: cosmo, cyborg\n" in body


def test_theme_uses_gallery_screenshot():
    prefix, _ = generate({"mkdocs_theme": "cinder"})
    assert "mkdocs-gallery/assets/img/cinder.png" in prefix
    assert "mkdocs-gallery/themes/cinder/" in prefix


def test_custom_screenshot():
    prefix, _ = generate(
        {
            "mkdocs_theme": "sumi",
            "homepage": "https://example.com/sumi/",
            "screenshot": "https://example.com/sumi.png",
        }
    )
    assert '<img src="https://example.com/sumi.png"' in prefix
    assert '<a href="https://example.com/sumi/">' in prefix
    assert "mkdocs-gallery" not in prefix


def test_screenshot_can_be_turned_off():
    prefix, body = generate({"mkdocs_theme": "sumi", "screenshot": False})
    assert prefix == ""
    assert "theme: sumi" in body


def test_no_screenshot_for_plugins():
    prefix, _ = generate({"mkdocs_plugin": "search"})
    assert prefix == ""
