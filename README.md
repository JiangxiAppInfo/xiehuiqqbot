# xiehuiqqbot

## How to start

1. generate project using `nb create` .
2. install plugins using `nb plugin install` .
3. run your bot using `nb run` .

## Documentation

See [Docs](https://nonebot.dev/)

## 回复配置

机器人回复规则位于 `config/replies.yaml`。修改规则后重启机器人即可生效，QQ 账号密钥仍保存在 `.env.prod`。

每条规则包含以下字段：

- `id`：规则唯一名称。
- `enabled`：是否启用规则。
- `priority`：优先级，数字越小越先匹配。
- `trigger.type`：支持 `command`、`exact`、`contains`、`regex`。
- `trigger.values`：命令、精确文本或关键词列表；`regex` 使用 `trigger.pattern`。
- `reply.text` 或 `reply.candidates`：固定回复或随机回复列表。
- `reply.type`：`text`（默认）或 `markdown`。
- `only_when_mentioned`：是否必须 @机器人，规则级配置会覆盖全局配置。

配置加载使用安全的 YAML 解析，并在启动时忽略格式错误的单条规则；这样修改一条规则出错时，其他有效规则仍可使用。

## Markdown 回复

直接发送 Markdown 正文时，在规则的 `reply` 中配置：

```yaml
reply:
  type: markdown
  text: |
    # 协会小助手
    **欢迎使用！**
    发送 /帮助 查看可用功能。
```
使用 QQ 开放平台已审核的 Markdown 模板时，配置模板 ID 和参数：

```yaml
reply:
  type: markdown
  custom_template_id: "你的模板ID"
  params:
    title: ["协会小助手"]
    content: ["发送 /帮助 查看可用功能。"]
```

## 入群欢迎

`plugins/welcome.py` 会监听 QQ 群新成员加入事件，并发送 Markdown 欢迎消息。可以在 `config/welcome.yaml` 修改文案；设置 `enabled: false` 可关闭。修改后重启机器人生效。机器人需要具备在群内发送消息及 Markdown 的权限。
