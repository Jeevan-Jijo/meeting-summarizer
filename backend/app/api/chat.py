from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.db_models import Meeting, ChatMessage, utcnow
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse, ChatMessageRead, Citation
from app.services.vector_store import MeetingVectorStore

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("", response_model=ChatQueryResponse)
async def query_meeting_chatbot(payload: ChatQueryRequest, db: Session = Depends(get_db)):
    """Ask a question about a meeting and receive an evidence-backed answer with timestamp citations."""
    meeting = db.query(Meeting).filter(Meeting.id == payload.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    user_query = payload.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Record User Message
    user_msg = ChatMessage(
        meeting_id=meeting.id,
        role="user",
        content=user_query,
        citations=[]
    )
    db.add(user_msg)
    db.commit()

    # Query Vector Store
    vstore = MeetingVectorStore(meeting.id)
    answer, citations = await vstore.answer_question(user_query, meeting.title)

    # Convert citations to dicts for DB storage
    citations_data = [c.model_dump() for c in citations]

    # Record Assistant Message
    assistant_msg = ChatMessage(
        meeting_id=meeting.id,
        role="assistant",
        content=answer,
        citations=citations_data
    )
    db.add(assistant_msg)
    db.commit()

    return ChatQueryResponse(
        answer=answer,
        citations=citations,
        meeting_id=meeting.id,
        query=user_query
    )


@router.get("/history/{meeting_id}", response_model=List[ChatMessageRead])
def get_chat_history(meeting_id: int, db: Session = Depends(get_db)):
    """Fetch previous chat messages for this meeting."""
    messages = db.query(ChatMessage).filter(ChatMessage.meeting_id == meeting_id).order_by(ChatMessage.created_at).all()
    results = []
    for m in messages:
        citations = []
        if m.citations:
            for c in m.citations:
                try:
                    citations.append(Citation(**c))
                except Exception:
                    pass
        results.append(ChatMessageRead(
            id=m.id,
            meeting_id=m.meeting_id,
            role=m.role,
            content=m.content,
            citations=citations,
            created_at=m.created_at
        ))
    return results


@router.delete("/history/{meeting_id}")
def clear_chat_history(meeting_id: int, db: Session = Depends(get_db)):
    """Clear chat conversation history for a meeting."""
    db.query(ChatMessage).filter(ChatMessage.meeting_id == meeting_id).delete()
    db.commit()
    return {"status": "cleared", "meeting_id": meeting_id}
