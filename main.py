from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import time

app = FastAPI(
    title="API de Tareas — Lab IV",
    description="CRUD completo para gestión de tareas usando FastAPI",
    version="1.0.0",
)

# Configuración de CORS [4]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_db: dict[int, dict] = {}
_contador_id: int = 0

class TareaBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200, json_schema_extra={"example": "Estudiar FastAPI"})
    descripcion: Optional[str] = Field(None, max_length=1000, json_schema_extra={"example": "Revisar docs"})
    completada: bool = Field(False)

class TareaCrear(TareaBase):
    pass

class TareaActualizar(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1)
    descripcion: Optional[str] = Field(None)
    completada: Optional[bool] = None

class TareaRespuesta(TareaBase):
    id: int
    creada_en: float

def _siguiente_id() -> int:
    global _contador_id
    _contador_id += 1
    return _contador_id

@app.get("/", tags=["Raíz"])
def raiz():
    return {"mensaje": "API de Tareas activa ✓", "version": "1.0.0"}

@app.post("/tareas", response_model=TareaRespuesta, status_code=status.HTTP_201_CREATED, tags=["Tareas"])
def crear_tarea(tarea: TareaCrear):
    nid = _siguiente_id()
    nueva_tarea = {"id": nid, "creada_en": time.time(), **tarea.model_dump()}
    _db[nid] = nueva_tarea
    return nueva_tarea

@app.get("/tareas", response_model=List[TareaRespuesta], tags=["Tareas"])
def listar_tareas():
    return sorted(_db.values(), key=lambda t: t["id"])

@app.get("/tareas/{tarea_id}", response_model=TareaRespuesta, tags=["Tareas"])
def obtener_tarea(tarea_id: int):
    if tarea_id not in _db:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return _db[tarea_id]

@app.put("/tareas/{tarea_id}", response_model=TareaRespuesta, tags=["Tareas"])
def actualizar_tarea(tarea_id: int, datos: TareaActualizar):
    if tarea_id not in _db:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    _db[tarea_id].update(datos.model_dump(exclude_none=True))
    return _db[tarea_id]

@app.delete("/tareas/{tarea_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tareas"])
def eliminar_tarea(tarea_id: int):
    if tarea_id not in _db:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    del _db[tarea_id]