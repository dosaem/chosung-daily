def test_index_page_renders(client):
    res = client.get("/")

    assert res.status_code == 200
    assert "오늘의 초성".encode() in res.data


def test_static_js_is_served(client):
    res = client.get("/static/app.js")

    assert res.status_code == 200
    assert b"API_BASE" in res.data
