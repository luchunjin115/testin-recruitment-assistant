# 最终命名与交付收口计划

> 归档位置说明：本计划已经执行完成，现只用于最终命名和交付收口过程追溯。

> 日期：2026-08-18
>
> 状态：第 5A—5D 步已全部完成，最终命名与交付文档收口结束
>
> 前置条件：旧版退役第 1—4 步已完成，70 个旧代码文件已经删除并通过全量回归

## 1. 为什么还需要这一步

旧版与新版并行期间，项目使用 `stage3`、`rebuilt` 和 `V2_STORAGE_DIR` 隔离新版代码。旧版已经删除后，这些名字不再表示真实产品概念，会让读者误以为项目仍处于临时迁移状态。

本步骤只处理命名和交付材料，不改变招聘业务流程、数据字段、状态流转、权限或 AI 评分规则。

## 2. 只读盘点结果

### 2.1 前端 `stage3`

- 浏览器 `/stage3` 路径出现在 9 个运行文件、14 个测试文件和 11 份文档中。
- `frontend/src/stage3/` 共有 40 个文件，其中 10 个页面/Layout 文件使用 `Stage3*` 前缀。
- 该名称对用户可见，也是当前最应优先收口的施工期名字。

### 2.2 后端 `rebuilt`

- `backend/app/**/rebuilt/` 共有 68 个源码文件，相关 `backend/tests/**/rebuilt/` 共有 60 个测试文件。
- 当前旧同级 Model、Schema、Service、Prompt 已删除，因此 `rebuilt` 隔离层已经失去职责。
- 这是内部 Python import 路径，不改变 HTTP API 或 PostgreSQL 表名，但移动范围大，必须单独执行并做全量回归。

### 2.3 `/api/v2` 与 `V2_STORAGE_DIR`

- `/api/v2` 是正式版本化业务接口，共影响 13 个运行文件。版本号能给未来不兼容升级留下边界，建议保留。
- `V2_STORAGE_DIR` 出现在 7 个配置、运行和测试文件中。文件存储不应使用 API 版本命名，建议改为 `STORAGE_DIR`。

### 2.4 根目录交付文档

- `README.md` 496 行、`使用说明.md` 1195 行、`HANDOFF.md` 469 行、`TODO_NEXT.md` 231 行，共 2391 行。
- README 仍有 9 处、使用说明 3 处、HANDOFF 72 处、TODO 5 处引用已经删除的 SQLite、旧 Router/Page 或演示数据脚本。
- 启动脚本本身已经使用 PostgreSQL、Alembic、当前 FastAPI 和 Vite，可以保留；问题主要在说明文字已经过时。

## 3. 推荐的最终命名

| 当前名称 | 推荐名称 | 原因 |
| --- | --- | --- |
| 浏览器内部工作台 `/stage3/*` | `/app/*` | 明确表示 HR 登录后的产品工作台，不暴露开发阶段编号 |
| 公开投递 `/stage3/apply` | `/apply` | 对求职者最直观，不经过内部工作台前缀 |
| `frontend/src/stage3/` | `frontend/src/features/recruitment/` | 按业务功能组织，不再按历史开发阶段组织 |
| `Stage3Dashboard` 等组件 | `RecruitmentDashboard` 等语义名称 | 简历和面试中更容易说明职责 |
| `backend/app/**/rebuilt/` | 移到对应父目录 | 旧同级实现已删除，不再需要隔离层 |
| 测试目录中的 `rebuilt/` | 移到对应父目录 | 测试路径与正式源码保持一致 |
| `V2_STORAGE_DIR` | `STORAGE_DIR` | 存储配置不与 API 版本耦合 |
| `/api/v2`、`v2Http` | 保留 | 它们明确表示正式 API 版本，不是旧系统残留 |

不保留 `/stage3/*` 兼容路由。项目尚未正式上线且旧系统已明确退役，继续保留兼容入口会重新制造遗留合同；未知地址统一进入 `/app/dashboard`。

## 4. 建议实施顺序

### 第 5B 步：前端最终命名

- 把浏览器内部路径改为 `/app/*`，公开投递直接使用 `/apply`。
- 把 `src/stage3/` 移到 `src/features/recruitment/`，移除 `Stage3*` 组件前缀。
- 同步更新前端测试，不修改后端接口与业务逻辑。
- 验证 14 个前端脚本和生产构建。

实际结果（2026-08-18）：

- `frontend/src/stage3/` 的 40 个文件已移动到 `frontend/src/features/recruitment/`，10 个页面/Layout 文件、相关 TypeScript 类型和 Service 方法均从 `Stage3*` 改为 `Recruitment*`。
- 浏览器内部工作台已改为 `/app/*`，公开投递页 `/apply` 直接加载投递表单；没有保留 `/stage3/*` 兼容路由，未知地址进入 `/app/dashboard`。
- 9 个 `stage3-*` 测试文件与对应 npm script 已改为 `recruitment-*`；CSS 中 1446 处 `s3-` 施工期前缀同步改为 `recruitment-`。
- 运行源码中 `stage3`、`Stage3`、`s3-` 引用均为 0；入口保护测试会阻止 `frontend/src/stage3/` 或 `/stage3` 路由重新出现。
- 前端 14 个测试脚本全部通过，`tsc && vite build` 成功转换 3116 个模块。目录首次移动后测试发现 Service 到公共 HTTP 客户端的相对路径少一级，已修正并从头完成全量回归。

