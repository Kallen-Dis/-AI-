# 智能AI旅游规划助手

用自然语言描述出行需求，系统会生成行程文案、推荐景点/餐厅/酒店，并在地图上标点、画路线。

对话助手叫「小满」。网页打开后可点「使用教程」，或阅读仓库中的 `使用教程.md`。

仓库里**没有** `.env`、`KEY.md` 和虚拟环境，克隆后必须自己建环境并填写自己的密钥。

## 功能

- 对话收集目的地、天数、预算、偏好
- DeepSeek 生成日程说明
- 百度地图检索地点、规划路线、查询天气
- 地图标注与图层开关
- 游记提纲与导出

## 环境要求

- Python 3.10+
- 自己申请的 [DeepSeek API Key](https://platform.deepseek.com)
- 自己申请的 [百度地图 Key](https://lbsyun.baidu.com/)
  - 服务端：地点检索、地理编码、路线规划、天气
  - 浏览器端：网页底图（必须配置 Referer 白名单）

## 第一次使用

在项目根目录（有 `README.md` 的那一层）执行。

**1. 创建虚拟环境并安装依赖**（请装 `MCP_map/requirements.txt`，不要装 `Multi-agent/requirements.txt`）

Windows:

```bash
python -m venv .venv
.\.venv\Scripts\pip.exe install -r MCP_map\requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r MCP_map/requirements.txt
```

**2. 填写密钥**

复制示例文件后改成自己的 Key：

```bash
copy .env.example .env
```

macOS / Linux 用 `cp .env.example .env`。

`.env` 内容：

```
DEEPSEEK_API_KEY=你的DeepSeek密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
BAIDU_MAP_AK=百度服务端Key
BAIDU_MAP_BROWSER_AK=百度浏览器端Key
```

也可把百度 Key 写在根目录 `KEY.md`（格式见 `KEY.md.example`）。不要把填好的 `.env` / `KEY.md` 提交到公开仓库。

浏览器端 Key 的 Referer 白名单需包含：

- `http://127.0.0.1:5000/*`
- `http://localhost:5000/*`

**3. 启动网页**

Windows:

```bash
cd MCP_map
..\.venv\Scripts\python.exe -c "from app import app; app.run(debug=False, host='127.0.0.1', port=5000)"
```

macOS / Linux:

```bash
cd MCP_map
../.venv/bin/python -c "from app import app; app.run(debug=False, host='127.0.0.1', port=5000)"
```

浏览器打开：http://127.0.0.1:5000

## 长期公网演示（推荐 Render）

别人用链接打开，需要把网站挂到云上。密钥只填在平台的环境变量里，不要写进 Git。

1. 打开 [Render](https://render.com)，用 GitHub 登录，选择这个仓库 `Kallen-Dis/-AI-`。
2. 若提示使用 Blueprint，选仓库根目录的 `render.yaml`；或新建 Web Service，构建设置为：
   - Build：`pip install -r MCP_map/requirements.txt`
   - Start：`gunicorn --chdir MCP_map -b 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180 app:app`
3. 在 Environment 里填写（与本地 `.env` 相同，不要公开）：
   - `DEEPSEEK_API_KEY`
   - `DEEPSEEK_BASE_URL` = `https://api.deepseek.com`
   - `DEEPSEEK_MODEL` = `deepseek-chat`
   - `BAIDU_MAP_AK`
   - `BAIDU_MAP_BROWSER_AK`
4. 部署完成后会得到 `https://xxxx.onrender.com`。把这个地址发给别人即可。
5. 到百度开放平台，给**浏览器端 Key** 的 Referer 增加：`https://你的onrender域名/*`  
   服务端 Key 若开了 IP 白名单，先关掉或加上 Render 出口 IP，否则搜点和路线会失败。

免费套餐闲置约 15 分钟会休眠，第一次打开可能要等 1 分钟。要一直不休眠，在 Render 把套餐升到付费。

也可用 Docker（本仓库已有 `Dockerfile`）部署到任意云主机：

```bash
docker build -t travel-ai .
docker run -p 5000:5000 --env-file .env travel-ai
```

首次使用建议：

1. 顶部选择天数、偏好、预算（选过的项对话里不会再问）
2. 对小满说明目的地，例如：`安庆，喜欢文化和美食`
3. 目的地和天数齐了会自动规划；结果出现在左侧行程和右侧地图（默认只标当天行程点）

详细步骤见 `使用教程.md`。

## 项目结构

```
├── .env.example         # 密钥模板（复制为 .env）
├── KEY.md.example       # 百度 Key 备忘模板
├── 使用教程.md
├── README.md
├── MCP_map/             # Web：Flask + 地图界面
├── Multi-agent/         # 规划编排与各类 Agent
├── orchestrator/        # 旧命令行入口（需高德 Key，网页不依赖）
├── TravelPlanner/       # 评测与相关研究代码
├── TripTailor/          # 相关研究代码
└── Anqing_Data/         # 示例数据
```

日常使用只需配置密钥并启动 `MCP_map`。

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

## 故障排查

**启动报错找不到 flask / dotenv**

还没装依赖，或没用项目里的 `.venv`。回到根目录执行上面的 pip 安装命令。

**地图空白**

- 用 Ctrl+F5 强制刷新
- 检查浏览器端 Key 与 Referer 白名单

**规划失败或一直转圈**

- DeepSeek 密钥是否有效、是否有额度
- 本机能否访问 `https://api.deepseek.com`

**搜不到点或路线只有直线**

- 服务端 Key 是否开通地点检索、地理编码、路线规划、天气
- 查看后端终端里的报错日志

**小满反复问天数 / 预算**

先在顶部勾选标签，再在对话里点刷新后重新说目的地。
