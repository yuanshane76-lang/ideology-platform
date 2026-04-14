"""
主题配置系统 - 管理PPT颜色、字体、装饰风格
"""
from typing import Dict, Tuple, Any
from dataclasses import dataclass


@dataclass
class ThemeColors:
    """主题颜色"""
    primary: Tuple[int, int, int]      # 主色
    secondary: Tuple[int, int, int]    # 辅色
    accent: Tuple[int, int, int]       # 强调色
    background: Tuple[int, int, int]   # 背景色
    text: Tuple[int, int, int]         # 文字色
    text_light: Tuple[int, int, int]   # 浅色文字


@dataclass
class ThemeFonts:
    """主题字体"""
    title: str
    body: str


@dataclass
class ThemeDecorations:
    """主题装饰配置"""
    corner_style: str  # traditional/modern/minimal
    has_header_line: bool
    has_footer_decoration: bool


@dataclass
class Theme:
    """完整主题配置"""
    name: str
    colors: ThemeColors
    fonts: ThemeFonts
    decorations: ThemeDecorations

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "colors": {
                "primary": self.colors.primary,
                "secondary": self.colors.secondary,
                "accent": self.colors.accent,
                "background": self.colors.background,
                "text": self.colors.text,
                "text_light": self.colors.text_light
            },
            "fonts": {
                "title": self.fonts.title,
                "body": self.fonts.body
            },
            "decorations": {
                "corner_style": self.decorations.corner_style,
                "has_header_line": self.decorations.has_header_line,
                "has_footer_decoration": self.decorations.has_footer_decoration
            }
        }


