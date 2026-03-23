import re
import json
import httpx
import random
from nonebot import on_message, require, get_driver
from nonebot import logger
from nonebot.plugin import PluginMetadata
from nonebot.adapters.milky import Bot
from nonebot.adapters.milky.event import GroupMessageEvent
from nonebot.adapters.milky import MessageSegment, Message

require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_data_file  # noqa: E402
from nonebot_plugin_alconna import on_alconna, Alconna, Args, Subcommand, Match  # noqa: E402
from nonebot_plugin_alconna.uniseg import UniMessage  # noqa: E402

__plugin_meta__ = PluginMetadata(
    name="全自动膜拜机",
    description="当你诵念大佬的尊名时本插件将自动发送群表情",
    usage="在群内诵念大佬们的尊名即可",
    type="application",
    supported_adapters={"~milky"},
    homepage="https://github.com/zhongwen-4/nonebot_plugin_qwqa",
)

alc = Alconna(
    ["."],
    "qwqa",
    Subcommand("add", Args["user_name", str]),
    Subcommand("get_list"),
    Subcommand("remove", Args["user_name", str], alias= ["del", "-r"]),
)
list_operations = on_alconna(alc, use_cmd_start=False)
send_reaction = on_message()
reaction: list[str] = []
driver = get_driver()
path = get_plugin_data_file("tycoon_list.json")


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
                logger.debug(
                    f"检测到ID为非数字类表情，正在重新随机抽取（第{number}次）"
                )
                reaction = random.choice(emoji_id)
                logger.debug(f"抽取结果: {reaction}")
                number += 1
            else:
                break
    return reaction


@driver.on_startup
async def qwqa_plugin_startup_handle():
    if not path.is_file() or path.stat().st_size == 0:
        with open(path, "w") as f:
            json.dump({}, f)


@send_reaction.handle()
async def send_reaction_handle(bot: Bot, event: GroupMessageEvent):
    msg = event.message.extract_plain_text()
    qwqa = re.search(r"^q([\s\S]?)w([\s\S]?)q[a-zA-Z]$", msg, re.IGNORECASE)
    singl = re.search(r"^s(ing|ign)l\*?$", msg, re.IGNORECASE)
    noah = re.search(r"(towanoah|noa|noah)", msg, re.IGNORECASE)

    group = event.data.group.group_id  # type: ignore
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

        await bot.send_group_message_reaction(
            group_id=group, message_seq=seq, reaction=emoji_id
        )
        await send_reaction.finish()


@list_operations.assign("add")
async def add_list(user_name: Match[str], event: GroupMessageEvent):
    data = {}
    name = user_name.result

    with open(path, "r") as f:
        data: dict = json.load(f)

    if "list" not in data:
        data["list"] = [name]
        with open(path, "w") as f:
            json.dump(data, f)

        await list_operations.finish(
            UniMessage.reply(str(event.data.message_seq)).text("添加成功")
        )
    
    elif name not in data["list"]:
        data["list"].append(name)
        with open(path, "w") as f:
            json.dump(data, f)

        await list_operations.finish(
            UniMessage.reply(str(event.data.message_seq)).text("添加成功")
        )
    
    else:
        await list_operations.finish(
            UniMessage.reply(str(event.data.message_seq)).text("添加失败, 已经有这位大佬了")
        )


@list_operations.assign("remove")
async def remove_list(user_name: Match[str], event: GroupMessageEvent):
    data = {}
    name = user_name.result

    with open(path, "r") as f:
        data: dict = json.load(f)
    
    if "list" not in data:
        await list_operations.finish(
            UniMessage.reply(str(event.data.message_seq)).text("删除失败，没有这位大佬的名字")
        )
    
    elif name not in data["list"]:
        await  list_operations.finish(
            UniMessage.reply(str(event.data.message_seq)).text("删除失败，没有这位大佬的名字")
        )
    
    else:
        data["list"].remove(name)
        with open(path, "w") as f:
            json.dump(data, f)

        await list_operations.finish(
            UniMessage.reply(str(event.data.message_seq)).text("删除成功")
        )


@list_operations.assign("get_list")
async def get_list(event: GroupMessageEvent):
    data = {}
    
    with open(path, "r") as f:
        data = json.load(f)
    
    if "list" not in data:
        await list_operations.finish(
            UniMessage.reply(str(event.data.message_seq)).text("没有大佬列表，快使用 < .qwqa add name > 添加吧~")
        )
    
    quantity = len(data["list"])
    msg_list = [f"共有{quantity}位大佬~"]
    for i in data["list"]:
        msg_list.append(f"- {i}")
    
    if quantity <= 10:
        await list_operations.finish(
            "\n".join(msg_list)
        )
    else:
        msg = [MessageSegment.node(
            user_id= 2854196310,
            name= "Q群管家",
            segments= Message(MessageSegment.text("\n".join(msg_list)))
        )]

        await list_operations.finish(Message(MessageSegment.forward(msg)))