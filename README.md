# Music_puls 微信点歌强化插件

微信机器人的点歌功能强化插件，支持通过指定命令搜索歌曲并发送摇一摇搜歌格式的音乐卡片。
## 功能特点
- **支持指令**: 点歌 <歌曲名>（示例：点歌 晴天）
- **API调用**: 调用外部API获取歌曲信息
- **数据解析**: 解析API返回的数据，提取歌曲名称、歌手、封面等信息
- **错误处理**: 针对各种错误情况（如命令格式错误、API调用失败等）进行详细的错误处理
- **功能描述**: 通过「点歌 歌曲名」指令调用外部API搜索歌曲，并返回结构化音乐卡片（支持摇一摇搜歌格式）

## 使用方法
确保微信机器人已加载本插件
在微信群/私聊中发送指令：点歌 <歌曲名>（示例：点歌 晴天）
插件将自动：
调用API搜索歌曲
解析并校验歌曲信息
生成摇一摇搜歌格式的音乐卡片并发送
错误处理说明
命令格式错误：返回❌命令格式错误！点歌 <歌曲名>
未找到歌曲：返回❌未找到与「歌曲名」相关的歌曲！
歌曲信息获取失败：返回❌获取歌曲信息失败！
字段缺失：返回❌获取的歌曲信息不完整！
注意事项
API接口需返回特定格式数据（当前支持TEXT格式列表和JSON格式详情）
微信机器人需支持发送appmsg类型的XML消息（需与基础框架兼容）
建议定期检查API地址有效性（若API变更需同步修改api_url配置）
