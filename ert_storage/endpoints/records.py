import uuid
import io
import numpy as np
from typing import Any, Mapping, Optional, List, AsyncGenerator
import sqlalchemy as sa
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Header,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm.exc import NoResultFound
from ert_storage.database import Session, get_db, HAS_AZURE_BLOB_STORAGE, BLOB_CONTAINER
from ert_storage import database_schema as ds, json_schema as js


if HAS_AZURE_BLOB_STORAGE:
    from ert_storage.database import azure_blob_container


router = APIRouter(tags=["record"])


class ListRecords(BaseModel):
    ensemble: Mapping[str, str]
    forward_model: Mapping[str, str]


@router.post("/ensembles/{ensemble_id}/records/{name}/file")
async def post_ensemble_record_file(
    *,
    db: Session = Depends(get_db),
    ensemble_id: int,
    name: str,
    realization_index: Optional[int] = None,
    file: UploadFile = File(...),
) -> None:
    """
    Assign an arbitrary file to the given `name` record.
    """
    ensemble = _get_and_assert_ensemble(db, ensemble_id, name, realization_index)

    file_obj = ds.File(
        filename=file.filename,
        mimetype=file.content_type,
    )
    if HAS_AZURE_BLOB_STORAGE:
        key = f"{name}@{realization_index}@{uuid.uuid4()}"
        blob = azure_blob_container.get_blob_client(key)
        await blob.upload_blob(file.file)

        file_obj.az_container = azure_blob_container.container_name
        file_obj.az_blob = key
    else:
        file_obj.content = await file.read()

    db.add(file_obj)
    record_obj = ds.Record(
        name=name,
        record_type=ds.RecordType.file,
        realization_index=realization_index,
        file=file_obj,
    )

    record_obj.ensemble = ensemble
    db.add(record_obj)


@router.put("/ensembles/{ensemble_id}/records/{name}/blob")
async def add_block(
    *,
    db: Session = Depends(get_db),
    ensemble_id: int,
    name: str,
    realization_index: Optional[int] = None,
    request: Request,
    block_index: int,
) -> None:
    """
    Stage blocks to an existing azure blob record.
    """

    ensemble = db.query(ds.Ensemble).filter_by(id=ensemble_id).one()
    block_id = str(uuid.uuid4())

    file_block_obj = ds.FileBlock(
        ensemble=ensemble,
        block_id=block_id,
        block_index=block_index,
        record_name=name,
        realization_index=realization_index,
    )

    record_obj = (
        db.query(ds.Record)
        .filter_by(
            ensemble_id=ensemble.id, name=name, realization_index=realization_index
        )
        .one()
    )
    if HAS_AZURE_BLOB_STORAGE:
        key = record_obj.file.az_blob
        blob = azure_blob_container.get_blob_client(key)
        await blob.stage_block(block_id, await request.body())
    else:
        file_block_obj.content = await request.body()

    db.add(file_block_obj)
    db.commit()


@router.post("/ensembles/{ensemble_id}/records/{name}/blob")
async def create_blob(
    *,
    db: Session = Depends(get_db),
    ensemble_id: int,
    name: str,
    realization_index: Optional[int] = None,
) -> None:
    """
    Create a record which points to a blob on Azure Blob Storage.
    """

    ensemble = db.query(ds.Ensemble).filter_by(id=ensemble_id).one()
    file_obj = ds.File(
        filename="test",
        mimetype="mime/type",
    )
    if HAS_AZURE_BLOB_STORAGE:
        key = f"{name}@{realization_index}@{uuid.uuid4()}"
        blob = azure_blob_container.get_blob_client(key)
        file_obj.az_container = (azure_blob_container.container_name,)
        file_obj.az_blob = (key,)
    else:
        pass

    db.add(file_obj)
    record_obj = ds.Record(
        name=name,
        record_type=ds.RecordType.file,
        realization_index=realization_index,
        file=file_obj,
    )

    record_obj.ensemble = ensemble
    db.add(record_obj)


