"""配置驱动的 QQ 机器人回复插件。

整体流程：
1. 插件加载时读取并校验 ``config/replies.yaml``（见 ``_load_config``）；
2. 挂载一条全局消息监听器（``reply_matcher``）；
3. 每条消息按 priority 顺序逐条匹配规则，命中即回复并结束；
4. 所有规则未命中时，若 settings.fallback.enabled 则回复兜底文案。
"""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any

import yaml
from nonebot import get_driver, logger, on_message
from nonebot.adapters.qq import MessageEvent, MessageSegment
from nonebot.adapters.qq.models import MessageMarkdown, MessageMarkdownParams

# 回复配置文件路径：plugins/ 的上一级（项目根目录）下的 config/replies.yaml
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "replies.yaml"
# 支持的触发器类型：命令 / 精确匹配 / 包含关键词 / 正则
SUPPORTED_TRIGGER_TYPES = {"command", "exact", "contains", "regex"}


def _reply_error(reply: Any) -> str | None:
    """校验回复结构；Markdown 正文与模板配置互斥。"""
    if not isinstance(reply, dict):
        return "reply 必须是对象"
    reply_type = reply.get("type", "text")
    if reply_type not in ("text", "markdown"):
        return "reply.type 仅支持 text、markdown"
    if reply_type == "markdown" and "custom_template_id" in reply:
        template_id = reply["custom_template_id"]
        if not isinstance(template_id, str) or not template_id.strip():
            return "reply.custom_template_id 必须是非空字符串"
        if "text" in reply or "candidates" in reply:
            return "Markdown 模板不能同时配置 text 或 candidates"
        params = reply.get("params", {})
        if not isinstance(params, dict) or any(
            not isinstance(key, str) or not key.strip()
            or not isinstance(values, list) or not values
            or not all(isinstance(value, str) for value in values)
            for key, values in params.items()
        ):
            return "reply.params 必须是参数名到非空字符串数组的映射"
        return None
    if not (isinstance(reply.get("text"), str) or isinstance(reply.get("candidates"), list)):
        return "reply 必须提供 text 或 candidates"
    return None


def _as_bool(value: Any, default: bool = False) -> bool:
    """把 YAML 中可能是 bool 的值安全地转成 bool。

    仅当 ``value`` 本身就是 bool 时直接采用，否则（None / 字符串 / 数字等）
    返回默认值，避免 ``if value:`` 对非空字符串误判为 True。
    """
    return value if isinstance(value, bool) else default


