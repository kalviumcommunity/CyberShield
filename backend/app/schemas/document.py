from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
    """
    Response schema for document upload operation.
    """
    document_id: int = Field(..., description="ID of the stored document")
    filename: str = Field(..., description="Original filename")
    document_type: str = Field(..., description="Category of the document")
    extracted_text_length: int = Field(..., description="Length of text extracted from document")
    upload_status: str = Field("success", description="Upload status result")

    # Full document object details
    id: int = Field(..., description="Document primary key ID")
    title: str = Field(..., description="Title of the document")
    file_name: str = Field(..., description="Original filename saved")
    file_path: str = Field(..., description="Local path where document file is stored")
    content: Optional[str] = Field(None, description="Extracted plain text content")
    created_at: datetime = Field(..., description="Upload timestamp")

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    """
    Response schema for fetching document details.
    """
    id: int = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    document_type: str = Field(..., description="Type of document")
    file_name: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Path to stored file")
    content: Optional[str] = Field(None, description="Extracted plain text content")
    extracted_text_length: int = Field(0, description="Character count of extracted text")
    uploaded_by: Optional[int] = Field(None, description="ID of uploading user if available")
    created_at: datetime = Field(..., description="Created timestamp")

    model_config = ConfigDict(from_attributes=True)


class DocumentProcessResponse(BaseModel):
    """
    Response schema for POST /api/documents/{document_id}/process
    """
    document_id: int = Field(..., description="ID of the processed document")
    chunks_created: int = Field(..., description="Number of text chunks generated")
    processing_status: str = Field(..., description="Status of processing ('success' or 'already_processed')")
    message: str = Field(..., description="Descriptive status message")

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkResponse(BaseModel):
    """
    Response schema for individual document text chunk.
    """
    id: int = Field(..., description="Chunk primary key ID")
    document_id: int = Field(..., description="Associated document ID")
    chunk_index: int = Field(..., description="Order index of chunk within document")
    content: str = Field(..., description="Text content of chunk")
    embedding: Optional[str] = Field(None, description="Serialized vector embedding")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class DocumentEmbedResponse(BaseModel):
    """
    Response schema for POST /api/documents/{document_id}/embed
    """
    document_id: int = Field(..., description="ID of the embedded document")
    chunks_embedded: int = Field(..., description="Number of text chunks embedded")
    embedding_dimension: int = Field(384, description="Vector embedding dimension (384)")
    status: str = Field(..., description="Status of embedding ('success' or 'already_embedded')")
    message: str = Field(..., description="Descriptive status message")

    model_config = ConfigDict(from_attributes=True)
