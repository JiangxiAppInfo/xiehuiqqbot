"""新成员入群欢迎插件。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from nonebot import logger, on_type
from nonebot.adapters.qq import GroupMemberAddEvent, MessageSegment

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "welcome.yaml"


def _load_config() -> dict[str, Any]:
    """加载欢迎配置；配置错误时禁用欢迎功能，不影响机器人启动。"""
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
    except FileNotFoundError:
        logger.warning(f"欢迎配置不存在：{CONFIG_PATH}")
        return {"enabled": False, "message": ""}
    except yaml.YAMLError as error:
        logger.error(f"欢迎配置 YAML 解析失败：{error}")
        return {"enabled": False, "message": ""}

    if not isinstance(config, dict):
        logger.error("欢迎配置顶层必须是 YAML 对象")
        return {"enabled": False, "message": ""}

    enabled = config.get("enabled", True)
    message = config.get("message")
    if not isinstance(enabled, bool) or not isinstance(message, str) or not message.strip():
        logger.error("欢迎配置需要布尔值 enabled 和非空字符串 message")
        return {"enabled": False, "message": ""}
    return {"enabled": enabled, "message": message}


CONFIG = _load_config()
welcome_matcher = on_type(GroupMemberAddEvent, priority=10, block=False)


@welcome_matcher.handle()
async def welcome_new_member(event: GroupMemberAddEvent) -> None:
    """在新成员加入群聊时发送 Markdown 欢迎消息。"""
    if not CONFIG["enabled"]:
        return
    await welcome_matcher.finish(MessageSegment.markdown(CONFIG["message"]))
