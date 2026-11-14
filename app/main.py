"""API de consulta de Cédula y RNC contra la DGII.

Ejecutar:  uvicorn app.main:app --reload
Docs:      http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import re

from fastapi import FastAPI, HTTPException, Path, Query

from app.dgii_client import DGIIClient, DGIIError

app = FastAPI(
    title="API Consulta DGII",
    description="Consulta de Cédula y RNC usando las consultas web públicas de la DGII.",
    version="1.0.0",
)

cliente = DGIIClient()


def solo_digitos(valor: str) -> str:
    return re.sub(r"[\s-]", "", valor)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/cedula/{numero}")
async def consultar_cedula(numero: str = Path(..., description="Cédula, 11 dígitos (guiones opcionales)")):
    num = solo_digitos(numero)
    if not re.fullmatch(r"\d{11}", num):
        raise HTTPException(422, "La cédula debe tener 11 dígitos.")
    try:
        datos = await cliente.consultar_cedula(num)
    except DGIIError as e:
        raise HTTPException(502, str(e))
    if not datos:
        raise HTTPException(404, "La cédula consultada no se encuentra inscrita en la DGII.")
    return {"cedula": num, "datos": datos}


@app.get("/rnc/buscar")
async def buscar_por_nombre(nombre: str = Query(..., min_length=4, description="Nombre o razón social")):
    try:
        resultados = await cliente.buscar_razon_social(nombre.strip())
    except DGIIError as e:
        raise HTTPException(502, str(e))
    return {"nombre": nombre, "total": len(resultados), "resultados": resultados}


@app.get("/rnc/{numero}")
async def consultar_rnc(numero: str = Path(..., description="RNC (9 dígitos) o cédula (11 dígitos)")):
    num = solo_digitos(numero)
    if not re.fullmatch(r"\d{9}|\d{11}", num):
        raise HTTPException(422, "El RNC debe tener 9 dígitos (o 11 si es cédula).")
    try:
        datos = await cliente.consultar_rnc(num)
    except DGIIError as e:
        raise HTTPException(502, str(e))
    if not datos:
        raise HTTPException(404, "El RNC/Cédula consultado no se encuentra inscrito como contribuyente.")
    return {"rnc": num, "datos": datos}
