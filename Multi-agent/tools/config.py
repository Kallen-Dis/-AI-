"""
配置管理模块
加载 .env 文件中的 API Key 和其他配置项
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# 尝试加载 .env
try:
    from dotenv import load_dotenv
    
    # 计算项目根目录
    config_file = Path(__file__).resolve().parent.parent.parent
    root_env = config_file / ".env"
    
    if root_env.exists() and root_env.stat().st_size > 0:
        load_dotenv(root_env, override=True)
    
except ImportError:
    pass
except Exception:
    pass


@dataclass
class DeepSeekConfig:
    """DeepSeek LLM 配置"""
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.3
    planning_temperature: float = 0.7
    max_tokens: int = 4096

    def __post_init__(self):
        self.api_key = self.api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = self.base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = self.model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def load_baidu_keys(project_root: Optional[Path] = None) -> tuple:
    """从环境变量或 KEY.md 读取百度服务端/浏览器端 Key。"""
    import re
    server = (
        os.getenv("BAIDU_MAP_AK", "")
        or os.getenv("BAIDU_API_KEY", "")
        or os.getenv("AMAP_API_KEY", "")
    )
    browser = os.getenv("BAIDU_MAP_BROWSER_AK", "")
    root = project_root or Path(__file__).resolve().parent.parent.parent
    key_file = root / "KEY.md"
    if key_file.exists():
        text = key_file.read_text(encoding="utf-8")
        m1 = re.search(r"服务端\s*([A-Za-z0-9]+)", text)
        m2 = re.search(r"浏览器端\s*([A-Za-z0-9]+)", text)
        if m1 and not server:
            server = m1.group(1)
        if m2 and not browser:
            browser = m2.group(1)
    return server, browser


@dataclass
class BaiduConfig:
    """百度地图 配置"""
    api_key: str = ""
    browser_key: str = ""
    base_url: str = "https://api.map.baidu.com"

    def __post_init__(self):
        server, browser = load_baidu_keys()
        self.api_key = self.api_key or server
        self.browser_key = self.browser_key or browser


# 兼容旧字段名
AmapConfig = BaiduConfig


@dataclass
class AgentConfig:
    """主控Agent总配置"""
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)
    baidu: BaiduConfig = field(default_factory=BaiduConfig)
    amap: BaiduConfig = field(default_factory=BaiduConfig)

    def validate(self) -> list:
        """校验必填Key, 返回缺失项列表"""
        missing = []
        if not self.deepseek.api_key:
            missing.append("DEEPSEEK_API_KEY")
        map_key = self.baidu.api_key or self.amap.api_key
        if not map_key:
            missing.append("BAIDU_MAP_AK")
        return missing


def load_config(**overrides) -> AgentConfig:
    """加载配置, 支持参数覆盖"""
    ds_overrides = {k.replace("deepseek_", ""): v for k, v in overrides.items() if k.startswith("deepseek_")}
    baidu_overrides = {
        k.replace("baidu_", "").replace("amap_", ""): v
        for k, v in overrides.items()
        if k.startswith("baidu_") or k.startswith("amap_")
    }

    baidu_cfg = BaiduConfig(**baidu_overrides)
    config = AgentConfig(
        deepseek=DeepSeekConfig(**ds_overrides),
        baidu=baidu_cfg,
        amap=baidu_cfg,
    )

    missing = config.validate()
    if missing:
        print(f"  [WARN] Missing API Key: {', '.join(missing)}")
        print(f"   请在项目根目录的 .env 文件或环境变量中配置")

    return config
