"""Cliente para las consultas web de la DGII (ASP.NET WebForms).

Cada consulta hace:
  1. GET de la página para obtener los campos ocultos (__VIEWSTATE, etc.) y cookies.
  2. POST con esos campos + el valor buscado + el botón de búsqueda.
  3. Parseo del HTML de respuesta.
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://dgii.gov.do/app/WebApps/ConsultasWeb2/ConsultasWeb/consultas"
URL_CIUDADANOS = f"{BASE_URL}/ciudadanos.aspx"
URL_RNC = f"{BASE_URL}/rnc.aspx"

# Nombres de los controles del formulario (centralizados por si la DGII los cambia).
CAMPO_CEDULA = "ctl00$cphMain$txtCedula"
BOTON_CEDULA = "ctl00$cphMain$btnBuscarCedula"
CAMPO_RNC = "ctl00$cphMain$txtRNCCedula"
BOTON_RNC = "ctl00$cphMain$btnBuscarPorRNC"
CAMPO_RAZON_SOCIAL = "ctl00$cphMain$txtRazonSocial"
BOTON_RAZON_SOCIAL = "ctl00$cphMain$btnBuscarPorRazonSocial"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) api_consulta/1.0"


class DGIIError(Exception):
    """La DGII no respondió o respondió algo inesperado."""


def _texto(el) -> str:
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def _clave(label: str) -> str:
    """'Régimen de pagos' -> 'regimen_de_pagos'."""
    tabla = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    s = label.translate(tabla).lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def campos_ocultos(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    return {i["name"]: i.get("value", "") for i in soup.select("input[type=hidden][name]")}


def parse_tabla_detalle(soup: BeautifulSoup, tabla_id: str | None = None) -> dict[str, str]:
    """Tablas tipo DetailsView: cada fila es <td>Etiqueta</td><td>Valor</td>."""
    contenedor = soup.find(id="cphMain_divBusqueda") or soup
    tablas = [contenedor.find(id=tabla_id)] if tabla_id else contenedor.find_all("table")
    datos: dict[str, str] = {}
    for tabla in tablas:
        if not tabla:
            continue
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all(["td", "th"], recursive=False)
            if len(celdas) == 2 and not fila.find("th"):
                datos[_clave(_texto(celdas[0]))] = _texto(celdas[1])
    return datos


def parse_tabla_lista(soup: BeautifulSoup, tabla_id: str) -> list[dict[str, str]]:
    """Tablas tipo GridView: fila de encabezado <th> y filas de datos <td>."""
    tabla = soup.find(id=tabla_id)
    if not tabla:
        return []
    filas = tabla.find_all("tr")
    if not filas:
        return []
    encabezados = [_clave(_texto(th)) for th in filas[0].find_all("th")]
    resultado = []
    for fila in filas[1:]:
        celdas = fila.find_all("td")
        if celdas:
            resultado.append({k: _texto(c) for k, c in zip(encabezados, celdas)})
    return resultado


def parse_rnc(html: str) -> dict[str, str] | None:
    soup = BeautifulSoup(html, "lxml")
    return parse_tabla_detalle(soup, "cphMain_dvDatosContribuyentes") or None


def parse_razon_social(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    return parse_tabla_lista(soup, "cphMain_gvBuscRazonSocial")


def parse_cedula(html: str) -> dict[str, str] | None:
    soup = BeautifulSoup(html, "lxml")
    if soup.find(id="cphMain_divAlertDanger"):
        return None
    datos = parse_tabla_detalle(soup, "cphMain_dvResultadoCedula")
    # Respaldo: si la DGII cambia el id de la tabla, leer cualquier tabla del resultado.
    return datos or parse_tabla_detalle(soup) or None


class _Cache:
    def __init__(self, ttl: float):
        self.ttl = ttl
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str):
        item = self._data.get(key)
        if item and time.monotonic() - item[0] < self.ttl:
            return item[1]
        self._data.pop(key, None)
        return None

    def set(self, key: str, value: Any) -> None:
        if len(self._data) > 5000:
            self._data.clear()
        self._data[key] = (time.monotonic(), value)


class DGIIClient:
    def __init__(self, timeout: float = 20.0, cache_ttl: float = 600.0, reintentos: int = 1):
        self.timeout = timeout
        self.reintentos = reintentos
        self.cache = _Cache(cache_ttl)

    async def _postback(self, url: str, campos: dict[str, str]) -> str:
        ultimo_error: Exception | None = None
        for _ in range(self.reintentos + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    headers={"User-Agent": USER_AGENT},
                    follow_redirects=True,
                ) as http:
                    r = await http.get(url)
                    r.raise_for_status()
                    data = campos_ocultos(r.text)
                    data.update(campos)
                    r = await http.post(url, data=data)
                    r.raise_for_status()
                    return r.text
            except httpx.HTTPError as e:
                ultimo_error = e
        raise DGIIError(f"No se pudo consultar la DGII: {ultimo_error}")

    async def _cached(self, key: str, url: str, campos: dict[str, str], parser):
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        resultado = parser(await self._postback(url, campos))
        self.cache.set(key, resultado)
        return resultado

    async def consultar_rnc(self, numero: str) -> dict[str, str] | None:
        return await self._cached(
            f"rnc:{numero}", URL_RNC,
            {CAMPO_RNC: numero, BOTON_RNC: "BUSCAR"}, parse_rnc,
        )

    async def consultar_cedula(self, numero: str) -> dict[str, str] | None:
        return await self._cached(
            f"cedula:{numero}", URL_CIUDADANOS,
            {CAMPO_CEDULA: numero, BOTON_CEDULA: "Buscar"}, parse_cedula,
        )

    async def buscar_razon_social(self, nombre: str) -> list[dict[str, str]]:
        return await self._cached(
            f"razon:{nombre.upper()}", URL_RNC,
            {CAMPO_RAZON_SOCIAL: nombre, BOTON_RAZON_SOCIAL: "BUSCAR",
             "ctl00$cphMain$hidActiveTab": "razonsocial"},
            parse_razon_social,
        )
