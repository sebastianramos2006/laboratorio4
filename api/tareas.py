from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import time

app = FastAPI(
    title="API de Tareas — Serverless Vercel",
    description="CRUD de tareas desplegado como Serverless Function en Vercel",
    version="1.0.0"
)

# ==========================
# CORS
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# BASE DE DATOS TEMPORAL
# ==========================

_db: dict[int, dict] = {}
_contador: int = 0

# ==========================
# MODELOS
# ==========================

class TareaCrear(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=1000)
    completada: bool = False


class TareaActualizar(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=1000)
    completada: Optional[bool] = None


class TareaRespuesta(TareaCrear):
    id: int
    creada_en: float


# ==========================
# UTILIDADES
# ==========================

def _next_id() -> int:
    global _contador
    _contador += 1
    return _contador


# ==========================
# ENDPOINT RAÍZ
# ==========================

@app.get("/")
def raiz():
    return {
        "mensaje": "API de Tareas activa",
        "version": "1.0.0"
    }


# ==========================
# LISTAR TAREAS
# ==========================

@app.get("/tareas", response_model=List[TareaRespuesta])
def listar_tareas():
    return sorted(_db.values(), key=lambda t: t["id"])


# ==========================
# CREAR TAREA
# ==========================

@app.post(
    "/tareas",
    response_model=TareaRespuesta,
    status_code=status.HTTP_201_CREATED
)
def crear_tarea(tarea: TareaCrear):

    nuevo_id = _next_id()

    registro = {
        "id": nuevo_id,
        "titulo": tarea.titulo,
        "descripcion": tarea.descripcion,
        "completada": tarea.completada,
        "creada_en": time.time()
    }

    _db[nuevo_id] = registro

    return registro


# ==========================
# OBTENER TAREA
# ==========================

@app.get("/tareas/{tid}", response_model=TareaRespuesta)
def obtener_tarea(tid: int):

    if tid not in _db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {tid} no encontrada."
        )

    return _db[tid]


# ==========================
# ACTUALIZAR TAREA
# ==========================

@app.put("/tareas/{tid}", response_model=TareaRespuesta)
def actualizar_tarea(tid: int, datos: TareaActualizar):

    if tid not in _db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {tid} no encontrada."
        )

    cambios = datos.model_dump(exclude_none=True)

    _db[tid].update(cambios)

    return _db[tid]


# ==========================
# ELIMINAR TAREA
# ==========================

@app.delete(
    "/tareas/{tid}",
    status_code=status.HTTP_204_NO_CONTENT
)
def eliminar_tarea(tid: int):

    if tid not in _db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {tid} no encontrada."
        )

    del _db[tid]

    return None