@router.patch("/ensembles/{ensemble_id}/records/{name}/blob")
async def finalize_blob(
    *,
    db: Session = Depends(get_db),
    ensemble_id: int,
    name: str,
    realization_index: Optional[int] = None,
) -> None:
    """
    Commit all staged blocks to a blob record
    """

    ensemble = db.query(ds.Ensemble).filter_by(id=ensemble_id).one()

    record_obj = (
        db.query(ds.Record)
        .filter_by(
            ensemble_id=ensemble.id, name=name, realization_index=realization_index
        )
        .one()
    )

    submitted_blocks = list(
        db.query(ds.FileBlock)
        .filter_by(
            record_name=name,
            ensemble_id=ensemble.id,
            realization_index=realization_index,
        )
        .all()
    )

    if HAS_AZURE_BLOB_STORAGE:
        key = record_obj.file.az_blob
        blob = azure_blob_container.get_blob_client(key)
        block_ids = [
            block.block_id
            for block in sorted(submitted_blocks, key=lambda x: x.block_index)
        ]
        await blob.commit_block_list(block_ids)
    else:
        data = b"".join([block.content for block in submitted_blocks])
        record_obj.file.content = data


@router.post("/ensembles/{ensemble_id}/records/{name}/matrix")
async def post_ensemble_record_matrix(
    *,
    db: Session = Depends(get_db),
    ensemble_id: int,
    name: str,
    realization_index: Optional[int] = None,
    content_type: str = Header("application/json"),
    request: Request,
) -> None:
    """
    Assign an n-dimensional float matrix, encoded in JSON, to the given `name` record.
    """
    ensemble = _get_and_assert_ensemble(db, ensemble_id, name, realization_index)

    try:
        if content_type == "application/json":
            content = np.array(await request.json(), dtype=np.float64)
        elif content_type == "application/x-numpy":
            from numpy.lib.format import read_array

            stream = io.BytesIO(await request.body())
            content = read_array(stream)
        else:
            raise ValueError()
    except ValueError:
        if realization_index is None:
            message = f"Ensemble-wide record '{name}' for ensemble '{ensemble_id}' needs to be a matrix"
        else:
            message = f"Forward-model record '{name}' for ensemble '{ensemble_id}', realization {realization_index} needs to be a matrix"

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": message,
                "name": name,
                "ensemble_id": ensemble_id,
                "realization_index": realization_index,
            },
        )

    matrix_obj = ds.F64Matrix(
        content=content.tolist(),
    )
    db.add(matrix_obj)

    record_obj = ds.Record(
        name=name,
        record_type=ds.RecordType.float_vector,
        f64_matrix=matrix_obj,
        realization_index=realization_index,
    )
    record_obj.ensemble = ensemble
    db.add(record_obj)


@router.get("/ensembles/{ensemble_id}/records/{name}")
async def get_ensemble_record(
    *,
    db: Session = Depends(get_db),
    ensemble_id: int,
    realization_index: Optional[int] = None,
    name: str,
    accept: Optional[str] = Header(default="application/json"),
) -> Any:
    """
    Get record with a given `name`. If `realization_index` is not set, look for
    the ensemble-wide record. If it is set, look first for one created by a
    forward-model for the given realization index and then the ensemble-wide
    record.

    Records support multiple data formats. In particular:
    - Matrix:
      Will return n-dimensional float matrix, where n is arbitrary.
    - File:
      Will return the file that was uploaded.
    """
    if realization_index is None:
        bundle = _get_ensemble_record(db, ensemble_id, name)
    else:
        bundle = _get_forward_model_record(db, ensemble_id, name, realization_index)

    type_ = bundle.record_type
    if type_ == ds.RecordType.float_vector:
        if accept == "application/x-numpy":
            from numpy.lib.format import write_array

            stream = io.BytesIO()
            write_array(stream, np.array(bundle.f64_matrix.content))

            return Response(
                content=stream.getvalue(),
                media_type="application/x-numpy",
            )
        else:
            return bundle.f64_matrix.content
    if type_ == ds.RecordType.file:
        f = bundle.file
        if f.content is not None:
            return Response(
                content=f.content,
                media_type=f.mimetype,
                headers={"Content-Disposition": f'attachment; filename="{f.filename}"'},
            )
        elif f.az_container is not None and f.az_blob is not None:
            blob = azure_blob_container.get_blob_client(f.az_blob)
            download = await blob.download_blob()

            async def chunk_generator() -> AsyncGenerator[bytes, None]:
                async for chunk in download.chunks():
                    yield chunk

            return StreamingResponse(
                chunk_generator(),
                media_type=f.mimetype,
                headers={"Content-Disposition": f'attachment; filename="{f.filename}"'},
            )


