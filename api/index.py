"""
============================================================
LABORATORIO IV - PARTE II: APLICACIÓN DISTRIBUIDA
Backend — FastAPI CRUD de Gestión de Tareas
============================================================

Instalación:
    pip install fastapi uvicorn

Ejecución:
    uvicorn main:app --reload --port 8000

Documentación interactiva disponible en:
    http://localhost:8000/docs
============================================================
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import time

# ── Inicialización de la aplicación ─────────────────────────
app = FastAPI(
    title="API de Tareas — Lab IV",
    description="CRUD completo para gestión de tareas usando FastAPI",
    version="1.0.0",
)

# ── CORS: permite peticiones desde el frontend (cualquier origen) ─
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # En producción, limitar al dominio real
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Almacén en memoria (simula una base de datos) ───────────
# Formato: { tarea_id (int) : dict }
_db: dict[int, dict] = {}
_contador_id: int = 0          # Auto-incremento de IDs


# ── Modelos Pydantic ─────────────────────────────────────────

class TareaBase(BaseModel):
    """Campos comunes para crear o actualizar una tarea."""
    titulo     : str  = Field(..., min_length=1, max_length=200,
                              example="Estudiar FastAPI")
    descripcion: Optional[str] = Field(None, max_length=1000,
                                       example="Revisar documentación oficial")
    completada : bool = Field(False, example=False)


class TareaCrear(TareaBase):
    """Payload para POST /tareas."""
    pass


class TareaActualizar(BaseModel):
    """Payload para PUT /tareas/{id} — todos los campos son opcionales."""
    titulo     : Optional[str]  = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str]  = Field(None, max_length=1000)
    completada : Optional[bool] = None


class TareaRespuesta(TareaBase):
    """Respuesta enriquecida que incluye id y marca temporal."""
    id          : int
    creada_en   : float   # timestamp UNIX


# ── Utilidad interna ─────────────────────────────────────────

def _siguiente_id() -> int:
    """Genera el siguiente ID auto-incremental."""
    global _contador_id
    _contador_id += 1
    return _contador_id


# ── Endpoints ────────────────────────────────────────────────

@app.get("/", tags=["Raíz"])
def raiz():
    """Verificación de que la API está en línea."""
    return {"mensaje": "API de Tareas activa ✓", "version": "1.0.0"}


# ── CREATE ───────────────────────────────────────────────────
@app.post(
    "/tareas",
    response_model=TareaRespuesta,
    status_code=status.HTTP_201_CREATED,
    tags=["Tareas"],
    summary="Crear una nueva tarea",
)
def crear_tarea(tarea: TareaCrear):
    """
    Crea una nueva tarea y la almacena en memoria.

    - **titulo**: Nombre obligatorio de la tarea (1–200 caracteres).
    - **descripcion**: Detalle opcional (hasta 1 000 caracteres).
    - **completada**: Estado inicial, por defecto `false`.
    """
    nuevo_id = _siguiente_id()
    registro = {
        "id"         : nuevo_id,
        "titulo"     : tarea.titulo,
        "descripcion": tarea.descripcion,
        "completada" : tarea.completada,
        "creada_en"  : time.time(),
    }
    _db[nuevo_id] = registro
    return registro


# ── READ ALL ─────────────────────────────────────────────────
@app.get(
    "/tareas",
    response_model=list[TareaRespuesta],
    tags=["Tareas"],
    summary="Listar todas las tareas",
)
def listar_tareas():
    """Retorna la lista completa de tareas ordenadas por ID."""
    return sorted(_db.values(), key=lambda t: t["id"])


# ── READ ONE ─────────────────────────────────────────────────
@app.get(
    "/tareas/{tarea_id}",
    response_model=TareaRespuesta,
    tags=["Tareas"],
    summary="Obtener una tarea por ID",
)
def obtener_tarea(tarea_id: int):
    """
    Retorna los detalles de una tarea específica.

    Lanza **404** si el ID no existe.
    """
    if tarea_id not in _db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea con id={tarea_id} no encontrada.",
        )
    return _db[tarea_id]


# ── UPDATE ───────────────────────────────────────────────────
@app.put(
    "/tareas/{tarea_id}",
    response_model=TareaRespuesta,
    tags=["Tareas"],
    summary="Actualizar una tarea existente",
)
def actualizar_tarea(tarea_id: int, datos: TareaActualizar):
    """
    Actualiza parcialmente una tarea (PATCH semántico via PUT).

    Solo se modifican los campos que se envíen en el body;
    los demás conservan sus valores anteriores.

    Lanza **404** si el ID no existe.
    """
    if tarea_id not in _db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea con id={tarea_id} no encontrada.",
        )

    registro = _db[tarea_id]

    # Actualizar solo los campos que no sean None en el payload
    cambios = datos.model_dump(exclude_none=True)
    registro.update(cambios)

    _db[tarea_id] = registro
    return registro


# ── DELETE ───────────────────────────────────────────────────
@app.delete(
    "/tareas/{tarea_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tareas"],
    summary="Eliminar una tarea",
)
def eliminar_tarea(tarea_id: int):
    """
    Elimina permanentemente una tarea.

    Retorna **204 No Content** si se elimina con éxito.
    Lanza **404** si el ID no existe.
    """
    if tarea_id not in _db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea con id={tarea_id} no encontrada.",
        )
    del _db[tarea_id]
    # 204 No Content → sin body de respuesta
