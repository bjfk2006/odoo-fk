# Runbook — purchase_transit 模块（构建 / 安装 / 测试 / 回滚）

**对应设计**：`docs/design/2026-06-25-purchase-transit-tracking-solution.md`
**模块路径**：`addons/purchase_transit/`
**适用**：Odoo 19.0 社区版

> ✅ **已在测试服 43.134.82.40 用 Docker（odoo:19 + postgres:16）实测**：模块安装成功、6 个自动化测试全绿（`0 failed, 0 error of 6 tests`）、Web 服务 `HTTP 200`。实测过程中发现并修复了 3 个真实问题（`date_ordered` 类型不一致、Odoo 19 搜索视图 `expand` 已移除、里程碑约束误拦回填）——见 §10 与 git 提交 `9817822a` / `346a41ed`。

---

## 0. Docker Compose 一键启动（推荐，已实测）

仓库根已提供 `docker-compose.yml`，用官方 `odoo:19` 镜像的依赖 + **挂载本仓库源码跑 `odoo-bin`**（即跑这套真实代码，而非镜像内置 Odoo）。

```bash
# 在仓库根目录
docker compose up -d            # 首次启动自动建库 odoo + 安装 purchase_transit（含 demo 数据）
docker compose logs -f odoo     # 跟踪日志，等到 "HTTP service (werkzeug) running"
# 浏览器打开 http://<host>:8069   DB=odoo, 账号 admin / 密码 admin
docker compose down             # 停止（加 -v 连同 DB/filestore 数据卷一并删除）
```

- 服务清单：`db`（postgres:16，健康检查就绪后才起 odoo）、`odoo`（19，端口 8069）。
- `command` 里的 `-i purchase_transit` 仅首次安装；模块已装后为 no-op，可保留。
- 改了模块代码要重载：`docker compose run --rm odoo -d odoo -u purchase_transit --stop-after-init`（或临时把 command 的 `-i` 换成 `-u`）。
- 跑测试：
  ```bash
  docker compose run --rm odoo -d test_pt -i purchase_transit \
    --test-enable --test-tags /purchase_transit --stop-after-init --no-http --max-cron-threads=0
  ```
- ⚠️ 外网访问 8069 需云安全组放行入站；`user: root` 仅适合测试环境（生产请用专用用户 + 受控权限）。

---

## 1. 依赖准备

- 无新增第三方 Python 依赖。
- 模块依赖（`__manifest__.py`）：`purchase_stock`、`mail`（均为标准社区模块，随核心提供）。
- 确认这些模块在目标库可安装：`purchase`、`stock`、`purchase_stock`、`mail`。

## 2. 数据库 migration

- 无手写 migration 脚本。安装/升级由 Odoo ORM 自动建表：
  - 新表 `purchase_transit`；
  - `purchase_order` / `purchase_order_line` / `stock_move` 新增反向关联字段（One2many 不建列；`purchase_transit` 的 related 存储字段会建列）。
- 升级命令（测试库）：
  ```bash
  ./odoo-bin -d <db> -i purchase_transit --stop-after-init
  ```
- 已安装后改了代码再升级：
  ```bash
  ./odoo-bin -d <db> -u purchase_transit --stop-after-init
  ```

## 3. 配置变更

- 新增系统参数：`purchase_transit.auto_generate_on_confirm`（`res.config.settings` 中开关「PO 确认时自动生成在途跟踪」，默认关闭）。
- 新增定时任务：`Purchase Transit: check delays`（每日，扫描延误并建催办活动）。如不需要主动催办，可在「设置→技术→定时任务」停用。
- 无新增 secret / 环境变量。

## 4. 构建命令

- 纯 Python/XML 模块，无前端资产编译。安装即生效（见 §2）。

## 5. 静态检查（已在开发机执行，验证者可复跑）

```bash
cd addons/purchase_transit
python3 -m py_compile models/*.py          # 预期：无输出 = 通过
# XML 良构（任一）：
xmllint --noout $(find . -name '*.xml')     # 预期：无输出
```
- 建议 CI 跑 `ruff check addons/purchase_transit`（项目根有 `ruff.toml`）。

## 6. 安装冒烟（验证者在测试库）

1. 安装模块（§2 命令）→ 预期无 traceback，模块状态 `installed`。
2. 启动实例，以 admin 登录。
3. 「设置→用户」给测试用户加 **Logistics Officer / Logistics Manager** 组（`Transit Tracking` 权限分类下）。

