# HR智聘作品集演示数据包

这是一套**完全虚构、可重复生成、仅在显式确认后写入本地数据库**的作品集数据。它用于让岗位列表、公开投递、AI 初筛中心、候选人流程和招聘流程统计在本地演示时拥有足够的数据密度。

## 数据规模

- 5 个岗位：4 个开放、1 个历史关闭；
- 60 名不同候选人，严格少于 100 人；
- 64 次投递，其中 4 名候选人各有一次跨岗位投递；
- 40 次公开投递、16 次 HR 初筛录入、8 次 HR 直接通过；
- 60 份可直接上传的 UTF-8 TXT 虚构简历；
- 一套计划中的业务场景分布，以及与当前阶段 9 统计口径一致的预期漏斗和待办快照。

预期总漏斗为：

```text
64 申请
  → 32 初筛通过
  → 27 进入面试
  → 23 完成面试
  → 11 Offer 已发送
  → 7 Offer 已接受
  → 5 已录取
  → 3 已入职
```

实时待办预期为 20 条，覆盖阶段 9 定义的全部 7 类待办。

## 文件职责

| 文件 | 内容 |
| --- | --- |
| `jobs.json` | 5 个五段式 JD；`create_payload` 对齐当前 Job 创建字段，关闭岗位通过 `post_import_actions` 表达后续动作 |
| `candidates.json` | 60 名候选人的联系方式、普通资料、教育/工作/项目结构和对应简历路径 |
| `applications.json` | 64 次投递、来源、计划展示场景、当前状态、面试/Offer/处理轨迹 |
| `expected_statistics.json` | 全部岗位及单岗位的预期漏斗、转化率、耗时和待办 |
| `resumes/` | 60 份独立 TXT 简历，可用于公开投递或内部录入 |
| `generate_dataset.py` | 确定性生成器；固定版本下重复运行会得到相同业务内容 |
| `validate_dataset.py` | 离线校验人数、引用、状态、统计、隐私占位符和简历文件 |
| `import_dataset.py` | 本地 PostgreSQL 预检、事务演练和显式导入；校验当前 Schema、数据库约束及阶段 9 统计 |
| `.local/import_manifest.json` | 本机导入清单，精确记录本次新增 ID、文件和导入前后行数；已被 Git 忽略 |

## 生成与校验

在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe portfolio_demo\generate_dataset.py
.\.venv\Scripts\python.exe portfolio_demo\validate_dataset.py
```

生成和校验只读写 `portfolio_demo/` 下的已知数据文件，不连接 PostgreSQL、Redis 或 DeepSeek。

## 本地导入

导入器只允许连接 `development/dev/local/test` 环境中的本机 PostgreSQL，并拒绝覆盖已经存在的本版本演示数据。先检查和演练，再显式提交：

```powershell
.\.venv\Scripts\python.exe portfolio_demo\import_dataset.py inspect
.\.venv\Scripts\python.exe portfolio_demo\import_dataset.py dry-run
.\.venv\Scripts\python.exe portfolio_demo\import_dataset.py apply --confirm portfolio-demo-v1
```

`dry-run` 会真实执行 ORM 写入、数据库约束和统计 Service 校验，然后回滚事务。`apply` 会保留库中已有业务数据，新增本数据集并把 64 份按申请隔离的简历副本写到私有存储目录。再次执行 `apply` 时会根据演示候选人和本机清单停止，不会重复导入。

## 安全与诚实展示边界

- 姓名、号码、邮箱、学校、公司、项目、面试反馈和薪资全部为虚构；邮箱使用保留的 `.example` 域，电话使用未分配的 `+999` 演示号段。
- 简历不包含性别、年龄、民族、婚育、籍贯或照片等敏感招聘属性。
- `applications.json` 中的面试、Offer 和流程状态是导入器构造的**演示场景**，不是声称由真实 HR 操作产生的证据。
- 为让 AI 初筛页面可直接展示，导入器会创建 48 份确定性的虚构报告；结论正文保持正常阅读文案，不插入演示提示前缀。底层模型版本固定为 `portfolio-demo-fixture-no-model-call`，模型输入/输出 token 均为 0，因此它们只证明产品展示和数据链路，不是模型质量证据。
- 40 条公开投递处理记录全部导入为终态，关闭岗位使用 `paused/job_closed`；不会留下 `queued`、`running` 或 `waiting_screening` 记录，因此不会触发后台 Worker 或模型调用。
- 不自动 seed 是刻意设计：当前应用没有登录、RBAC、多租户和字段级薪资权限，演示数据只能由使用者显式导入到本地环境。

## 清理原则

当前未提供自动清理命令。若以后需要清理，只能使用本机导入清单精确记录的 ID 和存储文件，不得按邮箱后缀等宽泛条件清空开发库。
