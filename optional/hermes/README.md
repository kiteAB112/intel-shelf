# Hermes 可选适配（退出MVP主流程）

这是早期试验的保留入口，不是使用intel-shelf的前提。2026-11-03用户决定停止逐项测试Hermes，优先交付任何AI都可遵守的文档与MVP。实际项目入口是根目录README、workflows/investigate.md及workflows/maintain.md。

保留脚本未删除，默认不运行、不定时触发。原先scripts/review_with_hermes.py现位于本目录，ROOT路径已调整。历史验收见docs/hermes-review-validation.md；原始模型运行日志在本地Git忽略目录data/hermes-runs/。

本轮不再调用模型验证或改动Hermes配置。如将来明确需要适配，可按该脚本--help恢复手动使用，仍需审核模型输出，不能以结构通过代替事实正确。
