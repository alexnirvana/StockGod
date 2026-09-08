# 国际化说明

[English](I18N.md) · [简体中文](I18N_CN.md)

Stock God 0.5 完整支持简体中文（`zh-CN`）与英文（`en`），覆盖界面、五章课程、测验、复习案例、新手引导、图表及接口反馈。

## 语言选择

登录页和主界面顶部都有语言选择器。未登录时使用浏览器已保存的偏好，否则参考浏览器语言：中文变体使用简体中文，英文变体使用英文，其他语言暂用英文。登录后以账号已保存的语言为准。

登录后的切换写入 MySQL 的 `players.locale`。旧账号升级后默认简体中文。切换语言不改变答案、得分、奖励、交易、昵称与用户复盘。两种语言都按中国时间展示日期，金额仍为人民币，不进行汇率换算。

## 资源位置

| 内容 | 位置 |
| --- | --- |
| i18next 配置与语言工具 | `frontend/src/i18n/index.ts` |
| 界面英文翻译 | `frontend/src/i18n/en.json` |
| 英文课程正文 | `content/courses/en/*.md` |
| 接口、测验和复习翻译 | `content/locales/en.json` |
| 响应翻译与语言协商 | `backend/src/stock_god/i18n.py` |

当前以原始中文文案作为 i18next key，中文资源由 key 生成，英文保存在 JSON 中。新增文案应使用完整句子和命名插值，不要拼接中文语序的短片段。显示翻译的组件通过 `useLocale()` 订阅语言变化。

API 根据 `Accept-Language` 协商语言，返回 `Content-Language`，并在 `Vary` 中声明语言差异。只翻译明确允许的展示字段；判分仍使用稳定题目索引与原始内容。幂等记录在读取响应时翻译，JSON 导出保留原始审计数据与系统文案，用户自己写的内容保持原文。

## 添加更多语言

1. 在前端语言工具与选择器中加入语言代码和名称，并注册 i18next 资源。
2. 完整翻译界面、五章正文、测验、复习、规则与系统提示，保留插值变量和答案顺序，并按[语音说明](NARRATION_CN.md)重新生成对应音频。
3. 扩展后端语言校验、协商与资源加载。语言代码不超过现有字段的 16 字符，否则增加迁移。
4. 保持查询缓存按语言和账号隔离，验证重新登录恢复账号偏好。
5. 扩展翻译覆盖测试，并检查桌面、手机、弹窗、错误状态和新手引导。

缺失翻译目前回退到原始中文。测试检查所有前端静态 key 和全部测验、复习案例；新增内容应同时提供对应翻译。

## 验证

```sh
python -m pytest tests/integration/test_i18n.py tests/integration/test_comparison.py -q
npm --prefix frontend test
npm --prefix frontend run build
```

完整后端测试还需使用专用 MySQL 测试库执行，见[运维说明](OPERATIONS_CN.md)。官方参考：[i18next 配置](https://www.i18next.com/overview/configuration-options)、[react-i18next hooks](https://react.i18next.com/latest/using-with-hooks)。
