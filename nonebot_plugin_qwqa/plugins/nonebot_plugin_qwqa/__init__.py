import re
import httpx
import random
from nonebot import on_message
from nonebot import logger
from nonebot.plugin import PluginMetadata
from nonebot.adapters.milky import Bot
from nonebot.adapters.milky.event import GroupMessageEvent

__plugin_meta__ = PluginMetadata(
    name= "全自动膜拜机",
    description= "当你诵念大佬的尊名时本插件将自动发送群表情",
    usage= "在群内诵念大佬们的尊名即可",
    type= "application",
    supported_adapters= {"~milky"}
)

send_reaction = on_message()
reaction: list[str] = []

async def get_emoji_id() -> list[str]:
    url = "https://koishi.js.org/QFace/assets/qq_emoji/_index.json"
    emoji_id = []

    async with httpx.AsyncClient() as api:
        result = await api.get(url)
        if result.status_code == 200:
            result = result.json()
            for i in result:
                match i["emojiId"]:
                    case "38" | "297" | "181":
                        continue
                    case _:
                        emoji_id.append(i["emojiId"])

    return emoji_id


def extract_emoji_id(emoji_id: list[str]) -> str:
    probability = random.randint(1, 100)
    if probability <= 95:
        reaction = random.choice(["38", "297", "181"])
    else:
        reaction = random.choice(emoji_id)
        number = 1
        while True:
            if not reaction.isdigit():
                logger.debug(f"检测到ID为非数字类表情，正在重新随机抽取（第{number}次）")
                reaction = random.choice(emoji_id)
                logger.debug(f"抽取结果: {reaction}")
                number += 1
            else:
                break
    return reaction

@send_reaction.handle()
async def send_reaction_handle(bot: Bot, event: GroupMessageEvent):
    msg = event.message.extract_plain_text()
    qwqa = re.search(r"q([\s\S]?)w([\s\S]?)q[a-zA-Z]", msg, re.IGNORECASE)
    singl = re.search(r"s(ing|ign)l\*?", msg, re.IGNORECASE)
    noah = re.search(r"(towanoah|noa|noah)", msg, re.IGNORECASE)

    group = event.data.group.group_id # type: ignore
    seq = event.data.message_seq
    preset: list[str] = ["白圣女", "白圣女喵", "困困喵", "笨笨喵"]

    if qwqa or singl or msg in preset or noah:
        global reaction
        if not reaction:
            logger.debug("缓存中没有检测到emoji列表，正在拉取。。。")
            reaction = await get_emoji_id()
            emoji_id = extract_emoji_id(reaction)
            logger.debug(f"拉取成功, emoji_id: {emoji_id}")
        else:
            emoji_id = extract_emoji_id(reaction)
            logger.debug(f"使用缓存成功，emoji_id: {emoji_id}")

        await bot.send_group_message_reaction(group_id= group, message_seq= seq, reaction= emoji_id)
        await send_reaction.finish()