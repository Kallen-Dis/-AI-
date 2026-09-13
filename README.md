# 智能AI旅游规划助手

用自然语言描述出行需求，系统会生成行程文案、推荐景点/餐厅/酒店，并在地图上标点、画路线。

对话助手叫「小满」。网页打开后可点「使用教程」，或阅读仓库中的 `使用教程.md`。

## 功能

- 对话收集目的地、天数、预算、偏好
- DeepSeek 生成日程说明
- 百度地图检索地点、规划路线、查询天气
- 地图标注与图层开关
- 游记提纲与导出

## 环境要求

- Python 3.10+（推荐使用仓库内 `.venv`）
- DeepSeek API Key
- 百度地图 Key
  - 服务端：地点检索、地理编码、路线规划、天气
  - 浏览器端：网页底图（需配置 Referer 白名单）

## 配置

在项目根目录创建或编辑 `.env`：

```
DEEPSEEK_API_KEY=你的DeepSeek密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
BAIDU_MAP_AK=百度服务端Key
BAIDU_MAP_BROWSER_AK=百度浏览器端Key
```

也可把百度 Key 写在根目录 `KEY.md`（服务端 / 浏览器端两行）。不要把密钥提交到公开仓库。

浏览器端 Key 的 Referer 白名单需包含：

- `http://127.0.0.1:5000/*`
- `http://localhost:5000/*`

## 启动

```bash
cd MCP_map
..\.venv\Scripts\python.exe -c "from app import app; app.run(debug=False, host='127.0.0.1', port=5000)"
```

浏览器打开：http://127.0.0.1:5000

首次使用建议：

1. 顶部选择天数、偏好、预算
2. 在输入框对小满说明目的地，例如：`安庆 3 天，喜欢文化和美食，预算 2000`
3. 信息齐了会自动规划；结果出现在左侧行程和右侧地图

详细步骤见 `使用教程.md`。

## 项目结构

```
├── .env                 # 本地密钥（勿提交）
├── KEY.md               # 可选的密钥备忘
├── 使用教程.md
├── README.md
├── MCP_map/             # Web：Flask + 地图界面
├── Multi-agent/         # 规划编排与各类 Agent
├── orchestrator/        # 命令行规划入口
├── TravelPlanner/       # 评测与相关研究代码
├── TripTailor/          # 相关研究代码
└── Anqing_Data/         # 示例数据
```

## 工作流程

```
用户对话 / 快捷标签
        ↓
意图解析（DeepSeek）
        ↓
采集地点、天气、路线（百度地图）
        ↓
文化、路线、预算等 Agent 协作
        ↓
网页展示行程、地图、游记
```

## 命令行规划（可选）

```bash
cd orchestrator
python main.py
```

按提示输入目的地与天数。会话结果默认写在 `orchestrator/outputs/sessions/`。

## 故障排查

**地图空白**

- 用 Ctrl+F5 强制刷新
- 检查浏览器端 Key 与 Referer 白名单

**规划失败或一直转圈**

- DeepSeek 密钥是否有效、是否有额度
- 本机能否访问 `https://api.deepseek.com`

**搜不到点或路线只有直线**

- 服务端 Key 是否开通地点检索、路线规划
- 查看后端终端里的报错日志

**依赖未安装**

```bash
.\.venv\Scripts\pip.exe install -r MCP_map\requirements.txt
```
