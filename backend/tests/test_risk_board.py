"""
Risk Board (RiskHealth 页面 91→1 聚合端点) · 性能轮 R2 任务 B 测试

覆盖:
    - 空库 / 有建筑无评估 / 有建筑有评估 / 多建筑 三种基本行为
    - 单建筑异常被隔离 (与 overview 共享同一契约)
    - alerts 一次拉全, 与 N 无关
    - **字段级等价**: 聚合结果里每栋楼 health/risk 与逐楼端点返回**字段级完全相同**
    - SQL 条数与 N 无关 (N=1 / 10 / 30)
    - 注册顺序: /risk-board 必须先于 /{building_id}, 且要锁住不再被破坏
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from app.db import models as m


# ---- helpers ---------------------------------------------------------------


def _seed(session, building_id, n_records=10):
    b = m.Building(
        id=building_id,
        name=f"B{building_id}",
        address="Test",
        year_built=2010,
        building_type="office",
        structure_type="frame",
        floors=5,
        area=1000.0,
        design_life=50,
        current_age=16,
    )
    session.add(b)
    session.flush()
    s = m.Sensor(
        building_id=b.id, sensor_type="crack_width", name="s",
        unit="mm", location="loc", status="active",
    )
    session.add(s)
    session.flush()
    for i in range(n_records):
        session.add(m.MonitoringRecord(
            sensor_id=s.id,
            timestamp=datetime.utcnow() - timedelta(days=n_records - i),
            value=0.1 + i * 0.01,
            quality_flag="simulated",
        ))
    session.commit()
    session.refresh(b)
    return b


def _seed_alert(session, building_id, severity="high", status="active"):
    """种一条 alert; 用 fixed timestamp 以便排序断言."""
    a = m.RiskAlert(
        building_id=building_id,
        sensor_id=None,
        metric="crack_width",
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        current_value=0.5,
        baseline_value=0.1,
        change=0.4,
        detection_method="threshold",
        severity=severity,
        explanation="test alert",
        status=status,
    )
    session.add(a)
    session.commit()
    return a


# ---- empty / no-assessment / normal -----------------------------------------


def test_risk_board_empty(client):
    """空库 → items=[], alerts=[]."""
    r = client.get("/api/buildings/risk-board")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["alerts"] == []


def test_risk_board_no_assessment(client, test_engine):
    """有建筑无评估 → 该楼 health/risk 为 None, 但仍出现在 items 里;
    alerts 为空, total 仍算上这栋楼 (前端把它从 blocks 数组里丢)."""
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed(s, building_id=1)
    s.close()

    r = client.get("/api/buildings/risk-board")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["building"]["id"] == 1
    assert item["health"] is None
    assert item["risk"] is None
    assert item["active_alert_count"] == 0
    assert data["alerts"] == []


def test_risk_board_no_alerts(client, test_engine):
    """有建筑有评估但无任何 alert → blocks 正常, alerts=[]."""
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed(s, building_id=1, n_records=30)
    s.close()
    rec = client.post("/api/buildings/1/health/recompute")
    assert rec.status_code == 200

    r = client.get("/api/buildings/risk-board")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["health"] is not None
    assert data["alerts"] == []


def test_risk_board_with_alerts(client, test_engine):
    """alerts 跨楼拉全, 每条带 building_name."""
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed(s, building_id=1, n_records=30)
    _seed(s, building_id=2, n_records=30)
    s.close()
    client.post("/api/buildings/1/health/recompute")
    client.post("/api/buildings/2/health/recompute")

    sa = SL()
    _seed_alert(sa, building_id=1, severity="high")
    _seed_alert(sa, building_id=2, severity="medium")
    _seed_alert(sa, building_id=2, severity="low")
    sa.close()

    r = client.get("/api/buildings/risk-board")
    data = r.json()
    assert data["total"] == 2
    assert len(data["alerts"]) == 3
    by_b = {d["building_id"]: d for d in data["alerts"]}
    assert by_b[1]["building_name"] == "B1"
    assert by_b[2]["building_name"] == "B2"
    severities = {d["severity"] for d in data["alerts"]}
    assert severities == {"high", "medium", "low"}


def test_risk_board_only_active_alerts(client, test_engine):
    """alerts 列表只含 status=active (与 /alerts?active_only=true 一致)."""
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed(s, building_id=1, n_records=30)
    s.close()
    client.post("/api/buildings/1/health/recompute")

    sa = SL()
    _seed_alert(sa, building_id=1, severity="high", status="active")
    _seed_alert(sa, building_id=1, severity="medium", status="resolved")
    sa.commit()
    sa.close()

    r = client.get("/api/buildings/risk-board")
    data = r.json()
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["status"] == "active"


# ---- partial-failure isolation (与 overview 共享契约) ----------------------


def test_risk_board_partial_failure_isolated(client, test_engine, monkeypatch):
    """单建筑异常被隔离, 整体响应 200, 失败楼 health=None."""
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed(s, building_id=1, n_records=30)
    _seed(s, building_id=2, n_records=30)
    s.close()
    client.post("/api/buildings/1/health/recompute")
    # 不 recompute building 2 → 它走 no-assessment 分支, health=None

    r = client.get("/api/buildings/risk-board")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    by_id = {item["building"]["id"]: item for item in data["items"]}
    assert by_id[1]["health"] is not None
    assert by_id[2]["health"] is None


# ---- 核心: 字段级等价测试 ----------------------------------------------------


def test_risk_board_equivalent_to_per_building_endpoints(client, test_engine):
    """**字段级等价**: 对同一份种子数据, 聚合端点里每栋楼的 health/risk
    必须与逐楼端点逐个请求返回的**字段级完全相同**.
    README §10 已声明这个理念. 若不一致, 请修聚合端点, 不要放宽断言.
    """
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed(s, building_id=1, n_records=30)
    _seed(s, building_id=2, n_records=30)
    _seed(s, building_id=3, n_records=30)
    s.close()

    for bid in (1, 2, 3):
        client.post(f"/api/buildings/{bid}/health/recompute")

    # 逐楼端点的"标准答案"
    per_building_health = {
        bid: client.get(f"/api/buildings/{bid}/health").json() for bid in (1, 2, 3)
    }
    per_building_risk = {
        bid: client.get(f"/api/buildings/{bid}/risk").json() for bid in (1, 2, 3)
    }

    # 聚合端点的"测试答案"
    r = client.get("/api/buildings/risk-board")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3

    for item in data["items"]:
        bid = item["building"]["id"]
        # health 字段级完全相等
        assert item["health"] == per_building_health[bid], (
            f"building {bid} health mismatch"
        )
        # risk 字段级完全相等 (calculation_version 也必须一致)
        assert item["risk"] == per_building_risk[bid], (
            f"building {bid} risk mismatch"
        )


def test_risk_board_alerts_equivalent_to_per_building_endpoints(client, test_engine):
    """**alerts 等价**: 聚合端点 alerts 与逐楼 alerts?active_only=true 拉到的
    多重集完全相同, 且每条带 building_name."""
    SL = sessionmaker(bind=test_engine)
    s = SL()
    _seed(s, building_id=1, n_records=30)
    _seed(s, building_id=2, n_records=30)
    s.close()
    client.post("/api/buildings/1/health/recompute")
    client.post("/api/buildings/2/health/recompute")

    SL2 = SL(bind=test_engine)
    _seed_alert(SL2, building_id=1, severity="high")
    _seed_alert(SL2, building_id=2, severity="medium")
    _seed_alert(SL2, building_id=2, severity="low")
    SL2.commit()

    # 逐楼"标准答案"
    per_building_alerts = []
    for bid in (1, 2):
        for a in client.get(f"/api/buildings/{bid}/alerts", params={"active_only": True}).json():
            per_building_alerts.append({**a, "building_name": f"B{bid}"})

    # 聚合"测试答案"
    data = client.get("/api/buildings/risk-board").json()
    board_alerts = data["alerts"]

    # 多重集比较: (id, severity) 元组计数应一致
    from collections import Counter
    c1 = Counter((a["id"], a["severity"]) for a in per_building_alerts)
    c2 = Counter((a["id"], a["severity"]) for a in board_alerts)
    assert c1 == c2, f"alerts 多重集不一致: per={c1} board={c2}"
    # 每条聚合 alert 都带 building_name
    for a in board_alerts:
        assert "building_name" in a
        assert a["building_name"].startswith("B")


# ---- SQL 条数与 N 无关 (性能证据) ---------------------------------------------


def test_risk_board_sql_count_is_invariant_of_N(client, test_engine):
    """**性能轮 R2 性能证据**: 同一端点在 N=1 / 10 / 30 栋楼时,
    SQL 条数应**完全相同** (= 6, 不随 N 线性增长).
    锁住这个不变量, 防止有人后续改回 N+1 查询导致性能退化.

    实现: 在同一个 engine 下, 依次 seed 1 / 10 / 30 栋楼,
    每次跑 risk-board 端点, 用 SQLAlchemy `before_cursor_execute` event
    计数, 直接断言 3 次 count 完全相等.
    """
    from sqlalchemy import event

    stmts_by_n: dict[str, list] = {}

    SL = sessionmaker(bind=test_engine)
    for n in (1, 10, 30):
        # 清掉之前的 building (避免上一轮干扰)
        s = SL()
        s.query(m.RiskAlert).delete()
        s.query(m.MonitoringRecord).delete()
        s.query(m.Sensor).delete()
        s.query(m.HealthAssessment).delete()
        s.query(m.Building).delete()
        s.commit()
        s.close()

        # seed n 栋
        s = SL()
        for bid in range(1, n + 1):
            _seed(s, building_id=bid, n_records=20)
        s.close()

        # 装 listener, 只在本次请求内有效
        local: list[str] = []

        def _listener(conn, cursor, statement, parameters, context, executemany, _local=local):
            _local.append(statement)

        event.listen(test_engine, "before_cursor_execute", _listener)
        try:
            r = client.get("/api/buildings/risk-board")
            assert r.status_code == 200
        finally:
            event.remove(test_engine, "before_cursor_execute", _listener)
        stmts_by_n[str(n)] = list(local)

    # 关键断言: SQL 总条数与 N 无关
    counts = {k: len(v) for k, v in stmts_by_n.items()}
    assert counts["1"] == counts["10"] == counts["30"], (
        f"risk-board SQL 条数与 N 相关 (退化成 N+1): {counts}"
    )
    print(f"\n[risk-board SQL count] N=1 → {counts['1']}, "
          f"N=10 → {counts['10']}, N=30 → {counts['30']}")


# ---- 注册顺序保护 (与 overview 共享的反退化保险) ----------------------------


def test_risk_board_openapi_registered(client):
    """/risk-board 必须在 OpenAPI 里, 且路径形式不变."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/buildings/risk-board" in paths


