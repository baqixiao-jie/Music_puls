import tomllib
import aiohttp
from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class Music_puls(PluginBase):
    description = "点歌强化版，指令：点歌 歌曲名 "
    author = "电脑小白"
    version = "2.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/Music_puls/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["Music_puls"]

        self.enable = config["enable"]
        self.command = config["command"]
        self.command_format = config["command-format"]
        self.play_command = config.get("play_command", "播放")
        self.search_results = {}
        self.api_url = config["api_url"]

    async def _fetch_song_list(self, song_name: str) -> list:
        """调用API获取歌曲列表."""
        params = {
            "gm": song_name,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, params=params) as resp:
                    text = await resp.text()
                    logger.debug(f"API 响应: {text}")
                    song_list = self._parse_song_list(text)
                    return song_list
        except aiohttp.ClientError as e:
            logger.error(f"API 请求失败: {e}")
            return []

    def _parse_song_list(self, text: str) -> list:
        """解析 TEXT 格式的歌曲列表."""
        song_list = []
        lines = text.splitlines()
        for line in lines:
            parts = line.split(" -- ")
            if len(parts) == 2:
                try:
                    num_title, singer = parts
                    num = num_title.split("、")[0].strip()
                    title = num_title.split("、")[1].strip()
                    song_list.append({"num": num, "title": title, "singer": singer.strip()})
                except Exception as e:
                    logger.warning(f"解析歌曲列表失败，行内容：{line}， 错误信息: {e}")
        return song_list

    async def _fetch_song_data(self, song_name: str, index: int) -> dict:
        """调用API获取歌曲信息，需要指定歌曲序号."""
        params = {
            "gm": song_name,
            "n": index,
            "type": "json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, params=params) as resp:
                    data = await resp.json()
                    logger.debug(f"获取歌曲详情API 响应: {data}")
                    if data["code"] == 200:
                        return data
                    else:
                        logger.warning(f"获取歌曲信息失败，API返回：{data}")
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"API 请求失败: {e}")
            return None
        except Exception as e:
            logger.exception(f"解析歌曲信息失败: {e}")
            return None

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict) -> bool:
        if not self.enable:
            return True

        content = str(message["Content"]).strip()
        command = content.split(" ")

        if command[0] not in self.command:  # 仅保留点歌命令判断
            return True

        # 处理 "点歌" 命令（中间逻辑不变）
        if len(command) == 1:
            await bot.send_at_message(message["FromWxid"], f"-----Music_puls-----\n❌命令格式错误！{self.command_format}",
                                      [message["SenderWxid"]])
            return False

        song_name = content[len(command[0]):].strip()
        song_list = await self._fetch_song_list(song_name)  # 获取歌曲列表

        if not song_list:
            # 强化错误提示，明确阻断后续逻辑
            await bot.send_at_message(
                message["FromWxid"],
                f"-----Music_puls-----\n❌未找到与「{song_name}」相关的歌曲！",  # 补充具体歌曲名提示
                [message["SenderWxid"]]
            )
            return False  # 严格阻断后续逻辑，避免空卡片发送

        # 直接获取第一个歌曲数据（index=1）
        song_data = await self._fetch_song_data(song_list[0]["title"], 1)
        if not song_data:
            await bot.send_at_message(message["FromWxid"], f"-----Music_puls-----\n❌获取歌曲信息失败！",
                                      [message["SenderWxid"]])
            return False  # 已处理错误消息，阻止其他插件

        # 新增：关键数据字段校验（title/singer/music_url为必传字段）
        title = song_data.get("title")
        singer = song_data.get("singer")
        music_url = song_data.get("music_url")
        if not all([title, singer, music_url]):
            logger.warning(f"歌曲详情字段缺失，原始数据：{song_data}")
            await bot.send_at_message(message["FromWxid"], f"-----Music_puls-----\n❌获取的歌曲信息不完整！",
                                      [message["SenderWxid"]])
            return False

        # 优化：处理空值/None情况（空字符串转默认值，None转默认值）
        title = title.strip() or "未知歌曲"
        singer = singer.strip() if singer else "未知歌手"
        url = song_data.get("link", "")
        music_url = music_url.split("?")[0]  # 已通过前面校验，无需再判空
        cover_url = song_data.get("cover", "")
        lyric = song_data.get("lyrics", "")

        # 关键修改：调整为摇一摇搜歌的XML格式（appid和appname）
        xml = f"""<appmsg appid="wx485a97c844086dc9" sdkver="0">
    <title>{title}</title>
    <des>{singer}</des>
    <action>view</action>
    <type>3</type>
    <showtype>0</showtype>
    <content/>
    <url>{url}</url>
    <dataurl>{music_url}</dataurl>
    <lowurl>{url}</lowurl>
    <lowdataurl>{music_url}</lowdataurl>
    <thumburl>{cover_url}</thumburl>
    <songlyric>{lyric}</songlyric>
    <songalbumurl>{cover_url}</songalbumurl>
    <appattach>
        <totallen>0</totallen>
        <attachid/>
        <emoticonmd5/>
        <fileext/>
        <aeskey/>
    </appattach>
    <weappinfo>
        <pagepath/>
        <username/>
        <appid/>
        <appservicetype>0</appservicetype>
    </weappinfo>
</appmsg>
<fromusername>{bot.wxid}</fromusername>
<scene>0</scene>
<appinfo>
    <version>29</version>
    <appname>摇一摇搜歌</appname>
</appinfo>
<commenturl/>"""
        await bot.send_app_message(message["FromWxid"], xml, 3)
        return False  # 成功发送歌曲，阻止其他插件
        return True  # 未匹配任何命令，允许其他插件处理