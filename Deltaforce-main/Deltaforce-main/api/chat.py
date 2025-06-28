"""
Chat API endpoints for conversational interface
"""
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import asyncio
import logging
from datetime import datetime
import uuid

from agents.conversation_agent import ConversationAgent
from agents.voice_agent import VoiceAgent
from agents.query_agent import QueryAgent
from agents.execution_agent import ExecutionAgent
from agents.visualization_agent import VisualizationAgent
from agents.base_agent import AgentCoordinator
from api.middleware.auth import AuthMiddleware
from api.middleware.security import SecurityMiddleware
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Authentication middleware
auth = AuthMiddleware()

# Global agent coordinator
agent_coordinator = AgentCoordinator()

# Pydantic models for request/response
class ChatMessage(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    user_id: Optional[str] = Field("anonymous", description="User identifier")
    message_type: str = Field("text", description="Type of message: text, voice, query")
    context: Optional[Dict[str, Any]] = Field({}, description="Additional context")
    preferences: Optional[Dict[str, Any]] = Field({}, description="User preferences")

class ChatResponse(BaseModel):
    success: bool
    session_id: str
    response: str
    response_type: str
    conversation_state: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    timestamp: str
    processing_time: float

class SessionRequest(BaseModel):
    user_id: Optional[str] = Field("anonymous", description="User identifier")
    preferences: Optional[Dict[str, Any]] = Field({}, description="User preferences")

class SessionResponse(BaseModel):
    success: bool
    session_id: str
    welcome_message: str
    session_info: Dict[str, Any]

class MultiTurnRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="List of conversation messages")
    session_id: Optional[str] = Field(None, description="Session ID")
    process_all: bool = Field(True, description="Process all messages or stop on error")

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, str] = {}  # session_id -> connection_id
    
    async def connect(self, websocket: WebSocket, connection_id: str, session_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.session_connections[session_id] = connection_id
        logger.info(f"🔗 WebSocket connected: {connection_id} (session: {session_id})")
    
    def disconnect(self, connection_id: str, session_id: str):
        """Remove connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if session_id in self.session_connections:
            del self.session_connections[session_id]
        logger.info(f"🔌 WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: str, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(message)
    
    async def send_to_session(self, message: str, session_id: str):
        """Send message to session"""
        if session_id in self.session_connections:
            connection_id = self.session_connections[session_id]
            await self.send_personal_message(message, connection_id)

# Global connection manager
manager = ConnectionManager()

@router.on_event("startup")
async def startup_chat_service():
    """Initialize chat service and agents"""
    global agent_coordinator
    
    try:
        # Load configuration
        config = {}  # Would load from config file
        
        # Initialize agents
        conversation_agent = ConversationAgent(config)
        voice_agent = VoiceAgent(config)
        query_agent = QueryAgent(config)
        execution_agent = ExecutionAgent(config)
        visualization_agent = VisualizationAgent(config)
        
        # Register agents with coordinator
        agent_coordinator.register_agent(conversation_agent)
        agent_coordinator.register_agent(voice_agent)
        agent_coordinator.register_agent(query_agent)
        agent_coordinator.register_agent(execution_agent)
        agent_coordinator.register_agent(visualization_agent)
        
        # Activate all agents
        await agent_coordinator.activate_all()
        
        logger.info("🚀 Chat service initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Chat service initialization failed: {e}")
        raise

@router.post("/start-session", response_model=SessionResponse)
async def start_chat_session(
    request: SessionRequest,
    current_user: Dict = Depends(auth.get_current_user)
) -> SessionResponse:
    """Start a new chat session"""
    
    try:
        session_id = f"chat_{uuid.uuid4().hex[:8]}"
        
        # Get conversation agent
        conversation_agent = agent_coordinator.agents.get("ConversationAgent")
        if not conversation_agent:
            raise HTTPException(status_code=500, detail="Conversation agent not available")
        
        # Start session
        session_result = await conversation_agent.execute({
            "type": "start_session",
            "session_id": session_id,
            "user_id": request.user_id or current_user.get("user_id", "anonymous"),
            "preferences": request.preferences
        })
        
        if not session_result.get("success"):
            raise HTTPException(status_code=500, detail="Failed to start session")
        
        return SessionResponse(
            success=True,
            session_id=session_id,
            welcome_message=session_result["welcome_message"],
            session_info=session_result["session_info"]
        )
        
    except Exception as e:
        logger.error(f"❌ Session start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    request: ChatMessage,
    current_user: Dict = Depends(auth.get_current_user)
) -> ChatResponse:
    """Send a message in a chat session"""
    
    start_time = datetime.now()
    
    try:
        # Generate session ID if not provided
        if not request.session_id:
            request.session_id = f"chat_{uuid.uuid4().hex[:8]}"
        
        # Process message based on type
        if request.message_type == "voice":
            response = await _process_voice_message(request, current_user)
        elif request.message_type == "query":
            response = await _process_query_message(request, current_user)
        else:
            response = await _process_text_message(request, current_user)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Send to WebSocket if connected
        if request.session_id in manager.session_connections:
            await manager.send_to_session(
                json.dumps(response.dict()),
                request.session_id
            )
        
        response.processing_time = processing_time
        return response
        
    except Exception as e:
        logger.error(f"❌ Message processing failed: {e}")
        
        error_response = ChatResponse(
            success=False,
            session_id=request.session_id or "unknown",
            response=f"I'm sorry, I encountered an error: {str(e)}",
            response_type="error",
            timestamp=datetime.now().isoformat(),
            processing_time=(datetime.now() - start_time).total_seconds()
        )
        
        return error_response

@router.post("/end-session")
async def end_chat_session(
    session_id: str,
    save_history: bool = True,
    current_user: Dict = Depends(auth.get_current_user)
):
    """End a chat session"""
    
    try:
        conversation_agent = agent_coordinator.agents.get("ConversationAgent")
        if not conversation_agent:
            raise HTTPException(status_code=500, detail="Conversation agent not available")
        
        result = await conversation_agent.execute({
            "type": "end_session",
            "session_id": session_id,
            "save_history": save_history
        })
        
        # Disconnect WebSocket if exists
        if session_id in manager.session_connections:
            connection_id = manager.session_connections[session_id]
            manager.disconnect(connection_id, session_id)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Session end failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/multi-turn", response_model=List[ChatResponse])
async def process_multi_turn(
    request: MultiTurnRequest,
    current_user: Dict = Depends(auth.get_current_user)
) -> List[ChatResponse]:
    """Process multiple messages in sequence"""
    
    responses = []
    session_id = request.session_id or f"multi_{uuid.uuid4().hex[:8]}"
    
    try:
        for message in request.messages:
            message.session_id = session_id
            
            try:
                response = await send_chat_message(message, current_user)
                responses.append(response)
                
                # Stop on error if requested
                if not response.success and not request.process_all:
                    break
                    
            except Exception as e:
                error_response = ChatResponse(
                    success=False,
                    session_id=session_id,
                    response=f"Error processing message: {str(e)}",
                    response_type="error",
                    timestamp=datetime.now().isoformat(),
                    processing_time=0.0
                )
                responses.append(error_response)
                
                if not request.process_all:
                    break
        
        return responses
        
    except Exception as e:
        logger.error(f"❌ Multi-turn processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}/context")
async def get_session_context(
    session_id: str,
    include_history: bool = False,
    current_user: Dict = Depends(auth.get_current_user)
):
    """Get conversation context for a session"""
    
    try:
        conversation_agent = agent_coordinator.agents.get("ConversationAgent")
        if not conversation_agent:
            raise HTTPException(status_code=500, detail="Conversation agent not available")
        
        result = await conversation_agent.execute({
            "type": "get_context",
            "session_id": session_id,
            "include_history": include_history
        })
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Context retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}/export")
async def export_conversation(
    session_id: str,
    format: str = "json",
    current_user: Dict = Depends(auth.get_current_user)
):
    """Export conversation history"""
    
    try:
        conversation_agent = agent_coordinator.agents.get("ConversationAgent")
        if not conversation_agent:
            raise HTTPException(status_code=500, detail="Conversation agent not available")
        
        result = await conversation_agent.export_conversation(session_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Session not found")
        
        export_data = result["export_data"]
        
        if format == "json":
            return export_data
        elif format == "csv":
            # Convert to CSV format
            import pandas as pd
            df = pd.DataFrame(export_data["conversation"])
            csv_data = df.to_csv(index=False)
            
            return StreamingResponse(
                iter([csv_data]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=conversation_{session_id}.csv"}
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
        
    except Exception as e:
        logger.error(f"❌ Conversation export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    
    connection_id = f"ws_{uuid.uuid4().hex[:8]}"
    
    try:
        await manager.connect(websocket, connection_id, session_id)
        
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "Connected to CCTNS Chat",
            "session_id": session_id,
            "connection_id": connection_id
        }))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Create chat message
            chat_message = ChatMessage(
                message=message_data.get("message", ""),
                session_id=session_id,
                message_type=message_data.get("type", "text"),
                context=message_data.get("context", {})
            )
            
            # Process message (without auth for WebSocket)
            try:
                if chat_message.message_type == "voice":
                    response = await _process_voice_message(chat_message, {"user_id": "websocket"})
                elif chat_message.message_type == "query":
                    response = await _process_query_message(chat_message, {"user_id": "websocket"})
                else:
                    response = await _process_text_message(chat_message, {"user_id": "websocket"})
                
                # Send response
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "data": response.dict()
                }))
                
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(connection_id, session_id)
        logger.info(f"🔌 WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        manager.disconnect(connection_id, session_id)

@router.get("/status")
async def get_chat_status(current_user: Dict = Depends(auth.get_current_user)):
    """Get chat service status"""
    
    try:
        # Get agent statuses
        agent_statuses = agent_coordinator.get_all_status()
        
        # Get conversation stats
        conversation_agent = agent_coordinator.agents.get("ConversationAgent")
        conversation_stats = {}
        if conversation_agent:
            conversation_stats = await conversation_agent.get_conversation_stats()
        
        return {
            "service_status": "running",
            "active_agents": len(agent_coordinator.agents),
            "active_websockets": len(manager.active_connections),
            "active_sessions": len(manager.session_connections),
            "agent_statuses": agent_statuses,
            "conversation_stats": conversation_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def _process_text_message(request: ChatMessage, current_user: Dict) -> ChatResponse:
    """Process regular text message"""
    
    conversation_agent = agent_coordinator.agents.get("ConversationAgent")
    if not conversation_agent:
        raise HTTPException(status_code=500, detail="Conversation agent not available")
    
    result = await conversation_agent.execute({
        "type": "turn",
        "message": request.message,
        "session_id": request.session_id,
        "user_id": request.user_id or current_user.get("user_id", "anonymous")
    })
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
    
    # Generate suggestions based on response type
    suggestions = await _generate_suggestions(result["response_type"], request.message)
    
    return ChatResponse(
        success=True,
        session_id=request.session_id,
        response=result["response"],
        response_type=result["response_type"],
        conversation_state=result.get("conversation_state"),
        suggestions=suggestions,
        timestamp=datetime.now().isoformat(),
        processing_time=0.0  # Will be set by caller
    )

async def _process_voice_message(request: ChatMessage, current_user: Dict) -> ChatResponse:
    """Process voice message"""
    
    # Would implement voice processing workflow
    # For now, return placeholder
    
    return ChatResponse(
        success=True,
        session_id=request.session_id,
        response="Voice processing not yet implemented. Please use text input.",
        response_type="voice_error",
        timestamp=datetime.now().isoformat(),
        processing_time=0.0
    )

async def _process_query_message(request: ChatMessage, current_user: Dict) -> ChatResponse:
    """Process query message that requires database access"""
    
    try:
        # Execute workflow: conversation -> query -> execution -> visualization
        workflow = [
            {
                "agent": "ConversationAgent",
                "input": {
                    "type": "turn",
                    "message": request.message,
                    "session_id": request.session_id,
                    "user_id": request.user_id or current_user.get("user_id", "anonymous")
                }
            },
            {
                "agent": "QueryAgent", 
                "input": {
                    "type": "standard",
                    "text": request.message,
                    "context": request.context
                }
            },
            {
                "agent": "ExecutionAgent",
                "input": {
                    "type": "execute_sql",
                    "use_cache": True
                }
            }
        ]
        
        workflow_result = await agent_coordinator.execute_workflow(workflow)
        
        if not workflow_result.get("success"):
            return ChatResponse(
                success=False,
                session_id=request.session_id,
                response="I encountered an issue processing your query. Please try rephrasing it.",
                response_type="query_error",
                timestamp=datetime.now().isoformat(),
                processing_time=0.0
            )
        
        # Extract results
        conversation_result = workflow_result["results"].get("ConversationAgent", {})
        query_result = workflow_result["results"].get("QueryAgent", {})
        execution_result = workflow_result["results"].get("ExecutionAgent", {})
        
        # Format response
        if execution_result.get("success") and execution_result.get("result", {}).get("success"):
            data = execution_result["result"]["data"]
            row_count = len(data)
            
            response_text = f"I found {row_count} results for your query"
            if row_count > 0:
                response_text += f". Here's a summary of the data..."
            
            return ChatResponse(
                success=True,
                session_id=request.session_id,
                response=response_text,
                response_type="query_success",
                conversation_state=conversation_result.get("result", {}).get("conversation_state"),
                timestamp=datetime.now().isoformat(),
                processing_time=0.0
            )
        else:
            return ChatResponse(
                success=False,
                session_id=request.session_id,
                response="I couldn't execute your query. Please check if the request is valid.",
                response_type="query_failed",
                timestamp=datetime.now().isoformat(),
                processing_time=0.0
            )
    
    except Exception as e:
        logger.error(f"❌ Query processing failed: {e}")
        return ChatResponse(
            success=False,
            session_id=request.session_id,
            response=f"Query processing error: {str(e)}",
            response_type="query_error",
            timestamp=datetime.now().isoformat(),
            processing_time=0.0
        )

async def _generate_suggestions(response_type: str, message: str) -> List[str]:
    """Generate contextual suggestions for next user input"""
    
    suggestions = []
    
    if response_type == "greeting":
        suggestions = [
            "Show me recent FIRs from Guntur district",
            "How many arrests were made this month?",
            "List police officers in Krishna district"
        ]
    elif response_type == "query_success":
        suggestions = [
            "Show me a chart of this data",
            "Get more details about these results",
            "Export this data to CSV"
        ]
    elif response_type == "query_failed":
        suggestions = [
            "Try asking about FIR data",
            "Ask for help with query format",
            "Check available districts"
        ]
    elif "error" in response_type:
        suggestions = [
            "Ask for help",
            "Try a simpler question",
            "Start over"
        ]
    else:
        # Default suggestions based on keywords in message
        if "fir" in message.lower():
            suggestions = [
                "Show FIR statistics by district",
                "Get recent FIR reports",
                "Find FIRs by crime type"
            ]
        elif "arrest" in message.lower():
            suggestions = [
                "Show arrest statistics",
                "Get arrest reports by date",
                "Find arrests by officer"
            ]
        else:
            suggestions = [
                "What can you help me with?",
                "Show me police data",
                "Get crime statistics"
            ]
    
    return suggestions[:3] 