## 7. 手工验证清单（staging 浏览器）

**Golden path（收货闭环，最关键）**
1. 采购 → 新建 PO，加 1 个可入库产品行 → 确认。
2. PO 表单点 **Generate Transit Tracking** → 跳出在途列表，应有 1 条 `TR/2026/0001`，state=`Ordered`。
3. 打开该在途记录：填船名/航次/柜号、ETD、ETA(斐济)、依次填 实际工厂发货/集港/ATD/ATA/清关 → 顶部 statusbar 应逐步推进；`transit_days`/`eta_delay_days` 应计算。
4. 回到 PO，对收货单做**收货过户（Validate）** → 回到在途记录，**`Actual Received` 应被自动填上当日**，state 自动变 `Received`。✅ 这是核心闭环，重点验。

**可视化**
5. 在途菜单切到 **Kanban**：记录应按里程碑分列；延误记录红色高亮。
6. 切到 **Calendar**：按 ETA 显示；**Pivot/Graph**：可按供应商看 transit_days。

**Edge / 韧性**
7. 删除某 PO 行的在途记录后再收货 → **收货应正常完成**（无 traceback；后台日志可能有 `purchase_transit: failed to sync` 但不阻断）。重点验「跟踪失败不挡收货」。
8. 同一 PO 行重复点 Generate → **不应重复建**（unique 约束 + 去重）。
9. 故意把 ATA 填得早于 ATD → 保存应报 `ValidationError`（日期顺序校验）。
10. 部分收货（收货数量 < 订单数量）→ 在途记录 `is_partial=True`，state=`Received`。

**多公司（若启用）**
11. 切到另一公司用户，不应看到他司在途记录（`ir.rule` 隔离）。

**回归（相邻特性别被打破）**
12. 不安装本模块时的标准采购→收货流程不受影响（本模块只新增，未改既有字段语义）；卸载后 PO/收货仍正常。

## 8. CI gates

- `ruff check addons/purchase_transit`（0 error）。
- Odoo 测试运行器安装本模块 + 依赖，`--stop-after-init` 无 traceback（最低门槛）。
- 本模块**已附自动化测试** `tests/test_transit_flow.py`（`TransactionCase`，`post_install`），覆盖 6 个用例：
  1. `test_generate_and_receive_closes_loop` — 核心闭环：生成→收货 done→`actual_received` 自动填、state=received。
  2. `test_generate_is_idempotent` — 重复生成不建重复记录。
  3. `test_milestone_date_order_constraint` — 日期逆序触发 `ValidationError`。
  4. `test_receipt_not_blocked_without_transit` — 无在途记录时收货照常完成（韧性）。
  5. `test_state_progression_and_eta_delay` — 状态推进 + ETA 延误/在途天数计算。
  6. `test_partial_receipt_flag` — 部分收货 `is_partial=True`。
- 运行命令（测试库）：
  ```bash
  ./odoo-bin -d <db> -i purchase_transit --test-enable --test-tags /purchase_transit --stop-after-init
  ```
  预期：6 用例全绿，无 traceback。
- ⚠️ 测试**未在开发机执行**（无 DB 环境）；仅 `py_compile` 语法通过。需验证者在测试库跑上述命令确认。

## 9. 回滚策略

- 卸载模块：「应用→purchase_transit→卸载」，或 `./odoo-bin -d <db> -u base`（先在 UI 卸载）。
  - 卸载会**级联删除** `purchase_transit` 表数据（`ondelete=cascade`）；PO / 库存 / 财务数据不受影响。
- 代码回滚：本模块全部新增文件，`git revert`/删除 `addons/purchase_transit/` 即可，无既有文件改动需要还原。
- 配置回滚：停用系统参数与定时任务（见 §3）。

---

## 已知简化（相对设计文档）

- `state` 采用**纯计算只读**（由实际日期派生），未做「手动覆写」——比设计 §7.2 的「compute+手动」更简、更不易误操作；如确需人工强制改状态，再加 inverse。
- 目的港 `pod` 用固定下拉（Suva/Lautoka/Other），按 §11-Q3 推荐。
- 「1 PO 行 = 1 在途记录」（unique 约束），按 §11-Q1 推荐的 v1 方案；未做「一柜多行」父记录。
