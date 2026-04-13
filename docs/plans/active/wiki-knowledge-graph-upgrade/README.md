---
created_at: 2026-04-12
updated_at: 2026-04-13
doc_status: active
---

# Wiki Knowledge Graph Upgrade

升级目标：把当前“页面列表 + 页面级图谱”的 wiki 体系，推进到“稳定元数据 + 自动关联 + 混合搜索 + 概念图谱”的可持续知识系统。

当前分五段推进：

1. 补齐 `project / tags / links / source_path / doc_type`
2. 接入时自动提取候选 links
3. 搜索升级为 `BM25/FTS + vector + graph boost`
4. 图谱节点从页面降到实体/决策/模块/错误模式
5. 图谱显示升级为 `Schema / Explore / Table` 多视图浏览

GitHub 参考方向：

- [aws/graph-explorer](https://github.com/aws/graph-explorer)
- [antvis/G6](https://github.com/antvis/G6)
- [antvis/Graphin](https://github.com/antvis/Graphin)
- [cytoscape/cytoscape.js](https://github.com/cytoscape/cytoscape.js)
- [vasturiano/react-force-graph](https://github.com/vasturiano/react-force-graph)
