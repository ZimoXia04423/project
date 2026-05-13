# -*- coding: utf-8 -*-
"""生成紧凑版 database_er_neat.svg（UTF-8）"""
import os
p = os.path.join(os.path.dirname(__file__), "database_er_neat.svg")
s = r'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420">
  <defs>
    <style type="text/css"><![CDATA[
      .t { font-family: "Microsoft YaHei","SimHei",sans-serif; font-size: 16px; font-weight: bold; fill: #0f172a; }
      .h { font-family: "Microsoft YaHei","SimHei",sans-serif; font-size: 12.5px; font-weight: bold; fill: #0f172a; }
      .b { font-family: "Microsoft YaHei","SimHei",sans-serif; font-size: 11.5px; fill: #334155; }
      .rel { font-family: "Microsoft YaHei","SimHei",sans-serif; font-size: 11px; fill: #0f172a; font-weight: 600; }
      .c { font-family: "Microsoft YaHei","SimHei",sans-serif; font-size: 10px; fill: #64748b; }
      .box1 { fill: #ffffff; stroke: #1d4ed8; stroke-width: 2; }
      .box2 { fill: #f1f5f9; stroke: #1d4ed8; stroke-width: 1.5; }
      .box3 { fill: #fffbeb; stroke: #b45309; stroke-width: 1.5; }
      .line { stroke: #334155; stroke-width: 1.8; fill: none; }
      .line-dash { stroke: #94a3b8; stroke-width: 1.5; fill: none; stroke-dasharray: 6 4; }
      .head { fill: #dbeafe; }
      .head-log { fill: #fde68a; }
    ]]></style>
  </defs>
  <text x="600" y="22" text-anchor="middle" class="t">数据库 E-R 关系图（5 表，紧凑版）</text>

  <!-- 上排：商品 | 评论 | 用户，高度随内容收紧 -->
  <rect x="32" y="48" width="260" height="86" rx="3" class="box2"/>
  <rect x="32" y="48" width="260" height="24" class="head"/>
  <line x1="32" y1="72" x2="292" y2="72" stroke="#94a3b8" stroke-width="0.8"/>
  <text x="162" y="65" text-anchor="middle" class="h">商品表 products</text>
  <text x="40" y="88" class="b">product_id，名称，类目，店铺，价格，总销量，平台</text>
  <text x="40" y="105" class="b">主键 id；时间 created_at</text>

  <rect x="320" y="40" width="520" height="102" rx="3" class="box1"/>
  <rect x="320" y="40" width="520" height="24" class="head"/>
  <line x1="320" y1="64" x2="840" y2="64" stroke="#94a3b8" stroke-width="0.8"/>
  <text x="580" y="57" text-anchor="middle" class="h">评论主表 reviews（核心）</text>
  <text x="328" y="80" class="b">review_id；product_id(FK)；user_id(FK)；review_text；rating；label(0/1/-1)</text>
  <text x="328" y="97" class="b">时间：review_time, crawl_time；平台 platform；is_cleaned；is_duplicate</text>
  <text x="328" y="114" class="b">特征：字数、叹号、repeat_char_ratio、sentiment、user_review_count、avg_interval</text>
  <text x="328" y="131" class="b">主键 id；时间 created_at</text>

  <rect x="868" y="48" width="300" height="86" rx="3" class="box2"/>
  <rect x="868" y="48" width="300" height="24" class="head"/>
  <line x1="868" y1="72" x2="1168" y2="72" stroke="#94a3b8" stroke-width="0.8"/>
  <text x="1018" y="65" text-anchor="middle" class="h">用户表 users</text>
  <text x="876" y="88" class="b">user_id，昵称，注册天数，历史评论数，均分，信用</text>
  <text x="876" y="105" class="b">主键 id；平台 platform；created_at</text>

  <!-- 关系线：对齐到垂直中心带 -->
  <line x1="292" y1="95" x2="320" y2="95" class="line"/>
  <text x="298" y="88" class="c">1</text>
  <text x="310" y="88" class="c">n</text>
  <text x="302" y="80" class="rel">拥有</text>
  <line x1="840" y1="95" x2="868" y2="95" class="line"/>
  <text x="848" y="88" class="c">n</text>
  <text x="860" y="88" class="c">1</text>
  <text x="852" y="80" class="rel">发表</text>

  <!-- 下排：日志，矮框 -->
  <rect x="48" y="200" width="500" height="64" rx="3" class="box3"/>
  <rect x="48" y="200" width="500" height="22" class="head-log"/>
  <line x1="48" y1="222" x2="548" y2="222" stroke="#d97706" stroke-width="0.6"/>
  <text x="298" y="215" text-anchor="middle" class="h" font-size="12px">爬取任务日志 crawl_logs</text>
  <text x="56" y="238" class="b">任务名、平台、目标商品数、总/成功/失败请求、获取条数、起止时间、状态、时间戳</text>

  <rect x="652" y="200" width="500" height="64" rx="3" class="box3"/>
  <rect x="652" y="200" width="500" height="22" class="head-log"/>
  <line x1="652" y1="222" x2="1152" y2="222" stroke="#d97706" stroke-width="0.6"/>
  <text x="902" y="215" text-anchor="middle" class="h" font-size="12px">数据清洗日志 cleaning_logs</text>
  <text x="660" y="238" class="b">清洗前/后、去重删、空删、过短删、清洗耗时、时间戳</text>

  <!-- 虚线汇到评论表底中 -->
  <path d="M 298 200 L 298 175 L 580 175 L 580 142" class="line-dash"/>
  <path d="M 902 200 L 902 175 L 580 175" class="line-dash"/>
  <text x="320" y="168" class="c">批次追溯（虚线=逻辑，可无单条外键）</text>

  <text x="600" y="300" text-anchor="middle" class="c" font-size="10.5px">实线：reviews→products、users 外键参照。虚线：两日志表为批次级记录。实现见 database.py。</text>
</svg>'''
open(p, "w", encoding="utf-8").write(s)
print("Wrote", p)
