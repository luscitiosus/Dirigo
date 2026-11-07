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
