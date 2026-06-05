# intervals.icu Strava 数据自动同步工具

## 它能解决什么问题？

如果你同时使用 Strava 和 [intervals.icu](https://intervals.icu)，你可能会发现：虽然 intervals.icu 网站上能正常显示来自 Strava 的骑行数据，但当你想通过 intervals.icu 的 API 获取这些数据时（比如接入第三方工具、做数据分析），返回的全是空记录。

这是 intervals.icu 的一个已知限制 —— Strava 来源的活动在 API 中不可用。

本工具的解决方案很简单：**自动把 Strava 活动的完整数据重新上传到 intervals.icu**，让它变成"手动上传"来源的活动。上传后 intervals.icu 会自动替换掉原来的空记录，不会产生重复，不会影响你的训练负荷计算。

整个过程完全自动，部署后无需任何操作。

---

## 部署教程（零基础友好）

你需要准备：
- 一个 [GitHub](https://github.com) 账号（免费注册即可）
- 一个 [intervals.icu](https://intervals.icu) 账号（已绑定 Strava）

整个过程大约 10 分钟，不需要写任何代码。

---

### 第 1 步：获取 intervals.icu 的信息

你需要从 intervals.icu 获取 3 样东西。

#### 1.1 获取 Athlete ID

1. 打开 https://intervals.icu ，登录你的账号
2. 点击顶部导航栏的 **设置**（或 Settings）
3. 页面最上方会显示你的 Athlete ID，格式类似 `i123456`（字母 `i` 开头加一串数字）
4. 复制保存备用

#### 1.2 获取 API Key

1. 还是在设置页面，向下滚动找到 **Developer Settings**（开发者设置）
2. 如果还没有 API Key，点击生成一个
3. 复制这串密钥保存备用（一串字母和数字组成的字符串）

#### 1.3 确认你的登录邮箱和密码

就是你登录 intervals.icu 时用的邮箱和密码。如果你一直用"与 Strava 连接"登录而没有设置过密码，需要先去设置页面设一个密码。

---

### 第 2 步：Fork 本仓库

"Fork"就是把这个项目复制一份到你自己的 GitHub 账号下。

1. 确保你已登录 GitHub
2. 点击本页面右上角的 **Fork** 按钮

   ![Fork 按钮位置示意](https://docs.github.com/assets/cb-79331/mw-1440/images/help/repository/fork-button.webp)

3. 在弹出的页面中，**不需要改任何设置**，直接点击绿色的 **Create fork** 按钮
4. 等几秒钟，你就拥有了自己的副本

---

### 第 3 步：配置你的账号信息（Secrets）

你的密码和密钥不会出现在任何代码文件中，而是存储在 GitHub 的加密保险箱（Secrets）里，只有自动任务运行时才能读取，任何人（包括你自己）都无法在网页上回看明文。

1. 在你 Fork 后的仓库页面，点击顶部的 **Settings**（设置）标签

2. 在左侧菜单中，找到 **Secrets and variables**，点击展开，再点击 **Actions**

3. 你会看到一个 "Repository secrets" 区域，点击右上角的 **New repository secret** 按钮

4. 你需要依次添加 **4 个** secret，每添加一个就点 **Add secret** 保存，然后再添加下一个：

   | Name（名称，必须完全一致） | Secret（值） |
   |---|---|
   | `ICU_EMAIL` | 你的 intervals.icu 登录邮箱 |
   | `ICU_PASSWORD` | 你的 intervals.icu 登录密码 |
   | `ICU_API_KEY` | 第 1 步获取的 API Key |
   | `ICU_ATHLETE_ID` | 第 1 步获取的 Athlete ID（如 `i123456`） |

   > **注意**：Name 列的内容必须严格按上表填写（全大写、下划线），否则程序找不到对应信息会报错。

5. 添加完毕后，页面上应该显示 4 条 secret 记录（只显示名称，不显示值 —— 这是正常的）

---

### 第 4 步：启用自动任务

Fork 后的仓库默认会**禁用**所有自动任务（这是 GitHub 的安全策略），你需要手动开启：

1. 点击仓库顶部的 **Actions** 标签
2. 你会看到一条黄色提示，大意是"此仓库的 workflow 已禁用"
3. 点击绿色按钮 **I understand my workflows, go ahead and enable them**
4. 在左侧列表中点击 **sync-strava-via-icu-web**
5. 你会看到一条提示说此 workflow 有一个 schedule 触发器，点击 **Enable workflow** 启用它

---

### 第 5 步：手动运行一次，确认一切正常

1. 还在 Actions 页面，左侧选中 **sync-strava-via-icu-web**
2. 右侧点击 **Run workflow** 按钮
3. 弹出的小面板中保持默认设置，点击绿色 **Run workflow**
4. 等待几秒钟，页面上会出现一条新的运行记录，点进去查看
5. 点击 **sync** 这个 job，再点击 **run sync** 这个 step 查看日志

**运行成功的标志**：日志最后一行类似：
```
done: uploaded=3 queued=0 wrong-type=0 failed=0
```
- `uploaded=3` 表示成功上传了 3 条活动
- `failed=0` 表示没有失败

如果你之前 Strava 有很多活动，第一次运行只会处理最近 7 天的。可以在 Run workflow 面板里把 `Days back to scan` 改大（比如 `30` 或 `90`）来同步更多历史数据。

---

### 第 6 步：完成！

**不需要做任何其他事情了。**

从现在起，这个工具每 30 分钟会自动检查一次你的 intervals.icu 账号。当你完成一次 Strava 骑行后：

1. Strava 同步数据到 intervals.icu（通常几分钟内）
2. intervals.icu 分析处理数据（几分钟到几小时）
3. 本工具检测到新数据，自动下载并重新上传
4. 数据变为 API 可访问状态

---

## 常见问题

**Q: 会不会产生重复的活动记录？**
不会。intervals.icu 会自动用上传的完整数据替换掉原来的 Strava 空记录。

**Q: 会影响我的训练负荷（CTL/ATL）计算吗？**
不会。因为没有重复，数据量和之前完全一致。

**Q: 我的密码安全吗？**
安全。密码存在 GitHub 的加密 Secrets 中，不会出现在代码或日志里。即使仓库是公开的，其他人也看不到你的 Secrets。

**Q: 只同步骑行活动吗？能同步跑步吗？**
默认只同步骑行（Ride）。如果你也需要同步其他类型，在 Run workflow 时把 `activity_types` 改成你需要的类型，用逗号分隔。常见类型：

| 类型名 | 含义 |
|---|---|
| `Ride` | 户外骑行 |
| `VirtualRide` | 室内骑行（Zwift 等） |
| `MountainBikeRide` | 山地骑行 |
| `GravelRide` | 砾石骑行 |
| `Run` | 跑步 |
| `TrailRun` | 越野跑 |
| `Swim` | 游泳 |
| `Walk` | 步行 |
| `Hike` | 徒步 |

例如同时同步户外骑行和室内骑行，填：`Ride,VirtualRide`

如果想**长期**变更默认值（而不是每次手动填），你需要编辑仓库中的 `.github/workflows/sync.yml` 文件，找到 `default: "Ride"` 改成你想要的值。

**Q: 自动任务突然不运行了？**
GitHub 会在仓库连续 60 天没有任何活动（提交、issue 等）时自动停用定时任务。去 Actions 页面重新启用即可。建议偶尔去 Actions 页面看一眼运行状态。

**Q: 如果我修改了 intervals.icu 的密码怎么办？**
去仓库 Settings → Secrets and variables → Actions，找到 `ICU_PASSWORD`，点击更新按钮，填入新密码。

---

## 致谢

本工具基于 [intervals.icu](https://intervals.icu) 的 Web API 和公开 API 构建。感谢 David Tinker 创建了如此强大的训练分析平台。
