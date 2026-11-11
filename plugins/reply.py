from nonebot import on_command, on_keyword, on_message, on_regex
from nonebot.adapters.qq import Message, MessageEvent
from nonebot.rule import to_me
#
# # ============ 1. 指令回复：群/频道里发 "天气" 或 "/天气" 触发 ============
# weather = on_command("天气", priority=10, block=True)
#
#
# @weather.handle()
# async def handle_weather():
#     await weather.finish("今天天气晴，适合出门～")
#
#
# # ============ 2. 关键词回复：消息里包含关键词即触发 ============
# keywords = on_keyword({"你好", "在吗"}, priority=10, block=False)
#
#
# @keywords.handle()
# async def handle_keywords():
#     await keywords.finish("你好呀，我在的！")
#
#
# # ============ 3. 正则匹配回复 ============
# ask_name = on_regex(r"你(叫什么|是谁)", priority=10, block=True)
#
#
# @ask_name.handle()
# async def handle_ask_name():
#     await ask_name.finish("我是小助手机器人！")
#
#
# # ============ 4. @机器人 时才触发 ============
# at_me = on_command("菜单", rule=to_me(), priority=10, block=True)
#
#
# @at_me.handle()
# async def handle_menu():
#     await at_me.finish("可用指令：\n/天气 - 查天气\n/菜单 - 显示本菜单")
#
#
# # ============ 5. 获取用户消息内容再回复 ============
# echo_back = on_command("复读", priority=10, block=True)
#
#
# @echo_back.handle()
# async def handle_echo(event: MessageEvent):
#     # 去掉指令本身 "/复读"，取出后面的文本
#     text = event.get_message().extract_plain_text().strip()
#     if not text:
#         await echo_back.reject("你想让我复读什么？请发送：/复读 内容")
#     await echo_back.finish(f"你说的是：{text}")

