from sqlalchemy import event


def test_create_and_list(client):
    res = client.post("/tasks", json={"title": "테스트 할 일", "tags": ["개인", "긴급"]})
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "테스트 할 일"
    assert {t["name"] for t in body["tags"]} == {"개인", "긴급"}

    res = client.get("/tasks")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 1
    assert tasks[0]["tags"]


def test_list_tasks_query_count_does_not_grow(client, db_session):
    for i in range(3):
        res = client.post("/tasks", json={"title": f"할 일 {i}", "tags": ["개인", "긴급"]})
        assert res.status_code == 201

    # 생성 단계에서 로딩된 객체가 identity map에 남아 있으면 쿼리 수가 줄어 보입니다.
    db_session.expire_all()

    statements: list[str] = []

    def count(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", count)
    try:
        res = client.get("/tasks")
    finally:
        event.remove(engine, "before_cursor_execute", count)

    assert res.status_code == 200
    assert len(res.json()) == 3
    # tasks 1회 + tags 1회. 할 일 개수와 무관해야 합니다.
    assert len(statements) == 2
