import os
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, DocumentChunk, DocumentType
from app.schemas.document import (
    DocumentChunkResponse,
    DocumentEmbedResponse,
    DocumentProcessResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.chunking_service import chunk_text
from app.services.document_service import (
    extract_text,
    get_file_extension,
    is_supported_file_type,
    save_uploaded_file,
)
from app.services.embedding_service import (
    EMBEDDING_DIMENSION,
    generate_embeddings_batch,
    serialize_embedding,
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


@router.post("/{document_id}/process", response_model=DocumentProcessResponse)
def process_document_chunks(
    document_id: int,
    force: bool = Query(False, description="Set to true to force re-processing and overwrite existing chunks"),
    db: Session = Depends(get_db),
):
    """
    Cleans extracted document text, splits it into sequential chunks (500-800 words),
    and stores the resulting chunks in the DocumentChunk database table.
    """
    # 1. Fetch document from database
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    # 2. Check if content exists
    if not doc.content or not doc.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document content is empty. Cannot process document.",
        )

    # 3. Check for existing chunks (prevent duplicate processing unless force=True)
    existing_chunks_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count()

    if existing_chunks_count > 0 and not force:
        return DocumentProcessResponse(
            document_id=document_id,
            chunks_created=existing_chunks_count,
            processing_status="already_processed",
            message="Document has already been processed into chunks. Set force=true to re-process.",
        )

    # 4. If force re-processing, delete existing chunks
    if existing_chunks_count > 0 and force:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        db.commit()

    # 5. Clean text and generate chunks (500-800 words, overlapping)
    chunk_strings = chunk_text(doc.content, target_chunk_size=600, chunk_overlap=60)

    if not chunk_strings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text chunks generated from document content.",
        )

    # 6. Save chunks to DocumentChunk table
    new_chunks = []
    for index, text_snippet in enumerate(chunk_strings):
        chunk_record = DocumentChunk(
            document_id=document_id,
            chunk_index=index,
            content=text_snippet,
        )
        new_chunks.append(chunk_record)

    db.add_all(new_chunks)
    db.commit()

    return DocumentProcessResponse(
        document_id=document_id,
        chunks_created=len(new_chunks),
        processing_status="success",
        message=f"Document processed successfully into {len(new_chunks)} text chunk(s).",
    )


@router.post("/{document_id}/embed", response_model=DocumentEmbedResponse)
def generate_document_embeddings(
    document_id: int,
    force: bool = Query(False, description="Set to true to force re-generating vector embeddings"),
    db: Session = Depends(get_db),
):
    """
    Generates 384-dimensional semantic embeddings for all chunks of a document
    using SentenceTransformer ('all-MiniLM-L6-v2').
    """
    # 1. Check if document exists
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    # 2. Fetch document chunks
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document with ID {document_id} has no chunks. Please process the document first via /api/documents/{document_id}/process.",
        )

    # 3. Check if embeddings already exist (avoid unnecessary regeneration unless force=True)
    already_embedded = all(c.embedding is not None for c in chunks)
    if already_embedded and not force:
        return DocumentEmbedResponse(
            document_id=document_id,
            chunks_embedded=len(chunks),
            embedding_dimension=EMBEDDING_DIMENSION,
            status="already_embedded",
            message="Embeddings already generated for this document. Set force=true to regenerate.",
        )

    # 4. Extract text content from chunks and generate embeddings in batch
    texts = [c.content for c in chunks]
    try:
        vectors = generate_embeddings_batch(texts)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embeddings: {str(e)}",
        )

    # 5. Store serialized embeddings in database
    for chunk_obj, vec in zip(chunks, vectors):
        chunk_obj.embedding = serialize_embedding(vec)

    db.commit()

    # 6. Keep FAISS vector search index up to date
    try:
        from app.services.vector_search_service import get_vector_search_service
        get_vector_search_service().rebuild_index(db)
    except Exception as e:
        print(f"Notice: FAISS index update after embed: {e}")

    return DocumentEmbedResponse(
        document_id=document_id,
        chunks_embedded=len(chunks),
        embedding_dimension=EMBEDDING_DIMENSION,
        status="success",
        message=f"Generated semantic embeddings for {len(chunks)} document chunk(s).",
    )


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkResponse])
def get_document_chunks(document_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all processed text chunks for a given document.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    return chunks


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
