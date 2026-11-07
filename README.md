# Dirigo

Conector MCP con la normativa de la función directiva en los centros docentes
públicos no universitarios de Canarias (17 normas, según el listado de la
Inspección de Educación consultado el 7-11-2026).

*Hadrianus Muratellensis me fecit* · CC BY-NC-SA 4.0

## Herramientas (salidas compactas)

| Herramienta | Uso |
|---|---|
| `normas(bloque?)` | Lista las 17 normas, alias y estado de descarga |
| `buscar(consulta, norma?, limite?)` | Búsqueda BM25 sin tildes; devuelve `[norma\|precepto]` + fragmento |
| `articulo(norma, numero)` | Texto completo: `135`, `15 bis`, `da-primera`, `dt-2`, `df-unica` |
| `indice(norma, filtro?)` | Ids y encabezados de los preceptos |
| `leer(norma, desde?, caracteres?)` | Lectura por tramos (órdenes y resoluciones cortas) |

`norma` admite número (1-17), alias (`LOE`, `LODE`, `ROC`, `D106`…) o parte del título (`106/2009`).

## Despliegue gratuito en Render

1. Sube la carpeta a GitHub (`luscitiosus/Dirigo`).
2. En Render: *New → Blueprint* con el repo (usa `render.yaml`, plan free).
3. El build ejecuta `descargar.py`, que baja los textos de BOE (API de
   legislación consolidada) y BOC (índice del boletín + página de la disposición).
4. URL del conector: `https://<tu-servicio>.onrender.com/mcp`.

No usa APIs de pago. El plan free se duerme tras inactividad (primer arranque lento).

## Uso local

```
pip install -r requirements.txt
python descargar.py        # o: python descargar.py 5 7
python server.py                    # stdio; con PORT=8000 sirve HTTP en /mcp
python test_basico.py
```

## Pendiente de verificar tras la primera descarga

- La norma 17 (Resolución de 3-9-2024) solo está publicada en la web de la
  Inspección, sin URL en el listado: guarda su texto en `manual_17.txt` (o `manual_17.pdf`).
- La descarga automática no se pudo probar contra BOE/BOC desde el entorno de
  desarrollo (hosts bloqueados). Revisa el log del build: cada norma imprime
  `OK` o `FALLO`. Reejecuta solo las fallidas con `python descargar.py N`.
- Para que el texto de Render incluya la norma 17, haz commit de `manual_17.txt`.
