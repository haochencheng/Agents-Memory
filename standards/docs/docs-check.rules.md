# Docs Check Rules

第一版文档校验至少应覆盖：

1. docs 入口文件存在性
2. `docs/README.md` 中引用的文件存在性
3. README 与 getting-started 中命令列表的一致性
4. `llms.txt` 中的 repo map 与真实路径一致性
5. 过期结构或私有绝对路径引用告警

通过标准：

1. 无缺失文件引用
2. 无关键命令文档漂移
3. 无明显已废弃但未标记的结构说明