from typing import List, Sequence, Tuple

from addict import Dict

DEFAULT_MKDOCS_CONFIG_URL = "https://mkdocs-ng.org/user-guide/configuration/"
GALLERY_URL = "https://pawamoy.github.io/mkdocs-gallery"


def _get_as_list(mapping: Dict, key: str) -> Sequence[str]:
    names = mapping.get(key, ())
    if isinstance(names, str):
        names = (names,)
    return names


def _strip_prefix(value: str, prefix: str) -> str:
    # str.removeprefix needs Python 3.9; the build image still runs 3.8.
    if prefix and value.startswith(prefix):
        return value[len(prefix) :]
    return value


def _screenshot_md(project: Dict, themes: Sequence[str]) -> str:
    """Return the screenshot shown next to a theme.

    A project can set `screenshot` to an image URL, or to `false` to show none.
    Otherwise themes use their picture from the MkDocs gallery.
    """
    screenshot = project.get("screenshot")
    if screenshot is False:
        return ""
    if screenshot:
        link = project.homepage or project.github_url or screenshot
    elif themes:
        link = f"{GALLERY_URL}/themes/{themes[0]}/"
        screenshot = f"{GALLERY_URL}/assets/img/{themes[0]}.png"
    else:
        return ""
    return (
        f'<a href="{link}">\n'
        f'<img src="{screenshot}" width="400" align="right">\n'
        f"</a>\n\n"
    )


class MkDocsIntegration:
    @staticmethod
    def generate_md_details(project: Dict, configuration: Dict) -> Tuple[str, str]:
        if not configuration.generate_install_hints:
            return "", ""

        themes = _get_as_list(project, "mkdocs_theme")
        plugins = _get_as_list(project, "mkdocs_plugin")
        extensions = _get_as_list(project, "markdown_extension")

        config_keys: List[str] = []
        yml_main: List[str] = []
        yml_extra: List[str] = []
        yml = yml_main
        if themes:
            config_keys.append("theme")
            # One `theme:` line keeps the snippet valid YAML.
            yml.append(f"theme: {themes[0]}")
            if len(themes) > 1:
                yml.append("# or: " + ", ".join(themes[1:]))
            yml = yml_extra
        if plugins:
            config_keys.append("plugins")
            theme_prefix = f"{themes[0]}/" if themes else ""
            yml += ["plugins:"] + [
                f"  - {_strip_prefix(x, theme_prefix)}" for x in plugins
            ]
        if extensions:
            config_keys.append("markdown_extensions")
            yml += ["markdown_extensions:"] + [f"  - {x}" for x in extensions]

        if not config_keys:
            return "", ""
        config_url = configuration.mkdocs_config_url or DEFAULT_MKDOCS_CONFIG_URL
        url = f"{config_url}#{config_keys[0]}"

        prefix = _screenshot_md(project, themes)

        lines = [
            f"Add to [mkdocs.yml]({url}):",
            "```yaml",
            *yml_main,
            "```",
        ]
        if yml_extra:
            lines += [
                "Extras:",
                "```yaml",
                *yml_extra,
                "```",
            ]
        body = "- " + "".join(f"   {line}\n" for line in lines).lstrip()
        return prefix, body
