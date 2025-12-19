from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from services import llm
from models.domain import ChatMessageIn
from services import chat

class RenameChatRequest(BaseModel):
    title: str

router = APIRouter(prefix="/topologies", tags=["LLM", "Chat"])

@router.get("/{topology_id}/chat")
def get_chat_sessions(topology_id: str):
    return chat.get_chat_sessions_by_topology(topology_id)

@router.delete("/{topology_id}/chat/{session_id}")
def delete_chat_session(session_id: str):
    chat_id = chat.delete_chat_session_by_id(session_id)
    return {"status": "deleted", "id": chat_id}

@router.put("/{topology_id}/chat/{session_id}")
async def rename_chat_session(session_id: str, request: RenameChatRequest):
    chat_id = await run_in_threadpool(
        chat.rename_chat_session,
        session_id,
        request.title
    )
    return {"status": "renamed", "id": chat_id}

@router.get("/{topology_id}/chat/{session_id}/history")
def get_chat_history(topology_id: str, session_id: str):
    history = chat.get_chat_history_by_session(session_id, topology_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found in this topology")
    return history

@router.post("/{topology_id}/chat/{session_id}/ask")
async def send_message(topology_id: str, session_id: str, msg: ChatMessageIn):
    current_session_id = session_id
    
    if session_id == "new":
        topology_exists = await run_in_threadpool(
            chat.check_topology_exists,
            topology_id
        )
        if not topology_exists:
            raise HTTPException(status_code=404, detail="Topology not found")
        
        session_title = (msg.content[:30] + '...') if len(msg.content) > 30 else msg.content
        
        current_session_id = await run_in_threadpool(
            chat.create_chat_session,
            topology_id,
            session_title,
            'ask',
            msg.model
        )
        conversation_history = []
    else:
        current_session_id = session_id
        conversation_history = await run_in_threadpool(
            chat.get_conversation_history,
            current_session_id
        )

    await run_in_threadpool(
        chat.save_chat_message,
        current_session_id,
        "user",
        msg.content
    )

    conversation_history_limited = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
    
    payload = {
        "query": msg.content,
        "mode": "mix",
        "only_need_context": False,
        "only_need_prompt": False,
        "response_type": "Multiple Paragraphs",
        "top_k": 60,
        "chunk_top_k": 10,
        "max_entity_tokens": 1000,
        "max_relation_tokens": 1000,
        "max_total_tokens": 4096,
        "conversation_history": conversation_history_limited,
        "enable_rerank": False,
        "include_references": False,
        "include_chunk_content": False,
        "stream": True
    }

    return StreamingResponse(
        llm.response_generator(current_session_id=current_session_id, payload=payload, model=msg.model), 
        media_type="text/event-stream", 
        headers={"X-Session-ID": str(current_session_id)}
    )

@router.post("/{topology_id}/chat/{session_id}/agent")
async def send_message_agent(topology_id: str, session_id: str, msg: ChatMessageIn):
    current_session_id = session_id
    
    if session_id == "new":
        topology_exists = await run_in_threadpool(
            chat.check_topology_exists,
            topology_id
        )
        if not topology_exists:
            raise HTTPException(status_code=404, detail="Topology not found")
        
        session_title = (msg.content[:30] + '...') if len(msg.content) > 30 else msg.content
        
        current_session_id = await run_in_threadpool(
            chat.create_chat_session,
            topology_id,
            session_title,
            'agent',
            msg.model
        )

    await run_in_threadpool(
        chat.save_chat_message,
        current_session_id,
        "user",
        msg.content
    )

    history = await run_in_threadpool(
        chat.get_conversation_history,
        current_session_id,
        2
    )

    # 4. Run Agent Loop (Streaming)
    import json
    async def response_generator():
        full_response = ""
        
        # Stream chunks from the agent
        async for chunk_str in llm.run_agent_loop(topology_id, msg.content, history, msg.model, current_session_id):
            
            try:
                data = json.loads(chunk_str)
                text = data.get("text", "")
                full_response += text

                # Yield SSE format
                yield f"data: {chunk_str}\n\n"
            except:
                pass

        # 5. Save Final Assistant Response
        if full_response:
             await run_in_threadpool(
                chat.save_chat_message,
                current_session_id,
                "assistant",
                full_response
            )

    return StreamingResponse(
        response_generator(), 
        media_type="text/event-stream", 
        headers={"X-Session-ID": str(current_session_id)}
    )

@router.post("/{topology_id}/chat/{session_id}/local")
async def send_message_local(topology_id: str, session_id: str, msg: ChatMessageIn):
    current_session_id = session_id
    
    if session_id == "new":
        topology_exists = await run_in_threadpool(
            chat.check_topology_exists,
            topology_id
        )
        if not topology_exists:
            raise HTTPException(status_code=404, detail="Topology not found")
        
        session_title = (msg.content[:30] + '...') if len(msg.content) > 30 else msg.content
        
        current_session_id = await run_in_threadpool(
            chat.create_chat_session,
            topology_id,
            session_title,
            'local',
            msg.model
        )
        conversation_history = []
    else:
        current_session_id = session_id
        conversation_history = await run_in_threadpool(
            chat.get_conversation_history,
            current_session_id,
            2
        )

    await run_in_threadpool(
        chat.save_chat_message,
        current_session_id,
        "user",
        msg.content
    )

    conversation_history_limited = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
    
    payload = {
        "query": msg.content,
        "mode": "local",
        "only_need_context": False,
        "only_need_prompt": False,
        "response_type": "Multiple Paragraphs",
        "top_k": 60,
        "chunk_top_k": 10,
        "max_entity_tokens": 1000,
        "max_relation_tokens": 1000,
        "max_total_tokens": 4096,
        "conversation_history": conversation_history_limited,
        "enable_rerank": False,
        "include_references": False,
        "include_chunk_content": False,
        "stream": True
    }

    return StreamingResponse(
        llm.response_generator(current_session_id=current_session_id, payload=payload, model=msg.model), 
        media_type="text/event-stream", 
        headers={"X-Session-ID": str(current_session_id)}
    )

@router.post("/{topology_id}/chat/{session_id}/stop")
def stop_agent_chat(session_id: str):
    success = llm.stop_agent_task(session_id)
    if success:
        return {"status": "stopped", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="No active agent task found for this session")
