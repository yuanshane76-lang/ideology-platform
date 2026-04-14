"""
HTML幻灯片主题系统 - 定义多种预设主题风格
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Theme:
    """主题配置"""
    name: str
    display_name: str
    primary_color: str
    secondary_color: str
    accent_color: str
    text_color: str
    text_secondary: str
    background_style: str
    description: str = ""
    
    def get_css_variables(self) -> str:
        """生成CSS变量"""
        return f"""
        :root {{
            --primary-color: {self.primary_color};
            --secondary-color: {self.secondary_color};
            --accent-color: {self.accent_color};
            --text-color: {self.text_color};
            --text-secondary: {self.text_secondary};
            --bg-gradient: {self.background_style};
        }}
        """
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "accent_color": self.accent_color,
            "text_color": self.text_color,
            "text_secondary": self.text_secondary,
            "background_style": self.background_style,
            "description": self.description
        }


class ThemeManager:
    """主题管理器"""
    
    THEMES: Dict[str, Theme] = {
        "party_red": Theme(
            name="party_red",
            display_name="党建红",
            primary_color="#C41E3A",
            secondary_color="#FFD700",
            accent_color="#8B0000",
            text_color="#1A1A1A",
            text_secondary="#666666",
            background_style="linear-gradient(135deg, #FFF5F5 0%, #FFE4E4 50%, #FFD6D6 100%)",
            description="庄重大气的党建风格，红金配色"
        ),
        "tech_blue": Theme(
            name="tech_blue",
            display_name="科技蓝",
            primary_color="#1E90FF",
            secondary_color="#00BFFF",
            accent_color="#4169E1",
            text_color="#1A1A2E",
            text_secondary="#4A4A6A",
            background_style="linear-gradient(135deg, #E6F3FF 0%, #CCE5FF 50%, #B3D9FF 100%)",
            description="现代科技感，蓝白渐变"
        ),
        "minimal_white": Theme(
            name="minimal_white",
            display_name="简约白",
            primary_color="#2D3436",
            secondary_color="#636E72",
            accent_color="#0984E3",
            text_color="#2D3436",
            text_secondary="#636E72",
            background_style="linear-gradient(135deg, #FFFFFF 0%, #F8F9FA 50%, #F1F3F4 100%)",
            description="极简风格，黑白灰配色"
        ),
        "academic_green": Theme(
            name="academic_green",
            display_name="学术绿",
            primary_color="#27AE60",
            secondary_color="#2ECC71",
            accent_color="#1E8449",
            text_color="#1A1A1A",
            text_secondary="#555555",
            background_style="linear-gradient(135deg, #E8F8F5 0%, #D5F5E3 50%, #C8F7C5 100%)",
            description="清新学术风，绿色系"
        ),
        "elegant_purple": Theme(
            name="elegant_purple",
            display_name="典雅紫",
            primary_color="#8E44AD",
            secondary_color="#9B59B6",
            accent_color="#6C3483",
            text_color="#2C3E50",
            text_secondary="#5D6D7E",
            background_style="linear-gradient(135deg, #F5EEF8 0%, #E8DAEF 50%, #D7BDE2 100%)",
            description="优雅典雅，紫色系"
        ),
        "warm_orange": Theme(
            name="warm_orange",
            display_name="活力橙",
            primary_color="#E67E22",
            secondary_color="#F39C12",
            accent_color="#D35400",
            text_color="#2C3E50",
            text_secondary="#5D6D7E",
            background_style="linear-gradient(135deg, #FEF5E7 0%, #FDEBD0 50%, #FAD7A0 100%)",
            description="温暖活力，橙色系"
        )
    }
    
    @classmethod
    def get_theme(cls, name: str) -> Theme:
        """获取主题"""
        return cls.THEMES.get(name, cls.THEMES["party_red"])
    
    @classmethod
    def list_themes(cls) -> List[Dict[str, str]]:
        """列出所有主题"""
        return [
            {
                "name": theme.name,
                "display_name": theme.display_name,
                "description": theme.description,
                "primary_color": theme.primary_color
            }
            for theme in cls.THEMES.values()
        ]
    
    @classmethod
    def register_theme(cls, theme: Theme):
        """注册新主题"""
        cls.THEMES[theme.name] = theme
