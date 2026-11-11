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

也可以用 `candidates` 替代 `text`，随机发送一条 Markdown 内容。配置文件中提供了未启用的 `markdown-demo` 规则；将其 `enabled` 改为 `true`，重启后发送 `/markdown` 即可测试。

使用 QQ 开放平台已审核的 Markdown 模板时，配置模板 ID 和参数：

```yaml
reply:
  type: markdown
  custom_template_id: "你的模板ID"
  params:
    title: ["协会小助手"]
    content: ["发送 /帮助 查看可用功能。"]
```

`custom_template_id` 必须是带引号的非空字符串；`params` 的键必须与模板中的参数名一致，值必须是非空字符串数组。模板方式不能同时配置 `text` 或 `candidates`。

`settings.fallback` 也支持同样的 `type`、正文和模板字段，保留 `enabled: true` 即可使用 Markdown 兜底回复。现有纯文本配置无需修改。

机器人需要具备相应场景的 Markdown 发送权限；直接内容权限与模板权限以 QQ 开放平台为准，支持的 Markdown 语法也以 QQ 客户端为准。权限不足或模板未审核时，QQ 接口可能拒绝发送。