def _get_ensemble_record(db: Session, ensemble_id: int, name: str) -> ds.Record:
    try:
        return (
            db.query(ds.Record)
            .filter(
                sa.and_(
                    ds.Record.ensemble_id == ensemble_id,
                    ds.Record.name == name,
                    ds.Record.realization_index == None,
                )
            )
            .one()
        )
    except NoResultFound:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Ensemble-wide record '{name}' for ensemble '{ensemble_id}' not found!",
                "name": name,
                "ensemble_id": ensemble_id,
            },
        )


def _get_forward_model_record(
    db: Session, ensemble_id: int, name: str, realization_index: int
) -> ds.Record:
    try:
        return (
            db.query(ds.Record)
            .filter(
                sa.and_(
                    ds.Record.ensemble_id == ensemble_id,
                    ds.Record.name == name,
                    ds.Record.realization_index == realization_index,
                )
            )
            .one()
        )
    except NoResultFound:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Forward-model record '{name}' for ensemble '{ensemble_id}', realization {realization_index} not found!",
                "name": name,
                "ensemble_id": ensemble_id,
            },
        )


def _get_and_assert_ensemble(
    db: Session, ensemble_id: int, name: str, realization_index: Optional[int]
) -> ds.Ensemble:
    """
    Get ensemble and verify that no record with the name `name` exists
    """
    ensemble = db.query(ds.Ensemble).filter_by(id=ensemble_id).one()

    q = db.query(ds.Record).filter_by(ensemble_id=ensemble_id, name=name)
    if realization_index is not None:
        q = q.filter(
            (ds.Record.realization_index == None)
            | (ds.Record.realization_index == realization_index)
        )

    if q.count() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": f"Ensemble-wide record '{name}' for ensemble '{ensemble_id}' already exists",
                "name": name,
                "ensemble_id": ensemble_id,
            },
        )

    return ensemble


@router.get("/ensembles/{ensemble_id}/parameters", response_model=List[str])
def get_ensemble_parameters(
    *, db: Session = Depends(get_db), ensemble_id: int
) -> List[str]:
    ensemble = db.query(ds.Ensemble).get(ensemble_id)
    return ensemble.inputs


@router.get(
    "/ensembles/{ensemble_id}/records", response_model=Mapping[str, js.RecordOut]
)
def get_ensemble_records(
    *, db: Session = Depends(get_db), ensemble_id: int
) -> Mapping[str, js.RecordOut]:
    ensemble = db.query(ds.Ensemble).get(ensemble_id)
    return {
        rec.name: js.RecordOut(id=rec.id, name=rec.name, data=rec.data)
        for rec in ensemble.records
    }


@router.get("/records/{record_id}", response_model=js.RecordOut)
def get_record(*, db: Session = Depends(get_db), record_id: int) -> js.RecordOut:
    rec = db.query(ds.Record).get(record_id)
    return js.RecordOut(id=rec.id, name=rec.name, data=rec.data)
