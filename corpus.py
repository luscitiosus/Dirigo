# Hadrianus Muratellensis me fecit
# Licencia: CC BY-NC-SA 4.0
"""Carga del corpus, división en preceptos y búsqueda BM25 (sin dependencias)."""
import json
import math
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).parent
DATOS = RAIZ

# Encabezados de precepto: "Artículo 12.", "Disposición adicional primera.", etc.
RE_PRECEPTO = re.compile(
    r"^(Art[ií]culo\s+\d+[\sº°.ªA-Za-z]*?(?:\.|$)|"
    r"Disposici[oó]n\s+(?:adicional|transitoria|derogatoria|final)\s+[^.]{1,40}\.?|"
    r"Disposici[oó]n\s+derogatoria\s+[úu]nica\.?|"
    r"Art[ií]culo\s+[úu]nico\.?|"
    r"(?:ANEXO|Anexo)\s*[IVX\d]*\.?)",
    re.IGNORECASE,
)


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", normalizar(s)) if len(t) > 1]


def dividir_preceptos(lineas: list[str]) -> list[dict]:
    """Agrupa líneas de texto en preceptos. Lo previo al primero va como 'Preámbulo'."""
    res, actual = [], {"id": "Preámbulo", "titulo": "Preámbulo / parte inicial", "texto": []}
    for ln in lineas:
        ln = ln.strip()
        if not ln:
            continue
        m = RE_PRECEPTO.match(ln)
        if m and len(ln) < 400:
            if actual["texto"]:
                res.append(actual)
            cab = m.group(0).strip().rstrip(".")
            actual = {"id": clave_precepto(cab), "titulo": ln, "texto": []}
            resto = ln[len(m.group(0)):].strip()
            if resto:
                actual["texto"].append(resto)
        else:
            actual["texto"].append(ln)
    if actual["texto"]:
        res.append(actual)
    for p in res:
        p["texto"] = "\n".join(p["texto"])
    return res


def clave_precepto(cab: str) -> str:
    n = normalizar(cab)
    m = re.match(r"articulo\s+(\d+)\s*(bis|ter|quater|quinquies|sexies)?\b", n)
    if m:
        return m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")
    if "unico" in n and "articulo" in n:
        return "unico"
    m = re.match(r"disposicion\s+(adicional|transitoria|derogatoria|final)\s*(.*)", n)
    if m:
        pref = {"adicional": "da", "transitoria": "dt", "derogatoria": "dd", "final": "df"}[m.group(1)]
        return f"{pref}-{m.group(2).strip().replace(' ', '-') or 'unica'}"
    return re.sub(r"\W+", "-", n).strip("-")


class Corpus:
    def __init__(self):
        self.catalogo = json.loads((DATOS / "catalogo.json").read_text("utf-8"))
        self.normas = {}
        for c in self.catalogo:
            f = DATOS / f"normas_{c['n']:02d}.json"
            c["descargada"] = f.exists()
            if f.exists():
                d = json.loads(f.read_text("utf-8"))
                c["preceptos"] = d["preceptos"]
                c["actualizado"] = d.get("actualizado", "")
            else:
                c["preceptos"] = []
            self.normas[c["n"]] = c
        self._indexar()

    def _indexar(self):
        self.docs, self.tf, self.df, self.largos = [], [], {}, []
        for c in self.catalogo:
            for i, p in enumerate(c["preceptos"]):
                toks = tokens(p["titulo"] + " " + p["texto"])
                bag = {}
                for t in toks:
                    bag[t] = bag.get(t, 0) + 1
                self.docs.append((c["n"], i))
                self.tf.append(bag)
                self.largos.append(len(toks) or 1)
                for t in bag:
                    self.df[t] = self.df.get(t, 0) + 1
        self.avg = (sum(self.largos) / len(self.largos)) if self.largos else 1

    def resolver(self, ref) -> dict | None:
        """Acepta número (5), alias ('LOE', 'ROC') o fragmento del título ('106/2009')."""
        s = str(ref).strip()
        if s.isdigit() and int(s) in self.normas:
            return self.normas[int(s)]
        ns = normalizar(s)
        for c in self.catalogo:
            if ns in {normalizar(a) for a in c["alias"]}:
                return c
        for c in self.catalogo:
            if ns and ns in normalizar(c["titulo"]):
                return c
        return None

    def precepto(self, c: dict, num: str) -> dict | None:
        k = clave_precepto("Artículo " + num) if re.match(r"^\d", num.strip()) else normalizar(num).replace(" ", "-")
        k2 = normalizar(num).replace(" ", "-")
        for p in c["preceptos"]:
            if p["id"] in (k, k2, num):
                return p
        return None

    def buscar(self, consulta: str, norma: dict | None = None, limite: int = 8):
        q = tokens(consulta)
        if not q or not self.docs:
            return []
        N = len(self.docs)
        out = []
        for idx, (n, i) in enumerate(self.docs):
            if norma and n != norma["n"]:
                continue
            bag, L, s = self.tf[idx], self.largos[idx], 0.0
            for t in q:
                f = bag.get(t, 0)
                if not f:
                    continue
                idf = math.log(1 + (N - self.df[t] + 0.5) / (self.df[t] + 0.5))
                s += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * L / self.avg))
            if s > 0:
                out.append((s, n, i))
        out.sort(reverse=True)
        return out[:limite]

    @staticmethod
    def fragmento(texto: str, consulta: str, ancho: int = 220) -> str:
        nt = normalizar(texto)
        pos = -1
        for t in tokens(consulta):
            pos = nt.find(t)
            if pos >= 0:
                break
        pos = max(pos, 0)
        a = max(0, pos - ancho // 3)
        frag = texto[a:a + ancho].replace("\n", " ")
        return ("…" if a else "") + frag + ("…" if a + ancho < len(texto) else "")
