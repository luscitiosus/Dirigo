# Hadrianus Muratellensis me fecit
# Licencia: CC BY-NC-SA 4.0
"""Dirigo: conector MCP con la normativa de la función directiva (centros públicos
no universitarios de Canarias). Salidas compactas para gastar pocos tokens."""
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from corpus import Corpus

C = Corpus()
mcp = FastMCP(
    "Dirigo",
    instructions=(
        "Normativa de la función directiva en centros públicos no universitarios de Canarias "
        "(17 normas). Flujo: buscar → articulo. Cita siempre norma, precepto y publicación; "
        "el texto de cada precepto es el recuperado de la fuente oficial, no lo parafrasees "
        "como literal. Si una norma no está descargada, díselo al usuario."
    ),
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "8000")),
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

AVISO_VACIO = "Norma no descargada todavía (ver README: descargar.py)."


def _norma(ref):
    c = C.resolver(ref)
    if not c:
        raise ValueError(f"Norma no reconocida: {ref!r}. Usa la herramienta 'normas'.")
    return c


@mcp.tool()
def normas(bloque: str = "") -> str:
    """Lista las 17 normas con su número, alias, publicación y nº de preceptos.
    'bloque' filtra por texto del bloque temático (p. ej. 'selección', 'retribuciones')."""
    from corpus import normalizar
    out, actual = [], None
    for c in C.catalogo:
        if bloque and normalizar(bloque) not in normalizar(c["bloque"]):
            continue
        if c["bloque"] != actual:
            actual = c["bloque"]
            out.append(f"## {actual}")
        est = f"{len(c['preceptos'])} prec." if c["descargada"] else "sin texto"
        al = "/".join(c["alias"][:2])
        out.append(f"{c['n']}. {c['corto']} [{al}] · {c['publicacion']} · {est}")
        if c["nota"]:
            out.append(f"   nota: {c['nota']}")
    return "\n".join(out)


@mcp.tool()
def buscar(consulta: str, norma: str = "", limite: int = 8) -> str:
    """Busca en todas las normas (o en una: número, alias como 'LOE'/'ROC' o parte del título).
    Devuelve referencia + fragmento; usa 'articulo' para el texto completo."""
    c = _norma(norma) if norma else None
    res = C.buscar(consulta, c, max(1, min(limite, 20)))
    if not res:
        return "Sin resultados" + ("" if C.docs else ". " + AVISO_VACIO)
    out = []
    for s, n, i in res:
        nm = C.normas[n]
        p = nm["preceptos"][i]
        out.append(f"[{n}|{p['id']}] {nm['corto']} · {p['titulo'][:90]}\n  {C.fragmento(p['texto'], consulta)}")
    return "\n".join(out)


@mcp.tool()
def articulo(norma: str, numero: str) -> str:
    """Texto completo de un precepto. 'numero': '135', '131 bis', 'da-primera' (disposición
    adicional primera), 'dt-2', 'df-unica', 'unico'. Ver 'indice' para los ids disponibles."""
    c = _norma(norma)
    if not c["descargada"]:
        return AVISO_VACIO
    p = C.precepto(c, numero)
    if not p:
        return f"No encuentro '{numero}' en {c['corto']}. Usa 'indice'."
    return f"{c['titulo']}\n{c['publicacion']}\n\n{p['titulo']}\n{p['texto']}"


@mcp.tool()
def indice(norma: str, filtro: str = "") -> str:
    """Índice compacto de una norma: id de precepto y primeras palabras. 'filtro' acota por texto."""
    from corpus import normalizar
    c = _norma(norma)
    if not c["descargada"]:
        return AVISO_VACIO
    f = normalizar(filtro)
    lin = [f"{p['id']}: {p['titulo'][:80]}" for p in c["preceptos"] if not f or f in normalizar(p["titulo"])]
    return f"{c['corto']} ({len(c['preceptos'])} prec.)\n" + "\n".join(lin)


@mcp.tool()
def leer(norma: str, desde: int = 0, caracteres: int = 6000) -> str:
    """Lee una norma completa por tramos (útil para normas cortas como órdenes y resoluciones)."""
    c = _norma(norma)
    if not c["descargada"]:
        return AVISO_VACIO
    txt = "\n\n".join(f"{p['titulo']}\n{p['texto']}" for p in c["preceptos"])
    caracteres = max(500, min(caracteres, 20000))
    trozo = txt[desde:desde + caracteres]
    fin = desde + caracteres
    pie = f"\n\n[siguiente tramo: desde={fin} de {len(txt)}]" if fin < len(txt) else "\n\n[fin]"
    return f"{c['titulo']}\n{c['publicacion']}\n\n{trozo}{pie}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http" if os.environ.get("PORT") or os.environ.get("MCP_HTTP") else "stdio")