def _load_config() -> dict[str, Any]:
    """安全读取并校验 YAML；配置错误时返回空配置，避免插件阻塞启动。"""
    # ---- 1. 读文件与解析，任何错误都降级为空配置（只记日志不抛异常）----
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
    except FileNotFoundError:
        logger.warning(f"回复配置不存在：{CONFIG_PATH}")
        return {"settings": {}, "rules": []}
    except yaml.YAMLError as error:
        logger.error(f"回复配置 YAML 解析失败：{error}")
        return {"settings": {}, "rules": []}

    # ---- 2. 顶层结构校验：必须是对象且 version == 1 ----
    if not isinstance(config, dict):
        logger.error("回复配置顶层必须是 YAML 对象")
        return {"settings": {}, "rules": []}
    if config.get("version") != 1:
        logger.error("回复配置 version 必须为 1")
        return {"settings": {}, "rules": []}

    # ---- 3. settings / rules 基本类型校验 ----
    settings = config.get("settings", {})
    rules = config.get("rules", [])
    if not isinstance(settings, dict) or not isinstance(rules, list):
        logger.error("回复配置的 settings 必须是对象，rules 必须是数组")
        return {"settings": {}, "rules": []}

    # ---- 4. 逐条校验规则，非法规则仅告警并跳过，不影响其余规则 ----
    valid_rules: list[dict[str, Any]] = []
    seen_ids: set[str] = set()  # 用于检测重复 id
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            logger.warning(f"忽略第 {index + 1} 条非对象规则")
            continue
        # 取出规则的关键字段
        rule_id = rule.get("id")
        trigger = rule.get("trigger")
        reply = rule.get("reply")
        trigger_type = trigger.get("type") if isinstance(trigger, dict) else None
        # id 必须是非空字符串且不能重复
        if not isinstance(rule_id, str) or not rule_id.strip() or rule_id in seen_ids:
            logger.warning(f"忽略无效或重复的规则 id：{rule_id!r}")
            continue
        # trigger 必须是对象，且 type 在支持列表内
        if not isinstance(trigger, dict) or trigger_type not in SUPPORTED_TRIGGER_TYPES:
            logger.warning(f"忽略规则 {rule_id}：trigger.type 不支持")
            continue
        reply_error = _reply_error(reply)
        if reply_error:
            logger.warning(f"忽略规则 {rule_id}：{reply_error}")
            continue
        # regex 类型必须提供合法 pattern（提前编译验证，避免运行时抛异常）
        if trigger_type == "regex":
            pattern = trigger.get("pattern")
            if not isinstance(pattern, str):
                logger.warning(f"忽略规则 {rule_id}：regex 缺少 pattern")
                continue
            try:
                re.compile(pattern)
            except re.error as error:
                logger.warning(f"忽略规则 {rule_id}：正则无效：{error}")
                continue
        # 其余类型必须提供非空字符串数组 values
        elif not isinstance(trigger.get("values"), list) or not all(
            isinstance(value, str) and value for value in trigger["values"]
        ):
            logger.warning(f"忽略规则 {rule_id}：trigger.values 必须是非空字符串数组")
            continue
        seen_ids.add(rule_id)
        valid_rules.append(rule)

    # ---- 5. 补默认 priority 并按 priority 从小到大排序（小者优先匹配）----
    for rule in valid_rules:
        priority = rule.get("priority", 100)
        if not isinstance(priority, int):
            rule["priority"] = 100
    valid_rules.sort(key=lambda item: item["priority"])
    return {"settings": settings, "rules": valid_rules}


# 插件加载时即读取并缓存配置；修改 YAML 后需重启机器人生效
CONFIG = _load_config()


def _normalize(text: str, settings: dict[str, Any]) -> str:
    """按全局设置对文本做归一化，用于规则匹配前的预处理。

    依次处理：可选去除首尾空白（trim_whitespace）、可选忽略大小写（ignore_case）。
    """
    if _as_bool(settings.get("trim_whitespace"), True):
        text = text.strip()
    if _as_bool(settings.get("ignore_case"), True):
        text = text.casefold()
    return text


def _matches(rule: dict[str, Any], text: str, event: MessageEvent, settings: dict[str, Any]) -> bool:
    """判断规则是否命中当前消息，返回 True/False。

    ``text`` 是已归一化的消息纯文本；``event`` 用于 only_when_mentioned 判断。
    触发方式按 trigger.type 分四种：
    - regex：用 pattern 做搜索匹配（大小写受全局 ignore_case 控制）；
    - command：去掉命令前缀后取第一个词，精确比较；
    - exact：整条消息必须完全等于某个 value；
    - contains：消息中包含任一 value 即命中。
    """
    trigger = rule["trigger"]
    # only_when_mentioned 支持三级覆盖：trigger > rule > settings（逐级取默认值）
    only_when_mentioned = trigger.get(
        "only_when_mentioned",
        rule.get("only_when_mentioned", settings.get("only_when_mentioned", False)),
    )
    # 仅在被 @ 时才允许触发，未 @ 直接不命中
    if _as_bool(only_when_mentioned) and not event.is_tome():
        return False

    trigger_type = trigger["type"]
    # ---- regex：对原始文本做正则搜索 ----
    if trigger_type == "regex":
        flags = re.IGNORECASE if _as_bool(settings.get("ignore_case"), True) else 0
        return re.search(trigger["pattern"], text, flags) is not None

    # 以下三种类型都基于 values 列表比较，先把触发词同样做归一化
    values = [_normalize(value, settings) for value in trigger["values"]]
    # ---- command：按前缀取第一个词比较 ----
    if trigger_type == "command":
        # 读取命令前缀列表（配置非法时回退为 ["/"]）
        prefixes = settings.get("command_prefixes", ["/"])
        prefixes = prefixes if isinstance(prefixes, list) else ["/"]
        command = text
        # 命中第一个匹配的前缀后去掉前缀及紧随的空白，然后 break
        for prefix in prefixes:
            if isinstance(prefix, str) and prefix and command.startswith(prefix):
                command = command[len(prefix) :].lstrip()
                break
        # 取命令名（第一个词）与 values 精确比较；空命令视为不匹配
        return command.split(maxsplit=1)[0] in values if command else False
    # ---- exact：整条消息完全等于某个 value ----
    if trigger_type == "exact":
        return text in values
    # ---- contains：包含任一 value（走到这里只剩 contains）----
    return any(value in text for value in values)