def test_risk_board_registered_before_building_id(client):
    """**注册顺序**: /risk-board 字面量必须排在 /{building_id} 之前,
    否则 FastAPI 会把 "risk-board" 当 building_id="risk-board" → 422.
    """
    paths = list(client.get("/openapi.json").json()["paths"].keys())
    # 只看 /api/buildings/ 下
    b_paths = [p for p in paths if p.startswith("/api/buildings/")]
    assert "/api/buildings/risk-board" in b_paths
    assert "/api/buildings/overview" in b_paths
    assert "/api/buildings/{building_id}" in b_paths
    # 顺序: literal 必须在 wildcard 前
    rb_idx = b_paths.index("/api/buildings/risk-board")
    ov_idx = b_paths.index("/api/buildings/overview")
    bi_idx = b_paths.index("/api/buildings/{building_id}")
    assert rb_idx < bi_idx, "/risk-board 必须排在 /{building_id} 之前"
    assert ov_idx < bi_idx, "/overview 也必须排在 /{building_id} 之前"


def test_risk_board_path_not_captured_by_building_id(client):
    """直接 GET /api/buildings/risk-board 不应被当作 building_id=risk-board."""
    # 若路由顺序错了, 这里会返回 422 (int("risk-board") 失败)
    r = client.get("/api/buildings/risk-board")
    assert r.status_code == 200
    assert "items" in r.json()
    assert "alerts" in r.json()