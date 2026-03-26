# Profile Check Rules

未来 `profiles/` 落地后，至少要校验：

1. profile 引用的 standards 文件都存在
2. profile 生成的模板路径都存在
3. profile 声明的验证命令可执行
4. profile 安装行为是幂等的