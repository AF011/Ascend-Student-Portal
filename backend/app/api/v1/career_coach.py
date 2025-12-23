from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
from app.middleware.auth_middleware import get_current_user
from app.services.groq_service import groq_service
from app.db.mongo import get_database
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
import json
import asyncio

router = APIRouter(prefix="/career-coach", tags=["Career Coach"])


class ChatRequest(BaseModel):
    message: str
    roadmap_id: Optional[str] = None



@router.get("/history")
async def get_chat_history(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Get chat history"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access career coach")
    
    try:
        db = get_database()
        chat_doc = db.career_coach_chats.find_one({"user_id": current_user["user_id"]})
        
        if not chat_doc:
            return {"success": True, "messages": [], "message": "No chat history"}
        
        messages = chat_doc.get("messages", [])[-limit:]
        
        # Convert datetime objects to ISO strings
        for msg in messages:
            if "timestamp" in msg and isinstance(msg["timestamp"], datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
        
        return {"success": True, "messages": messages, "total_messages": len(messages)}
    
    except Exception as e:
        print(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/chat", response_model=dict)
async def job_chat(
    request: dict,
    current_user = Depends(get_current_user)
):
    """Chat about a specific job"""
    message = request.get("message")
    context = request.get("context", {})
    
    prompt = f"""You are a career advisor AI. Answer the student's question about this job:

Job Title: {context.get('job_title')}
Company: {context.get('company')}
Description: {context.get('description')}
Requirements: {context.get('requirements')}
Skills: {context.get('skills_required')}

Student Question: {message}

Provide a helpful, concise answer (2-3 sentences max).
"""
    
    try:
        response = await groq_service.generate_response(prompt, max_tokens=200)
        return {"success": True, "response": response}
    except Exception as e:
        return {"success": False, "response": "I'm having trouble right now. Please try again."}

@router.post("/job-question", response_model=dict)
async def job_question(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Ask a question about a specific job (non-streaming)"""
    from groq import Groq
    from app.config import settings
    
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access career coach")
    
    message = request.get("message", "")
    context = request.get("context", {})
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Enhanced system prompt for professional, concise responses
    system_prompt = """You are a professional career advisor helping students with job opportunities.

Guidelines:
- Be concise and direct (2-4 sentences unless asked for details)
- Use a professional, human tone (avoid sounding robotic)
- Use bullet points for lists, never use ** or ## markdown
- Never use asterisks (**) for emphasis
- Format lists as: • Item or - Item
- Only provide detailed responses when explicitly asked
- Focus on actionable insights"""
    
    user_prompt = f"""Job: {context.get('job_title', 'N/A')} at {context.get('company', 'N/A')}
Location: {context.get('location', 'N/A')}
Type: {context.get('job_type', 'N/A')}
Experience: {context.get('experience_required', 'N/A')}
Skills: {context.get('skills_required', 'N/A')}
Description: {context.get('description', 'N/A')[:400]}

Student's Question: {message}

Provide a helpful, professional answer. Keep it brief (2-4 sentences) unless the student asks for detailed information. Use bullet points (•) for lists, never use ** formatting."""
    
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,  # Increased slightly for flexibility but system prompt keeps it concise
            temperature=0.6,  # Slightly lower for more focused responses
            top_p=0.9
        )
        
        answer = response.choices[0].message.content
        
        # Clean up any remaining ** formatting that might slip through
        answer = answer.replace("**", "")
        
        return {
            "success": True,
            "response": answer.strip()
        }
    except Exception as e:
        print(f"Job question error: {e}")
        return {
            "success": False,
            "response": "I'm having trouble right now. Please try again in a moment."
        }

@router.delete("/history")
async def clear_chat_history(current_user: dict = Depends(get_current_user)):
    """Clear chat history"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can access career coach")
    
    try:
        db = get_database()
        db.career_coach_chats.delete_one({"user_id": current_user["user_id"]})
        return {"success": True, "message": "Chat history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")