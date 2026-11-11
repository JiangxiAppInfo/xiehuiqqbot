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
- `only_when_mentioned`：是否必须 @机器人，规则级配置会覆盖全局配置。

配置加载使用安全的 YAML 解析，并在启动时忽略格式错误的单条规则；这样修改一条规则出错时，其他有效规则仍可使用。
