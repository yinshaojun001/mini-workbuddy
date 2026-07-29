# 知梦传统梦象来源与重建

## 来源边界

知梦 v1 的传统条目来自公版《周公解梦》。所用转录文本可追溯到中文维基文库：

- 中文维基文库：<https://zh.wikisource.org/wiki/周公解夢>
- 转换参考仓库：<https://github.com/tf1993614/Know-your-fate>
- 固定上游提交：`1aa675597ee1405c9dea142bda0a3a9ed460ac99`
- 固定上游目录：`.claude/skills/zhougong-dream-interpretation/references/zhougong`
- 运行时索引版本：`1.0.1`
- 来源标识：`zhougong-public-domain-v1`

古代原文按公版材料使用。转换参考仓库的代码与整理材料采用 MIT License，版权声明为：

> Copyright (c) 2026 Feng Tang and 命数天问 (Mingshu Tianwen) contributors

完整 MIT notice 保存在 [ATTRIBUTION.md](../backend/app/bootstrap/assets/dream-interpreter/references/ATTRIBUTION.md)，上游许可证固定链接为：

<https://github.com/tf1993614/Know-your-fate/blob/1aa675597ee1405c9dea142bda0a3a9ed460ac99/LICENSE>

传统断语只作文化参照，不代表未来事实、医学结论、心理诊断或治疗建议。项目不抓取现代商业解梦网站，也不在用户请求期间联网检索解释。

## 索引内容

离线构建器固定读取 27 个分类 Markdown 文件，并验证其中 988 条 `- ` 开头的转录条目。运行时索引仅保留 37 个经过审阅的常见意象，每项包含：

- 稳定 symbol ID 与显示名称。
- 简体、繁体和常见口语别名。
- 分类、原文断语和来源 ID。
- 固定索引版本与上游提交 SHA。

匹配器在本地执行 Unicode 规范化、最长别名优先、同一 symbol 去重和最多 8 条限制。没有命中是正常结果；索引损坏时 Dream Adapter 返回不可用状态，不能让模型凭记忆补造传统引用。

## 离线重建

在项目根目录执行：

```bash
cd backend
uv run python scripts/build_dream_references.py
uv run pytest tests/test_dream_references.py tests/test_dream_public_adapter.py -q
```

构建脚本只在维护阶段下载固定 SHA 的归档一次，生产启动和公开解梦请求不会调用它。重建后需要人工检查以下文件：

- `app/bootstrap/assets/dream-interpreter/references/dream-symbols.json`
- `app/bootstrap/assets/dream-interpreter/references/ATTRIBUTION.md`

如果更换来源提交、原文、别名或精选条目，必须提升索引版本，更新本页和 attribution，并重新运行 40 案真实模型评测。Dream App 在评测与人工审阅完成前保持 `enabled=false`。
