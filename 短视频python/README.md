# 基于Python的短视频平台热点话题数据抓取与趋势分析系统

## 项目简介

本系统以B站（Bilibili）为数据来源，利用Python爬虫技术自动化采集热门排行榜及视频数据，通过数据清洗存储至MySQL数据库，运用关键词提取和情感分析等方法进行多维度分析，最终通过Flask Web可视化界面展示分析结果。

## 系统架构

系统由四个核心模块组成：

```
数据抓取 → 数据清洗与存储 → 数据分析 → 数据可视化
```

- **数据抓取模块**：基于Requests库调用B站公开API，采集热门排行榜视频信息及用户评论
- **数据清洗与存储模块**：利用Pandas进行数据清洗，存储至MySQL数据库
- **数据分析模块**：热度排名、趋势分析、jieba关键词提取、SnowNLP情感分析
- **数据可视化模块**：基于Flask+ECharts的Web可视化界面

## 项目结构

```
├── app.py                      # Flask Web应用主程序
├── config.py                   # 系统配置文件
├── run_crawl.py                # 数据抓取主程序（一键采集）
├── requirements.txt            # Python依赖包列表
├── README.md                   # 项目说明文档
├── scraper/                    # 数据抓取模块
│   ├── __init__.py
│   └── bilibili_scraper.py     # B站数据爬虫
├── cleaner/                    # 数据清洗模块
│   ├── __init__.py
│   └── data_cleaner.py         # 数据清洗处理
├── database/                   # 数据库模块
│   ├── __init__.py
│   ├── db_init.py              # 数据库初始化（建库建表）
│   └── db_operations.py        # 数据库增删改查操作
├── analyzer/                   # 数据分析模块
│   ├── __init__.py
│   └── data_analyzer.py        # 数据分析（热度/趋势/关键词/情感）
├── templates/                  # Flask HTML模板
│   ├── base.html               # 基础模板
│   ├── index.html              # 首页概览
│   ├── ranking.html            # 热度排行页
│   ├── trend.html              # 趋势分析页
│   ├── keywords.html           # 关键词分析页
│   └── sentiment.html          # 情感分析页
└── doc/                        # 文档资料
```

## 环境要求

- Python 3.8+
- MySQL 5.7+ 或 8.0+
- 稳定的网络连接

## 安装步骤

### 1. 安装Python依赖

```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置MySQL数据库

确保MySQL服务已启动，然后修改 `config.py` 中的数据库配置：

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",       # 修改为你的MySQL密码
    "database": "bilibili_hotspot",
    "charset": "utf8mb4",
}
```

### 3. 初始化数据库

数据库会在首次运行抓取程序时自动创建，也可手动初始化：

```bash
python database/db_init.py
```

## 使用方法

### 第一步：抓取数据

运行数据抓取程序，自动完成数据采集、清洗和存储：

```bash
python run_crawl.py
```

建议多次运行（间隔数小时或每日运行），以积累足够的数据用于趋势分析。

### 第二步：启动Web可视化界面

```bash
python app.py
```

启动后在浏览器访问 `http://localhost:5000` 即可查看分析结果。

## 功能说明

| 功能页面 | 说明 |
|---------|------|
| 首页概览 | 展示数据统计概况、TOP10视频、分区分布饼图 |
| 热度排行 | 按播放量/点赞数等维度排序的柱状图和数据表格 |
| 趋势分析 | 选择视频查看播放量等指标随时间变化的折线图 |
| 关键词分析 | 基于jieba分词的词云图和高频关键词柱状图 |
| 情感分析 | 基于SnowNLP的评论情感分布饼图和详情表格 |

## 技术栈

| 技术 | 用途 |
|------|------|
| Python | 编程语言 |
| Requests | HTTP请求与API数据抓取 |
| Pandas / NumPy | 数据清洗与处理 |
| MySQL + PyMySQL | 数据存储 |
| jieba | 中文分词与关键词提取 |
| SnowNLP | 中文情感分析 |
| Flask | Web应用框架 |
| ECharts | 前端数据可视化图表 |

## 数据库设计

系统包含三张核心数据表：

- **ranking_records**（排行榜记录表）：记录每次抓取的排行榜数据
- **videos**（视频信息表）：存储视频的标题、UP主、播放量等详细信息
- **comments**（评论表）：存储用户评论文本及相关信息

## 合规声明

- 本系统仅用于学术研究，不得用于商业用途
- 数据抓取仅调用B站公开API接口，不获取任何用户隐私信息
- 程序设置了合理的请求频率限制，避免对服务器造成过大负荷
