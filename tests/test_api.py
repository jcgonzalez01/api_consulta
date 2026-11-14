from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_cedula_formato_invalido():
    assert client.get("/cedula/123").status_code == 422


def test_rnc_formato_invalido():
    assert client.get("/rnc/12ab").status_code == 422


def test_rnc_con_guiones(monkeypatch):
    async def falso(num):
        assert num == "401007551"
        return {"estado": "ACTIVO"}

    monkeypatch.setattr(main.cliente, "consultar_rnc", falso)
    r = client.get("/rnc/401-00755-1")
    assert r.status_code == 200
    assert r.json()["datos"]["estado"] == "ACTIVO"


def test_cedula_no_encontrada(monkeypatch):
    async def falso(num):
        return None

    monkeypatch.setattr(main.cliente, "consultar_cedula", falso)
    assert client.get("/cedula/001-0000000-1").status_code == 404


def test_api_key_requerida(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "secreta")

    async def falso(num):
        return {"estado": "ACTIVO"}

    monkeypatch.setattr(main.cliente, "consultar_rnc", falso)
    assert client.get("/rnc/401007551").status_code == 401
    assert client.get("/rnc/401007551", headers={"X-API-Key": "mala"}).status_code == 401
    assert client.get("/rnc/401007551", headers={"X-API-Key": "secreta"}).status_code == 200
    assert client.get("/health").status_code == 200