class ThemeManager:
    """主题管理器"""

    # 预定义主题 - 基于Anthropic设计指南的专业配色
    THEMES = {
        # 党政主题
        "party_red": Theme(
            name="党政红",
            colors=ThemeColors(
                primary=(153, 0, 17),      # Cherry Bold #990011
                secondary=(252, 246, 245),  # Off-white #FCF6F5
                accent=(47, 60, 126),       # Navy #2F3C7E
                background=(252, 246, 245), # Off-white
                text=(33, 33, 33),          # Dark gray
                text_light=(255, 255, 255)  # White
            ),
            fonts=ThemeFonts(
                title="Microsoft YaHei",
                body="Microsoft YaHei"
            ),
            decorations=ThemeDecorations(
                corner_style="traditional",
                has_header_line=True,
                has_footer_decoration=True
            )
        ),
        # Anthropic专业配色
        "midnight_executive": Theme(
            name="午夜商务",
            colors=ThemeColors(
                primary=(30, 39, 97),       # Navy #1E2761
                secondary=(202, 220, 252),  # Ice blue #CADCFC
                accent=(255, 255, 255),     # White
                background=(202, 220, 252), # Ice blue
                text=(30, 39, 97),          # Navy
                text_light=(255, 255, 255)  # White
            ),
            fonts=ThemeFonts(
                title="Microsoft YaHei",
                body="Microsoft YaHei"
            ),
            decorations=ThemeDecorations(
                corner_style="modern",
                has_header_line=True,
                has_footer_decoration=True
            )
        ),
        "forest_moss": Theme(
            name="森林绿",
            colors=ThemeColors(
                primary=(44, 95, 45),       # Forest #2C5F2D
                secondary=(151, 188, 98),   # Moss #97BC62
                accent=(245, 245, 245),     # Cream
                background=(245, 245, 245), # Cream
                text=(44, 95, 45),          # Forest
                text_light=(255, 255, 255)  # White
            ),
            fonts=ThemeFonts(
                title="Microsoft YaHei",
                body="Microsoft YaHei"
            ),
            decorations=ThemeDecorations(
                corner_style="modern",
                has_header_line=False,
                has_footer_decoration=True
            )
        ),
        "coral_energy": Theme(
            name="珊瑚活力",
            colors=ThemeColors(
                primary=(249, 97, 103),     # Coral #F96167
                secondary=(249, 231, 149),  # Gold #F9E795
                accent=(47, 60, 126),       # Navy #2F3C7E
                background=(255, 250, 240), # Warm white
                text=(47, 60, 126),         # Navy
                text_light=(255, 255, 255)  # White
            ),
            fonts=ThemeFonts(
                title="Microsoft YaHei",
                body="Microsoft YaHei"
            ),
            decorations=ThemeDecorations(
                corner_style="modern",
                has_header_line=True,
                has_footer_decoration=False
            )
        ),
        "ocean_gradient": Theme(
            name="海洋蓝",
            colors=ThemeColors(
                primary=(6, 90, 130),       # Deep blue #065A82
                secondary=(28, 114, 147),   # Teal #1C7293
                accent=(33, 41, 92),        # Midnight #21295C
                background=(240, 248, 255), # Alice blue
                text=(33, 41, 92),          # Midnight
                text_light=(255, 255, 255)  # White
            ),
            fonts=ThemeFonts(
                title="Microsoft YaHei",
                body="Microsoft YaHei"
            ),
            decorations=ThemeDecorations(
                corner_style="modern",
                has_header_line=True,
                has_footer_decoration=True
            )
        ),
        "charcoal_minimal": Theme(
            name="极简灰",
            colors=ThemeColors(
                primary=(54, 69, 79),       # Charcoal #36454F
                secondary=(242, 242, 242),  # Off-white
                accent=(33, 33, 33),        # Black
                background=(242, 242, 242), # Off-white
                text=(54, 69, 79),          # Charcoal
                text_light=(255, 255, 255)  # White
            ),
            fonts=ThemeFonts(
                title="Microsoft YaHei",
                body="Microsoft YaHei"
            ),
            decorations=ThemeDecorations(
                corner_style="minimal",
                has_header_line=False,
                has_footer_decoration=False
            )
        ),
        # 原有主题保留
        "tech_blue": Theme(
            name="科技蓝",
            colors=ThemeColors(
                primary=(37, 99, 235),
                secondary=(6, 182, 212),
                accent=(191, 219, 254),
                background=(15, 23, 42),
                text=(255, 255, 255),
                text_light=(148, 163, 184)
            ),
            fonts=ThemeFonts(
                title="Microsoft YaHei",
                body="Microsoft YaHei"
            ),
            decorations=ThemeDecorations(
                corner_style="modern",
                has_header_line=True,
                has_footer_decoration=False
            )
        ),
        "elegant_green": Theme(
            name="典雅绿",
            colors=ThemeColors(
                primary=(34, 197, 94),
                secondary=(132, 204, 22),
                accent=(187, 247, 208),
                background=(240, 253, 244),
                text=(30, 41, 59),
                text_light=(71, 85, 105)
            ),
            fonts=ThemeFonts(
                title="Microsoft YaHei",
                body="Microsoft YaHei"
            ),
            decorations=ThemeDecorations(
                corner_style="minimal",
                has_header_line=False,
                has_footer_decoration=True
            )
        ),
        "default": Theme(
            name="简约白",
            colors=ThemeColors(
                primary=(99, 102, 241),
                secondary=(168, 85, 247),
                accent=(199, 210, 254),
                background=(248, 250, 252),
                text=(30, 41, 59),
                text_light=(100, 116, 139)
            ),
            fonts=ThemeFonts(
                title="Microsoft YaHei",
                body="Microsoft YaHei"
            ),
            decorations=ThemeDecorations(
                corner_style="minimal",
                has_header_line=False,
                has_footer_decoration=False
            )
        )
    }

    @classmethod
    def get_theme(cls, theme_name: str) -> Theme:
        """获取主题配置"""
        return cls.THEMES.get(theme_name, cls.THEMES["default"])

    @classmethod
    def list_themes(cls) -> Dict[str, str]:
        """列出所有可用主题"""
        return {key: theme.name for key, theme in cls.THEMES.items()}


def get_theme(theme_name: str) -> Theme:
    """获取主题配置"""
    return ThemeManager.get_theme(theme_name)


THEME_REGISTRY = ThemeManager.THEMES
