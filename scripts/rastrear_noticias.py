#!/usr/bin/env python3
"""Rastreador de aperturas y cierres de agencias automotrices en México.

Consulta Google News (RSS) con búsquedas en español, clasifica cada titular
como apertura / cierre / cambio de distribuidor, intenta extraer el grupo
automotriz y la marca, y agrega los resultados nuevos a
data/noticias_detectadas.csv (sin duplicados).

Uso:
    python3 scripts/rastrear_noticias.py            # últimos 31 días
    python3 scripts/rastrear_noticias.py --dias 90

Solo usa la biblioteca estándar de Python. Los resultados son candidatos:
revísalos y pasa los confirmados a data/movimientos.csv.
"""
import argparse
import csv
import email.utils
import html
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "noticias_detectadas.csv"
CAMPOS = ["fecha", "grupo", "tipo", "marca", "titular", "medio", "url"]

CONSULTAS = [
    '"inaugura agencia" autos',
    '"nueva agencia" grupo automotriz',
    '"abre agencia" autos',
    '"inaugura concesionaria"',
    '"nueva distribuidora" autos',
    '"cierra agencia" autos',
    '"cierre de agencia" automotriz',
    '"cierran agencia" autos',
    '"cambia de distribuidor" autos',
    '"grupo automotriz" apertura agencia',
    '"grupo automotriz" cierre agencias',
    'AMDA agencias cierre',
]

MARCAS = [
    "Audi", "BAIC", "Bestune", "BMW", "BYD", "Cadillac", "Changan", "Chevrolet",
    "Chirey", "Cupra", "Dodge", "Dongfeng", "Exeed", "Ford", "Foton", "GAC",
    "Geely", "GMC", "GWM", "Great Wall", "Haval", "Honda", "Hyundai", "Infiniti",
    "Isuzu", "JAC", "Jaecoo", "Jeep", "Jetour", "Kia", "Land Rover", "Leapmotor",
    "Lexus", "Lincoln", "Mazda", "Mercedes-Benz", "MG", "Mini", "Mitsubishi",
    "Nissan", "Omoda", "Peugeot", "Porsche", "RAM", "Renault", "Seat", "Subaru",
    "Suzuki", "SEV", "Tesla", "Toyota", "Volkswagen", "Volvo", "Zeekr",
]

PATRONES_TIPO = [
    ("cambio_distribuidor", re.compile(r"cambi\w* de (distribuidor|concesionari)|nuevo distribuidor|deja de (operar|representar)", re.I)),
    ("cierre", re.compile(r"\bcierr\w*|\bcerr(ó|aron|ar|ará|arán)\b|clausur\w*|baja la cortina|se despide|adiós a", re.I)),
    ("apertura", re.compile(r"inaugur\w*|\babre\b|\babren\b|apertura|nueva (agencia|concesionaria|distribuidora|sucursal)|llega a|expande|amplía|suma", re.I)),
]

PATRON_SECTOR = re.compile(r"agencia|concesionari|distribuidor|grupo automotriz|dealer|showroom", re.I)
PATRON_GRUPO = re.compile(r"\bGrupo\s+((?:[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&\.-]+)(?:\s+(?:de\s+)?[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&\.-]+){0,2})")
EXCLUIR_GRUPO = {"Financiero", "Modelo", "Bimbo", "México", "Salinas", "Carso", "Elektra", "Soriana"}


def rss_url(consulta: str) -> str:
    q = urllib.parse.quote(consulta)
    return f"https://news.google.com/rss/search?q={q}&hl=es-419&gl=MX&ceid=MX:es-419"


def descargar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "rastreador-agencias/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def clasificar(texto: str) -> str | None:
    for tipo, patron in PATRONES_TIPO:
        if patron.search(texto):
            return tipo
    return None


def extraer_grupo(texto: str) -> str:
    for m in PATRON_GRUPO.finditer(texto):
        nombre = m.group(1).strip(" .-")
        if nombre.split()[0] not in EXCLUIR_GRUPO:
            return f"Grupo {nombre}"
    return ""


def extraer_marca(texto: str) -> str:
    encontradas = [m for m in MARCAS if re.search(rf"\b{re.escape(m)}\b", texto)]
    return "; ".join(encontradas)


def leer_existentes() -> set[str]:
    if not SALIDA.exists():
        return set()
    with SALIDA.open(newline="", encoding="utf-8") as f:
        return {fila["url"] for fila in csv.DictReader(f)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=31, help="ventana de días hacia atrás")
    args = ap.parse_args()
    limite = datetime.now(timezone.utc) - timedelta(days=args.dias)

    vistos = leer_existentes()
    titulares_vistos: set[str] = set()
    nuevas = []
    for consulta in CONSULTAS:
        try:
            raiz = ET.fromstring(descargar(rss_url(consulta)))
        except Exception as e:  # red, XML inválido, etc.
            print(f"[aviso] {consulta!r}: {e}", file=sys.stderr)
            continue
        for item in raiz.iter("item"):
            titulo = html.unescape(item.findtext("title", ""))
            url = item.findtext("link", "")
            medio = item.findtext("source", "")
            try:
                fecha = email.utils.parsedate_to_datetime(item.findtext("pubDate", ""))
            except (TypeError, ValueError):
                continue
            if fecha < limite or url in vistos:
                continue
            clave = re.sub(r"\W+", "", titulo.lower())[:80]
            if clave in titulares_vistos:
                continue
            if not PATRON_SECTOR.search(titulo):
                continue
            tipo = clasificar(titulo)
            if not tipo:
                continue
            titulares_vistos.add(clave)
            vistos.add(url)
            nuevas.append({
                "fecha": fecha.date().isoformat(),
                "grupo": extraer_grupo(titulo),
                "tipo": tipo,
                "marca": extraer_marca(titulo),
                "titular": titulo,
                "medio": medio,
                "url": url,
            })

    nuevas.sort(key=lambda f: f["fecha"])
    escribir_encabezado = not SALIDA.exists()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if escribir_encabezado:
            w.writeheader()
        w.writerows(nuevas)

    print(f"{len(nuevas)} noticias nuevas agregadas a {SALIDA.relative_to(RAIZ)}")
    for n in nuevas:
        print(f"  {n['fecha']} [{n['tipo']}] {n['grupo'] or '¿grupo?'} | {n['titular']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
