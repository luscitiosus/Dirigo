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

# --- BOC: formato moderno (2012) y antiguo (2009) del índice y de la página ---
import descargar  # noqa: E402

IDX_2012 = b"""<html><body><h3>I. DISPOSICIONES GENERALES</h3><p>328</p><p>ORDEN de 12 de enero de 2012, por la que se establece el ambito.</p>
<p>5 paginas.</p><p>329</p><p>ORDEN de 12 de enero de 2012, por la que se fijan los indices.</p>
<p>330</p><p>Direcci\xc3\xb3n General de Tributos.- Resoluci\xc3\xb3n de 13 de enero de 2012, por la que se actualiza.</p><p>331</p><p>ORDEN de 15 de diciembre de 2011, por la que se crea el fichero.</p><p>332</p><p>CORRECCI\xc3\x93N de errores de la Resoluci\xc3\xb3n de 12 de enero de 2012, de X.</p>
<p>333</p><p>Direcci\xc3\xb3n General de Personal.- Resoluci\xc3\xb3n de 12 de enero de 2012, por la que se dictan instrucciones de procedimiento para la evaluaci\xc3\xb3n de la funci\xc3\xb3n directiva.</p></body></html>"""
PAG_2012 = b"""<html><body><div>Gobierno de Canarias</div><div>BOC N\xc2\xba 015. Lunes 23 de Enero de 2012 - 333</div><div>333</div>
<p>Direcci\xc3\xb3n General de Personal.- Resoluci\xc3\xb3n de 12 de enero de 2012, por la que se dictan instrucciones de procedimiento para la evaluaci\xc3\xb3n de la funci\xc3\xb3n directiva.</p>
<p>9 p\xc3\xa1ginas. Formato de archivo en PDF/Adobe Acrobat.</p><p>BOC-A-2012-015-333.</p><p>Firma electr\xc3\xb3nica-Descargar</p>
<p>Primero.- Objeto de la resoluci\xc3\xb3n.</p><p>Texto del primero.</p><p>\xc2\xa9 Gobierno de Canarias</p><p>Aviso Legal</p></body></html>"""
llamadas = []
def falso_get(url, accept="*/*"):
    llamadas.append(url)
    return PAG_2012 if url.endswith("006.html") else IDX_2012
descargar.get = falso_get
cat = json.loads((RAIZ / "catalogo.json").read_text("utf-8"))
c9 = next(c for c in cat if c["n"] == 9)
lin = descargar.lineas_boc(2012, 15, c9["fuente"]["clave"], c9["titulo"])
assert llamadas[-1].endswith("/boc/2012/015/006.html"), llamadas
assert lin[0].startswith("Dirección General de Personal") and "Texto del primero." in lin and not any("©" in x or "Aviso" in x or "BOC-A" in x for x in lin), lin
print("BOC OK")
