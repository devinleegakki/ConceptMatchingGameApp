# 连接 Google Sheets 成绩服务

题库继续读原来的 CSV。成绩另存一份私有 Google 表，App 通过 Web App 访问。发布接口后，组员只需要部署网址，无需共享表格编辑权限或 Google 密码。

## 表格所有者一次性配置

1. 在 Google Drive 新建一份空白 **Google 表格**，命名为 Concept Match Scores，保持常规访问权限为“受限”。
2. 打开“扩展程序 → Apps Script”。将本目录的 `Code.gs` 复制到编辑器，保存。在函数菜单选 `setupScores`，点击运行并完成 Google 的授权。查看表格，确认出现 `Users`、`Attempts` 和列标题。这一步在绑定该表的脚本编辑器中执行。
3. 点击“部署 → 新部署 → Web 应用”。执行身份选表格所有者，可访问用户选 **任何人（包括无需登录的玩家）**。复制以 `/exec` 结尾的 Web App URL。若学校账号未提供该访问级别，需使用获准支持匿名访问的账号或请管理员开放。保持成绩表本身为受限。
4. 在工程根目录打开 PowerShell。临时桌面联调可以设置环境变量；为了让其他组员和安装包也能找到接口，请同时在构建前写入配置文件：

   ```powershell
   $env:SCORES_API_URL = Read-Host 'Paste your deployed /exec URL'
   Set-Content -Encoding ascii -LiteralPath src/services/scores_endpoint.txt -Value $env:SCORES_API_URL
   ```

   配置文件须随本地工程构建，已从 Git 排除。将部署 URL 单独交给负责打包的组员即可。
5. 用组员原项目的 Python 环境运行 `python main.py`。进入 Profile，看到随机英文游客名和 0 次挑战，即可确认 App 成功连接。打开 Leaderboard，尚无两关通关记录时应显示空榜。GET 打开接口网址不是联调方法，App 使用 JSON POST。

更新后端代码时，在“管理部署”中编辑原 Web App，选择新版本，再部署，原 URL 可继续使用。官方文档：[Apps Script Web Apps](https://developers.google.com/apps-script/guides/web)。

## 现场验收

- 游客在首页直接开始。第一关 4 对、5 步、最高连击 3、剩余 60/120 秒应得 **85/100**。超时保留配对和连击分，时间分为 0。结算数据先写入设备待同步队列，网络恢复后重新打开 Profile 或排行榜即可重传。
- Google 表的 Attempts 每一次通关或超时新增一行。重复请求同一 attempt_id 不会多加一行。Profile 显示挑战次数、通过次数、最佳完整成绩和最近 10 次记录。
- 第二关超时后点 Retry level 属于原轮次；从首页重新开始第一关属于新轮次。两关成绩仅在同一 run_id 均成功时计入排行榜，每位玩家只占一行；同分并列。
- 在 Profile 输入英文昵称，点击 Create account，原游客成绩随账号保留。点眼睛显示 **32 位私人登录码**并自行保存。在另一台设备的 Profile 中用该码 Sign in 即可读取相同历史。昵称可重复，登录码才是账号凭证。Sign out 会创建新游客。仅向原玩家显示登录码，服务端仅存凭证摘要。
- 成绩与排名以表中已同步数据为准。缺少部署网址、无网或权限不对时显示错误和待传数量；题库仍需要组员原实现的网络连接。首次发布后，用拟展示的安卓设备完整跑一遍游客、登录、通关和刷新排行榜。

## 计分 v1

配对分 = max(0, 70 × 成功对数 / 目标对数 − 5 × 错配次数)。错配次数 = 步数 − 成功对数。
连击分 = 20 × 最高连击 / 目标对数。时间分 = 10 × 剩余秒数 / 关卡总秒数，仅通关获得。
三项相加后统一四舍五入，单关最高 100，两关最高 200。App 计算即时成绩，Apps Script 根据原始字段独立计算入表分数。

## 本地验证

在工程根目录运行 `python -m pytest -q` 和 `node --test tests/sheets_backend.cjs`。后者使用内存表检查实际 Apps Script 的操作逻辑，真实 Google 授权和部署需按上述步骤验证。