def _render_reply(rule: dict[str, Any]) -> str | MessageSegment | None:
    """根据规则的 reply 内容生成文本或 Markdown 消息段。

    优先使用 candidates（随机挑选一条合法候选）；没有可用候选时
    回退到固定 text；两者都无效则返回 None（表示无内容可回复）。
    """
    reply = rule["reply"]
    if reply.get("type") == "markdown" and "custom_template_id" in reply:
        return MessageSegment.markdown(MessageMarkdown(
            custom_template_id=reply["custom_template_id"],
            params=[
                MessageMarkdownParams(key=key, values=values)
                for key, values in reply.get("params", {}).items()
            ],
        ))
    text = reply.get("text")
    candidates = reply.get("candidates")
    if isinstance(candidates, list):
        # 过滤掉非字符串或空字符串的候选项
        candidates = [item for item in candidates if isinstance(item, str) and item]
        if candidates:
            text = random.choice(candidates)
    if not isinstance(text, str) or not text:
        return None
    return MessageSegment.markdown(text) if reply.get("type") == "markdown" else text


# 全局消息监听器：priority=10 保证较先处理，block=False 不阻断其他插件
reply_matcher = on_message(priority=10, block=False)


@reply_matcher.handle()
async def handle_configured_reply(event: MessageEvent) -> None:
    """消息处理入口：匹配规则并发送回复。

    策略：规则按 priority 从小到大依次尝试，命中第一条即回复并结束
    （对应配置中的 stop_after_match 语义）；全部未命中时尝试兜底回复。
    """
    settings = CONFIG["settings"]
    # 全局开关：settings.enabled 为 False 时整个插件不响应
    if not _as_bool(settings.get("enabled"), True):
        return

    # 提取纯文本并归一化；空消息（纯图片/表情等）直接跳过
    message_text = event.get_message().extract_plain_text()
    normalized_text = _normalize(message_text, settings)
    if not normalized_text:
        return

    # 逐条匹配已按 priority 排序的规则
    for rule in CONFIG["rules"]:
        # 规则级开关
        if not _as_bool(rule.get("enabled"), True):
            continue
        if _matches(rule, normalized_text, event, settings):
            response = _render_reply(rule)
            if response:
                # finish 会发送回复并终止当前事件处理流程
                await reply_matcher.finish(response)
            # 即使命中但无内容可回复，也不再继续匹配后续规则
            return

    # ---- 兜底回复：所有规则未命中且 settings.fallback.enabled 时触发 ----
    fallback = settings.get("fallback", {})
    if isinstance(fallback, dict) and _as_bool(fallback.get("enabled")):
        reply_error = _reply_error(fallback)
        if reply_error:
            logger.warning(f"忽略兜底回复：{reply_error}")
            return
        response = _render_reply({"reply": fallback})
        if response:
            await reply_matcher.finish(response)


@get_driver().on_startup
async def _log_reply_config() -> None:
    """机器人启动完成时打印一次配置加载情况，便于确认插件生效。"""
    logger.info(f"已加载 {len(CONFIG['rules'])} 条回复规则：{CONFIG_PATH}")
