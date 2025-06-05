import tomllib
import tomli_w  # 新增导入用于写入配置
import aiohttp
from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class Music_puls(PluginBase):
    description = "点歌插件魔改版，支持指令：点歌 歌曲名、切换卡片、切换列表。"
    author = "电脑小白"
    version = "2.0.3"

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
        self.log_enabled = config.get("log", {}).get("enabled", True)
        self.log_level = config.get("log", {}).get("level", "DEBUG").upper()
        self.fetch_song_list = config.get("features", {}).get("fetch_song_list", True)
        # 新增：读取卡片类型配置（默认使用原卡片）
        self.card_type = config.get("card_type", "原卡片")  # 关键修改1
        logger.level(self.log_level)
        logger.info(f"插件初始化完成 | 启用状态: {self.enable} | 触发命令: {self.command} | 播放命令: {self.play_command} | API地址: {self.api_url} | 卡片类型: {self.card_type}")

    async def _fetch_song_list(self, song_name: str) -> list:
        """调用API获取歌曲列表."""
        # 修复：补充type=text参数，明确要求API返回文本格式数据（与解析逻辑匹配）
        params = {
            "gm": song_name.replace(" ", "+"),
            "type": "text"  # 关键新增：指定返回文本格式，确保_parse_song_list能正确解析
        }
        # 新增：日志开关控制
        if self.log_enabled:
            logger.debug(f"开始获取歌曲列表 | 歌曲名: {song_name} | 请求参数: {params}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, params=params) as resp:
                    text = await resp.text()
                    # 新增：记录响应状态和内容长度
                    logger.debug(f"获取歌曲列表响应 | 状态码: {resp.status} | 内容长度: {len(text)}")
                    logger.debug(f"API 响应: {text}")  # 保留原有日志
                    song_list = self._parse_song_list(text)
                    # 新增：记录解析结果
                    logger.debug(f"歌曲列表解析完成 | 有效歌曲数: {len(song_list)}")
                    return song_list
        except aiohttp.ClientError as e:
            # 修改：补充上下文信息
            logger.error(f"获取歌曲列表失败 | 歌曲名: {song_name} | 错误详情: {str(e)}")
            return []

    def _parse_song_list(self, text: str) -> list:
        """解析 TEXT 格式的歌曲列表."""
        song_list = []
        lines = text.splitlines()
        logger.debug(f"开始解析歌曲列表 | 总行数: {len(lines)}")
        for line in lines:
            # 新增：过滤空行和无效行
            if not line.strip():
                continue
            # 优化：支持多种分隔符（-、--、|），使用正则匹配
            import re
            parts = re.split(r'[\-|]+', line, maxsplit=1)  # 关键修改：使用正则分割多种可能的分隔符
            if len(parts) == 2:
                try:
                    num_title, singer = parts
                    # 优化：处理序号可能包含的特殊符号（如括号）
                    num_title_parts = re.split(r'[、.]', num_title, maxsplit=1)  # 支持"1.标题"或"1、标题"格式
                    if len(num_title_parts) == 2:
                        num, title = num_title_parts
                        song_list.append({
                            "num": num.strip(),
                            "title": title.strip(),
                            "singer": singer.strip()
                        })
                    else:
                        logger.warning(f"序号标题格式异常 | 行内容: {line}")
                except Exception as e:
                    logger.warning(f"行解析失败 | 行内容: {line} | 错误详情: {str(e)}")
        logger.debug(f"歌曲列表解析结束 | 有效行数: {len(song_list)}")
        return song_list

    async def _fetch_song_data(self, song_name: str, index: int) -> dict:
        """调用API获取歌曲信息，需要指定歌曲序号."""
        # 修复：将歌曲名中的空格替换为+，适配API参数要求
        params = {
            "gm": song_name.replace(" ", "+"),  # 关键修改：处理空格
            "n": index,
            "type": "json",
        }
        # 新增：记录请求开始
        logger.debug(f"开始获取歌曲详情 | 歌曲名: {song_name} | 序号: {index} | 请求参数: {params}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, params=params) as resp:
                    data = await resp.json()
                    # 新增：记录响应状态和关键数据
                    logger.debug(f"获取歌曲详情响应 | 状态码: {resp.status} | 响应code: {data.get('code')}")
                    if data["code"] == 200:
                        # 新增：记录成功信息
                        logger.debug(f"歌曲详情获取成功 | 标题: {data.get('title')} | 歌手: {data.get('singer')}")
                        return data
                    else:
                        # 修改：补充上下文信息
                        logger.warning(f"歌曲详情获取失败 | 歌曲名: {song_name} | 序号: {index} | API返回: {data}")
                        return None
        except aiohttp.ClientError as e:
            # 修改：补充上下文信息
            logger.error(f"获取歌曲详情失败 | 歌曲名: {song_name} | 序号: {index} | 网络错误: {str(e)}")
            return None
        except Exception as e:
            # 保留原有异常日志并补充上下文
            logger.exception(f"歌曲详情解析失败 | 歌曲名: {song_name} | 序号: {index} | 错误详情: {str(e)}")
            return None

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict) -> bool:
        # 新增：日志开关控制
        if self.log_enabled:
            logger.info(f"收到用户消息 | 发送者: {message['SenderWxid']} | 内容: {message['Content']}")
        if not self.enable:
            if self.log_enabled:
                logger.debug("插件未启用 | 忽略当前消息")
            return True

        content = str(message["Content"]).strip()
        command = content.split(" ")

        # 读取主配置中的管理员列表和认证密码（关键修改）
        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)
        admins = main_config.get("admins", [])
        # 从[Admin]部分读取密码（使用管理后台密码作为认证密码）
        correct_password = main_config.get("Admin", {}).get("password", "admin123")  # 默认值保持兼容
        sender_wxid = message["SenderWxid"]

        # 新增：mc认证指令处理（用户认证为管理员）
        if command[0] == "mc认证" and len(command) >= 2:
            if self.log_enabled:
                logger.info(f"触发认证指令 | 用户: {sender_wxid}")
            input_password = " ".join(command[1:])
            if input_password == correct_password:  # 使用配置读取的密码
                try:
                    # 读取插件配置
                    with open("plugins/Music_puls/config.toml", "rb") as f:
                        plugin_config = tomllib.load(f)
                    # 添加用户ID到允许列表（去重）
                    allowed_users = plugin_config["Music_puls"].get("admins", {}).get("allowed_users", [])
                    if sender_wxid not in allowed_users:
                        allowed_users.append(sender_wxid)
                        # 确保[Music_puls.admins]存在（兼容旧配置）
                        if "admins" not in plugin_config["Music_puls"]:
                            plugin_config["Music_puls"]["admins"] = {}
                        plugin_config["Music_puls"]["admins"]["allowed_users"] = allowed_users
                        # 写入配置
                        with open("plugins/Music_puls/config.toml", "wb") as f:
                            tomli_w.dump(plugin_config, f)
                        await bot.send_at_message(
                            message["FromWxid"],
                            f"-----Music_puls-----\n✅认证成功！您已获得管理权限",
                            [sender_wxid]
                        )
                        if self.log_enabled:
                            logger.info(f"用户认证成功 | wxid: {sender_wxid}")
                    else:
                        await bot.send_at_message(
                            message["FromWxid"],
                            f"-----Music_puls-----\nℹ️您已认证过，无需重复操作",
                            [sender_wxid]
                        )
                except Exception as e:
                    await bot.send_at_message(
                        message["FromWxid"],
                        f"-----Music_puls-----\n❌认证失败：{str(e)}",
                        [sender_wxid]
                    )
                    if self.log_enabled:
                        logger.error(f"认证异常 | 错误: {str(e)}")
            else:
                await bot.send_at_message(
                    message["FromWxid"],
                    f"-----Music_puls-----\n❌密码错误！认证失败",
                    [sender_wxid]
                )
                if self.log_enabled:
                    logger.warning(f"认证失败 | 用户: {sender_wxid} | 错误密码: {input_password}")
            return False
        # 新增：配置修改指令处理
        if command[0] == "切换卡片":
            if self.log_enabled:
                logger.info(f"触发卡片切换指令 | 用户: {message['SenderWxid']}")
            try:
                # 读取当前配置
                with open("plugins/Music_puls/config.toml", "rb") as f:
                    plugin_config = tomllib.load(f)
                # 切换卡片类型
                current_type = plugin_config["Music_puls"]["card_type"]
                new_type = "原卡片" if current_type == "摇一摇搜歌" else "摇一摇搜歌"
                plugin_config["Music_puls"]["card_type"] = new_type
                # 写入新配置
                with open("plugins/Music_puls/config.toml", "wb") as f:
                    tomli_w.dump(plugin_config, f)
                # 更新实例属性
                self.card_type = new_type
                await bot.send_at_message(
                    message["FromWxid"],
                    f"-----Music_puls-----\n✅卡片类型已切换为：{new_type}",
                    [message["SenderWxid"]]
                )
                if self.log_enabled:
                    logger.info(f"卡片类型切换成功 | 原类型: {current_type} → 新类型: {new_type}")
            except Exception as e:
                await bot.send_at_message(
                    message["FromWxid"],
                    f"-----Music_puls-----\n❌切换失败：{str(e)}",
                    [message["SenderWxid"]]
                )
                if self.log_enabled:
                    logger.error(f"卡片切换异常 | 错误: {str(e)}")
            return False

        if command[0] == "日志开关":
            if self.log_enabled:
                logger.info(f"触发日志开关指令 | 用户: {message['SenderWxid']}")
            try:
                with open("plugins/Music_puls/config.toml", "rb") as f:
                    plugin_config = tomllib.load(f)
                # 切换日志状态
                current_status = plugin_config["Music_puls"]["log"]["enabled"]
                new_status = not current_status
                plugin_config["Music_puls"]["log"]["enabled"] = new_status
                with open("plugins/Music_puls/config.toml", "wb") as f:
                    tomli_w.dump(plugin_config, f)
                # 更新实例属性
                self.log_enabled = new_status
                status_text = "启用" if new_status else "禁用"
                await bot.send_at_message(
                    message["FromWxid"],
                    f"-----Music_puls-----\n✅日志功能已{status_text}",
                    [message["SenderWxid"]]
                )
                if self.log_enabled:  # 切换后如果启用才记录日志
                    logger.info(f"日志状态切换成功 | 原状态: {current_status} → 新状态: {new_status}")
            except Exception as e:
                await bot.send_at_message(
                    message["FromWxid"],
                    f"-----Music_puls-----\n❌日志开关失败：{str(e)}",
                    [message["SenderWxid"]]
                )
                if self.log_enabled:
                    logger.error(f"日志开关异常 | 错误: {str(e)}")
            return False

        if command[0] == "切换列表":
            if self.log_enabled:
                logger.info(f"触发列表显示开关指令 | 用户: {message['SenderWxid']}")
            try:
                with open("plugins/Music_puls/config.toml", "rb") as f:
                    plugin_config = tomllib.load(f)
                # 切换列表显示状态
                current_status = plugin_config["Music_puls"]["features"]["fetch_song_list"]
                new_status = not current_status
                plugin_config["Music_puls"]["features"]["fetch_song_list"] = new_status
                with open("plugins/Music_puls/config.toml", "wb") as f:
                    tomli_w.dump(plugin_config, f)
                # 更新实例属性
                self.fetch_song_list = new_status
                status_text = "显示" if new_status else "隐藏"
                await bot.send_at_message(
                    message["FromWxid"],
                    f"-----Music_puls-----\n✅歌曲列表现在{status_text}",
                    [message["SenderWxid"]]
                )
                if self.log_enabled:
                    logger.info(f"列表显示状态切换成功 | 原状态: {current_status} → 新状态: {new_status}")
            except Exception as e:
                await bot.send_at_message(
                    message["FromWxid"],
                    f"-----Music_puls-----\n❌列表开关失败：{str(e)}",
                    [message["SenderWxid"]]
                )
                if self.log_enabled:
                    logger.error(f"列表开关异常 | 错误: {str(e)}")
            return False

        if command[0] not in self.command and command[0] != self.play_command:
            # 新增：记录不匹配的命令
            logger.debug(f"命令不匹配 | 当前命令: {command[0]} | 有效命令: {self.command + [self.play_command]}")
            return True

        if command[0] in self.command:  # 处理 "点歌" 命令
            if self.log_enabled:
                logger.info(f"触发点歌命令 | 用户: {message['SenderWxid']} | 原始内容: {content}")
            if len(command) == 1:
                if self.log_enabled:
                    logger.warning(f"点歌命令格式错误 | 用户: {message['SenderWxid']} | 内容: {content}")
                await bot.send_at_message(message["FromWxid"], f"-----Music_puls-----\n❌命令格式错误！{self.command_format}",
                                          [message["SenderWxid"]])
                return False

            song_name = content[len(command[0]):].strip()

            # 新增：根据配置决定是否获取歌曲列表
            if self.fetch_song_list:
                # 原有列表获取逻辑
                song_list = await self._fetch_song_list(song_name)
                if not song_list:
                    if self.log_enabled:
                        logger.warning(f"歌曲搜索无结果 | 搜索词: {song_name}")
                    await bot.send_at_message(message["FromWxid"], f"-----Music_puls-----\n❌未找到相关歌曲！",
                                          [message["SenderWxid"]])
                    return False
                # 构建并发送歌曲列表
                response_text = "🎶----- 找到以下歌曲 -----🎶\n"
                for i, song in enumerate(song_list):
                    response_text += f"{i + 1}. 🎵 {song['title']} - {song['singer']} 🎤\n"
                response_text += "_________________________\n"
                response_text += f"🎵输入 “{self.play_command} + 序号” 播放歌曲🎵"
                self.search_results[message["FromWxid"]] = song_list
                await bot.send_at_message(message["FromWxid"], response_text, [message["SenderWxid"]])
                return False
            else:
                # 直接获取首歌曲逻辑
                if self.log_enabled:
                    logger.debug(f"直接获取首歌曲详情 | 歌曲名: {song_name}")
                song_data = await self._fetch_song_data(song_name, 1)
                if song_data:
                    title = song_data["title"]
                    singer = song_data["singer"]
                    url = song_data.get("link", "")
                    music_url = song_data.get("music_url", "").split("?")[0]
                    cover_url = song_data.get("cover", "")  # 确保cover字段有效
                    lyric = song_data.get("lyrics", "")
                    
                    # 根据卡片类型选择模板（优化图片显示）
                    if self.card_type == "摇一摇搜歌":
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
    <thumburl>{cover_url}</thumburl>  <!-- 使用有效图片链接 -->
    <songlyric>{lyric}</songlyric>
    <songalbumurl>{cover_url}</songalbumurl>
    <appattach>  <!-- 补充CDN相关字段（模拟test.py结构） -->
        <totallen>0</totallen>
        <attachid/>
        <emoticonmd5/>
        <fileext>jpg</fileext>  <!-- 明确图片类型 -->
        <aeskey/>
        <cdnthumburl>{cover_url}</cdnthumburl>  <!-- 用cover_url填充CDN地址 -->
        <cdnthumbaeskey/>
        <cdnthumbmd5/>
        <encryver>1</encryver>
        <cdnthumblength>0</cdnthumblength>
        <cdnthumbheight>100</cdnthumbheight>
        <cdnthumbwidth>100</cdnthumbwidth>
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
                    else:
                        xml = f"""<appmsg appid="wx79f2c4418704b4f8" sdkver="0">
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
    <recorditem/>
    <thumburl>{cover_url}</thumburl>  <!-- 使用有效图片链接 -->
    <messageaction/>
    <laninfo/>
    <extinfo/>
    <sourceusername/>
    <sourcedisplayname/>
    <songlyric>{lyric}</songlyric>
    <commenturl/>
    <appattach>  <!-- 补充CDN相关字段 -->
        <totallen>0</totallen>
        <attachid/>
        <emoticonmd5/>
        <fileext>jpg</fileext>
        <aeskey/>
        <cdnthumburl>{cover_url}</cdnthumburl>
        <cdnthumbaeskey/>
        <cdnthumbmd5/>
        <encryver>1</encryver>
        <cdnthumblength>0</cdnthumblength>
        <cdnthumbheight>100</cdnthumbheight>
        <cdnthumbwidth>100</cdnthumbwidth>
    </appattach>
    <webviewshared>
        <publisherId/>
        <publisherReqId>0</publisherReqId>
    </webviewshared>
    <weappinfo>
        <pagepath/>
        <username/>
        <appid/>
        <appservicetype>0</appservicetype>
    </weappinfo>
    <websearch/>
    <songalbumurl>{cover_url}</songalbumurl>
</appmsg>
<fromusername>{bot.wxid}</fromusername>
<scene>0</scene>
<appinfo>
    <version>1</version>
    <appname/>
</appinfo>
<commenturl/>"""
                    await bot.send_app_message(message["FromWxid"], xml, 3)
                    return False
                else:
                    if self.log_enabled:
                        logger.error(f"获取歌曲信息失败 | 歌曲名: {song_name}")
                    await bot.send_at_message(message["FromWxid"], f"-----Music_puls-----\n❌获取歌曲信息失败！",
                                          [message["SenderWxid"]])
                    return False

        elif command[0] == self.play_command:  # 处理 "播放" 命令
            # 新增：记录播放命令触发
            logger.info(f"触发播放命令 | 用户: {message['SenderWxid']} | 原始内容: {content}")
            try:
                index = int(command[1].strip())
                # 新增：记录播放序号
                logger.debug(f"尝试播放歌曲 | 用户: {message['SenderWxid']} | 目标序号: {index}")
                if message["FromWxid"] in self.search_results and 1 <= index <= len(
                        self.search_results[message["FromWxid"]]):
                    selected_song = self.search_results[message["FromWxid"]][index - 1]
                    song_data = await self._fetch_song_data(selected_song["title"], index)
                    if song_data:
                        title = song_data["title"]
                        singer = song_data["singer"]
                        url = song_data.get("link", "")
                        music_url = song_data.get("music_url", "").split("?")[0]
                        cover_url = song_data.get("cover", "")  # 确保cover字段有效
                        lyric = song_data.get("lyrics", "")

                        # 根据卡片类型选择模板（优化图片显示）
                        if self.card_type == "摇一摇搜歌":
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
    <thumburl>{cover_url}</thumburl>  <!-- 使用有效图片链接 -->
    <songlyric>{lyric}</songlyric>
    <songalbumurl>{cover_url}</songalbumurl>
    <appattach>  <!-- 补充CDN相关字段 -->
        <totallen>0</totallen>
        <attachid/>
        <emoticonmd5/>
        <fileext>jpg</fileext>
        <aeskey/>
        <cdnthumburl>{cover_url}</cdnthumburl>
        <cdnthumbaeskey/>
        <cdnthumbmd5/>
        <encryver>1</encryver>
        <cdnthumblength>0</cdnthumblength>
        <cdnthumbheight>100</cdnthumbheight>
        <cdnthumbwidth>100</cdnthumbwidth>
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
                        else:
                            xml = f"""<appmsg appid="wx79f2c4418704b4f8" sdkver="0">
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
    <recorditem/>
    <thumburl>{cover_url}</thumburl>  <!-- 使用有效图片链接 -->
    <messageaction/>
    <laninfo/>
    <extinfo/>
    <sourceusername/>
    <sourcedisplayname/>
    <songlyric>{lyric}</songlyric>
    <commenturl/>
    <appattach>
        <totallen>0</totallen>
        <attachid/>
        <emoticonmd5/>
        <fileext/>
        <aeskey/>
    </appattach>
    <webviewshared>
        <publisherId/>
        <publisherReqId>0</publisherReqId>
    </webviewshared>
    <weappinfo>
        <pagepath/>
        <username/>
        <appid/>
        <appservicetype>0</appservicetype>
    </weappinfo>
    <websearch/>
    <songalbumurl>{cover_url}</songalbumurl>
</appmsg>
<fromusername>{bot.wxid}</fromusername>
<scene>0</scene>
<appinfo>
    <version>1</version>
    <appname/>
</appinfo>
<commenturl/>"""
                        await bot.send_app_message(message["FromWxid"], xml, 3)
                        return False  # 成功发送歌曲，阻止其他插件
                    else:
                        await bot.send_at_message(message["FromWxid"], f"-----Music_puls-----\n❌获取歌曲信息失败！",
                                                  [message["SenderWxid"]])
                        return False  # 已处理错误消息，阻止其他插件
                else:
                    await bot.send_at_message(message["FromWxid"], f"-----Music_puls-----\n❌无效的歌曲序号！",
                                              [message["SenderWxid"]])
                    return False  # 已处理错误消息，阻止其他插件
            except ValueError:
                # 新增：记录序号格式错误
                logger.warning(f"播放序号格式错误 | 用户: {message['SenderWxid']} | 内容: {content}")
                await bot.send_at_message(message["FromWxid"], f"-----Music_puls-----\n❌请输入有效的歌曲序号！",
                                          [message["SenderWxid"]])
                return False  # 已处理错误消息，阻止其他插件

        return True  # 未匹配任何命令，允许其他插件处理
