# Hadrianus Muratellensis me fecit
# Licencia: CC BY-NC-SA 4.0
"""Descarga los textos oficiales (BOE y BOC) y genera normas_NN.json.

Uso:  python descargar.py [n ...]      (sin argumentos: las 17 normas)
Es tolerante: si una norma falla, lo avisa y sigue. Salida 0 siempre (apto para build).
"""
import datetime
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
from corpus import dividir_preceptos, normalizar  # noqa: E402

UA = {"User-Agent": "Dirigo/1.0 (conector MCP de normativa educativa)"}


def get(url: str, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(url, headers={**UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


# ---------- BOE ----------
def texto_xml(elem) -> str:
    return re.sub(r"\s+", " ", "".join(elem.itertext())).strip()


def lineas_boe(id_: str, consolidado: bool) -> list[str]:
    if consolidado:
        try:
            raiz = ET.fromstring(get(f"https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{id_}/texto", "application/xml"))
            lin = []
            for b in raiz.iter("bloque"):
                vers = list(b.findall("version"))
                fuente = vers[-1] if vers else b  # última versión = vigente
                lin += [texto_xml(p) for p in fuente.iter("p")]
            if len(lin) > 5:
                return lin
        except Exception as e:  # noqa: BLE001
            print(f"   consolidado falló ({e}); pruebo texto original")
    raiz = ET.fromstring(get(f"https://www.boe.es/diario_boe/xml.php?id={id_}", "application/xml"))
    texto = raiz.find(".//texto")
    return [texto_xml(p) for p in (texto if texto is not None else raiz).iter("p")]


# ---------- BOC ----------
class _Texto(HTMLParser):
    BLOQUES = {"p", "div", "li", "h1", "h2", "h3", "h4", "tr", "br", "table", "ul"}

    def __init__(self):
        super().__init__()
        self.lin, self.cur, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag in self.BLOQUES:
            self._cut()

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        if tag in self.BLOQUES:
            self._cut()

    def handle_data(self, d):
        if not self.skip:
            self.cur.append(d)

    def _cut(self):
        t = re.sub(r"\s+", " ", "".join(self.cur)).strip()
        if t:
            self.lin.append(t)
        self.cur = []


def html_lineas(html: bytes) -> list[str]:
    p = _Texto()
    p.feed(html.decode("utf-8", "replace"))
    p._cut()
    return p.lin


def base_boc(anio: int, bol: int) -> str:
    return f"https://www.gobiernodecanarias.org/boc/{anio}/{bol:03d}/"


def posicion_boc(anio: int, bol: int, clave: str) -> int:
    """Posición (1..n) de la disposición dentro del boletín, localizada en el índice."""
    lin = html_lineas(get(base_boc(anio, bol)))
    pos = 0
    for ln in lin:
        if re.match(r"^\d{1,5}\s+\S", ln) and ln.rstrip().endswith("[PDF]"):
            pos += 1
            titulo = normalizar(re.sub(r"^\d+\s+", "", ln))
            if titulo.startswith(normalizar(clave)):
                return pos
    raise LookupError(f"'{clave}' no aparece en el índice del BOC {anio}/{bol}")


def lineas_boc(anio: int, bol: int, clave: str) -> list[str]:
    pos = posicion_boc(anio, bol, clave)
    for p in (pos, pos + 1, pos - 1):  # por si el índice y la numeración difieren
        if p < 1:
            continue
        lin = html_lineas(get(f"{base_boc(anio, bol)}{p:03d}.html"))
        ini = next((i for i, l in enumerate(lin) if re.match(r"^\d+\s+-\s+\S", l) and normalizar(l).split(" - ", 1)[-1].startswith(normalizar(clave))), None)
        if ini is None:
            continue
        cuerpo = lin[ini + 1:]
        if cuerpo and cuerpo[0].lower().startswith("descargar en formato"):
            cuerpo = cuerpo[1:]
        fin = next((i for i, l in enumerate(cuerpo) if normalizar(l) in ("anterior", "siguiente", "volver", "arriba") or normalizar(l).startswith("gobierno de canarias")), len(cuerpo))
        return [lin[ini]] + cuerpo[:fin]
    raise LookupError(f"No pude cargar la página de '{clave}' ({anio}/{bol})")


# ---------- manual ----------
def lineas_manual(n: int) -> list[str]:
    t = RAIZ / f"manual_{n}.txt"
    if t.exists():
        return t.read_text("utf-8").splitlines()
    pdf = RAIZ / f"manual_{n}.pdf"
    if pdf.exists():
        import subprocess
        return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout.splitlines()
    raise FileNotFoundError(f"falta manual_{n}.txt (o .pdf)")


def main():
    cat = json.loads((RAIZ / "catalogo.json").read_text("utf-8"))
    pedidas = {int(a) for a in sys.argv[1:]}
    ok = 0
    for c in cat:
        if pedidas and c["n"] not in pedidas:
            continue
        f, print_id = c["fuente"], f"{c['n']:02d} {c['corto']}"
        try:
            if f["tipo"] == "boe":
                lin = lineas_boe(f["id"], f.get("consolidado", False))
            elif f["tipo"] == "boc":
                lin = lineas_boc(f["anio"], f["boletin"], f["clave"])
            else:
                lin = lineas_manual(c["n"])
            prec = dividir_preceptos(lin)
            if sum(len(p["texto"]) for p in prec) < 300:
                raise ValueError("texto sospechosamente corto")
            (RAIZ / f"normas_{c['n']:02d}.json").write_text(
                json.dumps({"n": c["n"], "actualizado": datetime.date.today().isoformat(), "preceptos": prec}, ensure_ascii=False), "utf-8")
            print(f"OK   {print_id}: {len(prec)} preceptos")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"FALLO {print_id}: {e}")
    print(f"\n{ok} normas descargadas")


if __name__ == "__main__":
    main()
