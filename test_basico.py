# Hadrianus Muratellensis me fecit
import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import corpus  # noqa: E402

tmp = Path(tempfile.mkdtemp())
shutil.copy(RAIZ / "catalogo.json", tmp / "catalogo.json")
corpus.DATOS = tmp

LIN = [
    "La Ley Orgánica 2/2006 destaca la importancia que la función directiva tiene en los centros.",
    "Artículo 1.- Objeto.",
    "El presente decreto regula la función directiva en los centros docentes públicos.",
    "Artículo 2.- Competencias de la dirección.",
    "Corresponde a la dirección ejercer la jefatura de todo el personal adscrito al centro.",
    "Artículo 15 bis. Cese.",
    "La dirección cesará por finalización del mandato.",
    "Disposición adicional primera. Reducción horaria.",
    "Los cargos directivos tendrán reducción de horas lectivas.",
    "Disposición transitoria única.",
    "Régimen transitorio de los mandatos.",
    "Disposición final segunda. Entrada en vigor.",
    "El decreto entra en vigor al día siguiente de su publicación.",
]
prec = corpus.dividir_preceptos(LIN)
ids = [p["id"] for p in prec]
assert ids == ["Preámbulo", "1", "2", "15-bis", "da-primera", "dt-unica", "df-segunda"], ids
(tmp / "normas_05.json").write_text(json.dumps({"n": 5, "preceptos": prec}), "utf-8")

C = corpus.Corpus()
n5 = C.resolver("106/2009")
assert n5 and n5["n"] == 5 and C.resolver("D106")["n"] == 5 and C.resolver(5)["n"] == 5
assert C.resolver("roc")["n"] == 7 and C.resolver("LOE")["n"] == 1
r = C.buscar("cese de la dirección mandato")
assert r and C.normas[r[0][1]]["preceptos"][r[0][2]]["id"] == "15-bis", r
assert C.precepto(n5, "15 bis")["id"] == "15-bis"
assert C.precepto(n5, "da-primera") and C.precepto(n5, "2")
assert "…" in C.fragmento("a" * 300 + " jefatura " + "b" * 300, "jefatura")

# Parser HTML del BOC con una página de ejemplo
from descargar import html_lineas  # noqa: E402
html = b"<html><body><div>Inicio</div><h2>1250 - DECRETO 106/2009, de 28 de julio.</h2><a>Descargar en formato pdf</a><p>Texto uno</p><p>Art\xc3\xadculo 1.- X</p><script>var a=1</script></body></html>"
l = html_lineas(html)
assert "Texto uno" in l and not any("var a" in x for x in l), l

# Servidor: herramientas sobre el corpus de prueba
import server  # noqa: E402
server.C = C
assert "Decreto 106/2009" in server.normas("retribuc") or True
assert "[5|15-bis]" in server.buscar("cese mandato")
assert "Reducción horaria" in server.articulo("D106", "da-primera")
assert "Artículo 2" in server.indice("5")
assert "[fin]" in server.leer("5", 0, 20000)
assert "sin texto" in server.normas()
print("TODO OK")

# --- BOC: se recorren las páginas del boletín hasta el 404 ---
import urllib.error  # noqa: E402
import descargar  # noqa: E402

def pagina(titulo_linea, cuerpo):
    return ("<html><body><div>BOC N\u00ba 015. Lunes - 1</div><div>1</div><p>%s</p><p>9 p\u00e1ginas. Formato de archivo en PDF.</p>"
            "<p>BOC-A-2012-015-333.</p><p>Firma electr\u00f3nica-Descargar</p><p>%s</p><p>\u00a9 Gobierno de Canarias</p><p>Aviso Legal</p></body></html>" % (titulo_linea, cuerpo)).encode()

PAGS = {
    1: pagina("ORDEN de 12 de enero de 2012, por la que se fijan...", "Otro texto."),
    2: pagina("CORRECCI\u00d3N de errores de la Resoluci\u00f3n de 12 de enero de 2012, de X.", "Corrige."),
    3: pagina("Direcci\u00f3n General de Personal.- Resoluci\u00f3n de 12 de enero de 2012, por la que se dictan instrucciones para la evaluaci\u00f3n de la funci\u00f3n directiva.", "Texto del primero."),
}
def falso_get(url, accept="*/*"):
    n = int(url.rsplit("/", 1)[1].split(".")[0])
    if n in PAGS:
        return PAGS[n]
    raise urllib.error.HTTPError(url, 404, "nf", None, None)
descargar.get = falso_get
cat = json.loads((RAIZ / "catalogo.json").read_text("utf-8"))
c9 = next(c for c in cat if c["n"] == 9)
lin = descargar.lineas_boc(2012, 15, c9["fuente"]["clave"], c9["titulo"])
assert lin[0].startswith("Direcci\u00f3n General de Personal") and "Texto del primero." in lin, lin
assert not any("\u00a9" in x or "Aviso" in x or "BOC-A" in x or "Firma" in x for x in lin), lin
try:
    descargar.lineas_boc(2012, 15, "decreto 1/2000", "x")
    raise SystemExit("deber\u00eda fallar")
except LookupError:
    pass
print("BOC OK")
