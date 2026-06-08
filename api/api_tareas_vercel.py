"""
============================================================
LABORATORIO IV - PARTE III: CLOUD COMPUTING
Serverless Function para Vercel — api/tareas.py
============================================================

Estructura de archivos requerida en el proyecto:
    mi-lab4/
    ├── api/
    │   └── tareas.py          ← Este archivo
    ├── index.html              ← Frontend (parte 2)
    └── vercel.json             ← Configuración de rutas

NOTAS IMPORTANTES para Vercel:
  - Cada archivo en /api/ se convierte en una función serverless.
  - Vercel soporta FastAPI/ASGI de forma nativa.
  - El almacén en memoria se reinicia en cada invocación "fría"
    (cold start). Para producción real usar una DB externa,
    p. ej. Vercel KV (Redis) o PlanetScale (MySQL).
============================================================
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import time

# ── Aplicación ASGI (Vercel detecta el objeto `app`) ────────
app = FastAPI(
    title="API de Tareas — Serverless Vercel",
    description="CRUD de tareas desplegado como Serverless Function en Vercel",
    version="1.0.0",
    # En Vercel el path base de la función es /api/tareas
    root_path="/api/tareas",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Cambiar al dominio de tu frontend en producción
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Almacén en memoria (stateless entre cold starts) ────────
# Para persistencia real → usar Vercel KV:
#   from vercel_kv import kv
#   await kv.set("tareas", json.dumps(_db))
_db: dict[int, dict] = {}
_contador: int = 0


# ── Modelos ──────────────────────────────────────────────────

class TareaCrear(BaseModel):
    titulo     : str           = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=1000)
    completada : bool          = False

class TareaActualizar(BaseModel):
    titulo     : Optional[str]  = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str]  = Field(None, max_length=1000)
    completada : Optional[bool] = None

class TareaRespuesta(TareaCrear):
    id       : int
    creada_en: float


def _next_id() -> int:
    global _contador
    _contador += 1
    return _contador


# ── Endpoints ────────────────────────────────────────────────

@app.get("/")
def raiz():
    return {"mensaje": "Serverless API de Tareas en Vercel ✓"}


@app.post("/", response_model=TareaRespuesta,
          status_code=status.HTTP_201_CREATED)
def crear(tarea: TareaCrear):
    nid = _next_id()
    reg = {"id": nid, "creada_en": time.time(), **tarea.model_dump()}
    _db[nid] = reg
    return reg


@app.get("/", response_model=list[TareaRespuesta])
def listar():
    return sorted(_db.values(), key=lambda t: t["id"])


@app.get("/{tid}", response_model=TareaRespuesta)
def obtener(tid: int):
    if tid not in _db:
        raise HTTPException(404, f"Tarea {tid} no encontrada.")
    return _db[tid]


@app.put("/{tid}", response_model=TareaRespuesta)
def actualizar(tid: int, datos: TareaActualizar):
    if tid not in _db:
        raise HTTPException(404, f"Tarea {tid} no encontrada.")
    _db[tid].update(datos.model_dump(exclude_none=True))
    return _db[tid]


@app.delete("/{tid}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(tid: int):
    if tid not in _db:
        raise HTTPException(404, f"Tarea {tid} no encontrada.")
    del _db[tid]
