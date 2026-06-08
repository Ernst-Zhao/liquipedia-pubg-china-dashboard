# 中国 PUBG 战队历年成绩与奖金看板

基于 Liquipedia PUBG Wiki 整理的中国战队赛事成绩和奖金可视化看板。
https://ernst-zhao.github.io/liquipedia-pubg-china-dashboard/

## 功能

- 34 支中国 PUBG 战队历年奖金矩阵
- 战队总奖金排行与年度变化比较
- 1,393 条赛事成绩筛选及奖金合计
- USD、CNY 和双币显示
- 人民币按赛事年份的年度平均汇率估算

## 数据来源

- [Liquipedia PUBG Wiki](https://liquipedia.net/pubg/)
- [Liquipedia Chinese Teams](https://liquipedia.net/pubg/Category:Chinese_Teams)
- [FRED AEXCHUS](https://fred.stlouisfed.org/series/AEXCHUS)

本项目与 Liquipedia、PUBG Studios 或赛事组织方没有隶属关系。数据可能因来源页面修订而变化。

## 本地使用

直接打开 `index.html` 即可。网站为纯静态页面，不需要服务器或构建工具。

## 自动更新

GitHub Actions 每周一北京时间 08:00 自动同步 Liquipedia 数据，也可以在仓库的 Actions 页面手动运行。

更新过程：

1. 按至少 31 秒间隔读取 34 支战队的 Results / Overview 页面。
2. 在临时目录生成新数据，不直接修改线上文件。
3. 检查战队覆盖、记录数量、重复记录、负数奖金和年度汇总。
4. 只有全部校验通过时才替换 `data.json` 和 `data.js`。
5. 自动提交到 `main`，GitHub Pages 随后重新发布。

如果 Liquipedia 返回 `429`、页面为空或数据量异常下降，任务会失败并保留上一次有效数据。

手动更新：

```bash
pip install -r requirements.txt
python scripts/update_data.py
python scripts/validate_data.py
```

可通过 `LIQUIPEDIA_REQUEST_DELAY` 调整请求间隔，但不应低于 Liquipedia API 使用条款要求。

## License

MIT
