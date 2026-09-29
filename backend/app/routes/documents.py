import os
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, DocumentType
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.services.document_service import (
    extract_text,
    get_file_extension,
    is_supported_file_type,
    save_uploaded_file,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload (.pdf, .docx, .txt)"),
    document_type: str = Form(..., description="Document type: threat_intelligence, incident_runbook, or vulnerability_advisory"),
    title: Optional[str] = Form(None, description="Optional document title"),
    db: Session = Depends(get_db),
):
    """
    Upload a document (PDF, DOCX, TXT), extract plain text content, and save metadata to PostgreSQL.
    """
    if not file.filename or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty.",
        )

    # 1. Validate file format / extension
    if not is_supported_file_type(file.filename):
        ext = get_file_extension(file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Supported formats are: .pdf, .docx, .txt",
        )

    # 2. Validate document_type enum
    valid_types = [dt.value for dt in DocumentType]
    if document_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document_type '{document_type}'. Allowed types are: {', '.join(valid_types)}",
        )

    # 3. Save uploaded file to local disk (uploads/)
    try:
        saved_file_path, safe_filename = await save_uploaded_file(file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}",
        )

    # 4. Extract text from saved file
    try:
        ext = get_file_extension(file.filename)
        extracted_text = extract_text(saved_file_path, ext)
    except Exception as e:
        # If extraction fails, cleanup saved file and return error
        if os.path.exists(saved_file_path):
            os.remove(saved_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text extraction failed: {str(e)}",
        )

    # 5. Store document record in PostgreSQL
    doc_title = title.strip() if title and title.strip() else file.filename
    doc_enum_type = DocumentType(document_type)

    new_doc = Document(
        title=doc_title,
        document_type=doc_enum_type,
        file_name=file.filename,
        file_path=saved_file_path,
        content=extracted_text,
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    doc_type_str = new_doc.document_type.value if hasattr(new_doc.document_type, "value") else str(new_doc.document_type)

    return DocumentUploadResponse(
        document_id=new_doc.id,
        filename=new_doc.file_name,
        document_type=doc_type_str,
        extracted_text_length=len(extracted_text or ""),
        upload_status="success",
        id=new_doc.id,
        title=new_doc.title,
        file_name=new_doc.file_name,
        file_path=new_doc.file_path,
        content=new_doc.content,
        created_at=new_doc.created_at,
    )


@router.get("", response_model=List[DocumentResponse])
@router.get("/", response_model=List[DocumentResponse])
def get_all_documents(
    skip: int = 0,
    limit: int = 100,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve list of uploaded documents with metadata and extracted text length.
    """
    query = db.query(Document)
    if document_type:
        query = query.filter(Document.document_type == document_type)

    documents = query.offset(skip).limit(limit).all()

    result = []
    for doc in documents:
        doc_type_str = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)
        text_len = len(doc.content) if doc.content else 0
        result.append(
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                document_type=doc_type_str,
                file_name=doc.file_name,
                file_path=doc.file_path,
                content=doc.content,
                extracted_text_length=text_len,
                uploaded_by=doc.uploaded_by,
                created_at=doc.created_at,
            )
        )
    return result


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_by_id(document_id: int, db: Session = Depends(get_db)):
    """
    Retrieve document details and full extracted text by document ID.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    doc_type_str = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)
    text_len = len(doc.content) if doc.content else 0

    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        document_type=doc_type_str,
        file_name=doc.file_name,
        file_path=doc.file_path,
        content=doc.content,
        extracted_text_length=text_len,
        uploaded_by=doc.uploaded_by,
        created_at=doc.created_at,
    )
