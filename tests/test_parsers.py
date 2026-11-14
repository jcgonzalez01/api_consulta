from pathlib import Path

from app.dgii_client import parse_cedula, parse_razon_social, parse_rnc

FX = Path(__file__).parent / "fixtures"


def leer(nombre: str) -> str:
    return (FX / nombre).read_text(encoding="utf-8")


def test_rnc_encontrado():
    d = parse_rnc(leer("rnc_encontrado.html"))
    assert d["cedula_rnc"] == "401-00755-1"
    assert d["nombre_razon_social"] == "BANCO CENTRAL DE LA REPUBLICA DOMINICANA"
    assert d["estado"] == "ACTIVO"
    assert d["regimen_de_pagos"] == "NORMAL"
    assert d["facturador_electronico"] == "SI"


def test_rnc_no_encontrado():
    assert parse_rnc(leer("rnc_no_encontrado.html")) is None


def test_razon_social():
    r = parse_razon_social(leer("razon_social.html"))
    assert len(r) >= 1
    assert r[0]["cedula_rnc"] == "401-00755-1"
    assert r[0]["estado"] == "ACTIVO"


def test_cedula_no_encontrada():
    assert parse_cedula(leer("cedula_no_encontrada.html")) is None


CEDULA_ENCONTRADA = """
<html><body><div id="cphMain_divBusqueda"><div id="cphMain_divResultsContainer">
<table class="table table-striped detailview" id="cphMain_dvResultadoCedula">
<tr><td style="font-weight:bold;">Nombre</td><td>PERSONA DE PRUEBA</td></tr>
<tr><td style="font-weight:bold;">Estado</td><td>ACTIVO</td></tr>
<tr><td style="font-weight:bold;">Tipo</td><td> FISICO </td></tr>
<tr><td style="font-weight:bold;">RNC o C&#233;dula</td><td>000-0000000-0</td></tr>
<tr><td style="font-weight:bold;">Marca</td><td>Participacion en Empresas</td></tr>
</table></div></div></body></html>
"""


def test_cedula_encontrada():
    d = parse_cedula(CEDULA_ENCONTRADA)
    assert d == {
        "nombre": "PERSONA DE PRUEBA",
        "estado": "ACTIVO",
        "tipo": "FISICO",
        "rnc_o_cedula": "000-0000000-0",
        "marca": "Participacion en Empresas",
    }