### 第 5C 步：后端最终命名

- 将 Model、Schema、Service、Adapter、Prompt 的 `rebuilt` 内容移到父 package。
- 同步移动测试、更新 import、Alembic metadata import 和 `app/main.py` 临时变量名。
- 将 `V2_STORAGE_DIR` 改为 `STORAGE_DIR`，保留 `/api/v2`。
- 验证后端全量测试、OpenAPI、Alembic、真实 PostgreSQL 空数据状态。

实际结果（2026-08-18）：

- 5 个正式源码和 5 个测试 `rebuilt/` 目录已移除；63 个源码文件、55 个测试文件共 118 个文件移动到对应父 package，129 个 Python 文件的 import 路径完成机械更新。
- 正式 package 的 `__init__.py` 已合并导出，`app/main.py` 的 `rebuilt_*` Router 别名改为正式模块名；运行源码与普通测试中的 `rebuilt` import/标识扫描均为 0。
- `V2_STORAGE_DIR` 已改为 `STORAGE_DIR`，并同步 `.env.example`、Docker Compose、配置、API 与测试；无调用者的旧 `UPLOAD_DIR` 同步删除。业务 API `/api/v2` 和私有存储内部 `v2/resumes` 命名空间不变。
- 旧代码防回流测试已适应最终路径：7 个被新版复用的 Model/Schema/Service 文件必须存在且包含 PostgreSQL Base、Pydantic v2 `ConfigDict` 或异步 `AsyncSession` 标记；10 个 `rebuilt/` 目录和其他旧专属文件必须不存在。
- 后端全量 595 项测试通过；OpenAPI 46 个 path 全部属于 `/api/health` 或 `/api/v2/*`；Alembic 位于 `f8c2d0e5b317 (head)` 且无 Schema 差异。
- PostgreSQL 12 张业务表仍为 0 行，Redis 0 个键、Chroma 0 个 collection、`backend/storage` 0 个文件，`sample_data/` 4 个受控文件保留。

### 第 5D 步：交付文档收口

- 从当前代码重新编写 README：产品定位、当前能力、架构、快速启动、测试、项目结构和阶段状态。
- 从当前 UI 与接口重新编写使用说明，只描述已经实现的新版流程，不编造尚未完成能力或演示数据。
- 删除旧 `HANDOFF.md`、`TODO_NEXT.md`，由 `PROJECT_STATE.md`、实施计划和阶段设计承担现行交接；历史仍可从 Git 追溯。
- 核对所有启动命令和链接，完成一次人工启动/页面验收。

实际结果（2026-08-18）：

- 根目录 `README.md` 和 `使用说明.md` 已按当前代码重写，只描述新版 PostgreSQL 主链、现有 UI/API、AI 配置、空数据状态和明确的未完成功能。
- 过时的 `HANDOFF.md`、`TODO_NEXT.md` 已删除；现行进度与交接统一由 `PROJECT_STATE.md`、实施计划和专项设计承担。
- `scripts/start_project.ps1` 默认打开地址已从旧施工期 URL 改为 `/app/jobs`；启动环境检查、文档链接与遗留引用扫描、Compose 解析和补丁格式检查通过，前端 14 个测试脚本按 README 中的命令重新全量执行通过。
- 新增 `docs/2026-08-18-legacy-retirement-summary.md`，提供整个退役过程的统一修改、验证、数据恢复边界和简历表达说明。
- 本步没有新增业务功能或修改 API、Schema、Service、Model、PostgreSQL 数据和 Alembic 历史。旧系统退役全部结束，开发恢复到阶段 7 下一小步。

## 5. 每步共同边界

- 不修改 PostgreSQL 表名、字段、约束或既有 Alembic revision。
- 不删除或生成业务数据，不创建演示数据。
- 不改变阶段 7 Application、Rubric、AI 初筛和 HR 决策合同。
- 不把命名清理扩展成新功能开发。
- 每个小步骤单独验证，前一步通过后才进入下一步。

## 6. 总体验收标准

- 运行代码和现行交付文档不再出现作为施工期命名的 `stage3`、`Stage3`、`rebuilt`、`V2_STORAGE_DIR`。
- 浏览器使用 `/app/*` 与 `/apply`；业务 API 继续使用 `/api/v2`。
- 前后端全量自动化测试、生产构建、OpenAPI 和 Alembic 检查通过。
- README 与使用说明可以让新开发者仅依据当前文件启动并理解项目。
- PostgreSQL、Redis、Chroma、新版存储和 `sample_data/` 不被删除或改写。
