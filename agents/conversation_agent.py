"""
Conversation Agent for managing multi-turn conversations and context
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from .base_agent import BaseAgent

class ConversationAgent(BaseAgent):
    """Agent specialized in conversation management and context tracking"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("ConversationAgent", config)
        
        # Conversation settings
        self.max_conversation_length = config.get("max_conversation_length", 50)
        self.context_window_size = config.get("context_window_size", 10)
        self.session_timeout_minutes = config.get("session_timeout_minutes", 30)
        
        # Conversation state
        self.active_sessions = {}
        self.conversation_templates = {
            "greeting": [
                "Hello! I'm your CCTNS assistant. How can I help you today?",
                "Welcome to CCTNS Copilot. What would you like to know?", 
                "Hi there! I can help you with police data queries. What do you need?"
            ],
            "clarification": [
                "Could you please be more specific about what you're looking for?",
                "I need a bit more information to help you better.",
                "Can you provide more details about your request?"
            ],
            "error": [
                "I'm sorry, I couldn't process that request. Could you try rephrasing?",
                "There seems to be an issue. Let me try to help you differently.",
                "I encountered a problem. Could you please try again?"
            ],
            "goodbye": [
                "Thank you for using CCTNS Copilot. Have a great day!",
                "Goodbye! Feel free to return if you need more assistance.",
                "See you later! I'm always here to help with CCTNS queries."
            ]
        }
        
        # Intent patterns
        self.intent_patterns = {
            "greeting": ["hello", "hi", "hey", "good morning", "good afternoon"],
            "goodbye": ["bye", "goodbye", "see you", "thanks", "thank you"],
            "help": ["help", "what can you do", "how do you work", "guide"],
            "query": ["show", "get", "find", "how many", "list", "count"],
            "clarification": ["what do you mean", "explain", "more details", "unclear"]
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process conversation input and manage dialogue flow"""
        
        conversation_type = input_data.get("type", "turn")
        
        if conversation_type == "turn":
            return await self._process_conversation_turn(input_data)
        elif conversation_type == "start_session":
            return await self._start_conversation_session(input_data)
        elif conversation_type == "end_session":
            return await self._end_conversation_session(input_data)
        elif conversation_type == "get_context":
            return await self._get_conversation_context(input_data)
        else:
            raise ValueError(f"Unsupported conversation type: {conversation_type}")
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate conversation input"""
        base_validation = await super()._validate_input(input_data)
        if not base_validation["valid"]:
            return base_validation
        
        if input_data.get("type") == "turn":
            if not input_data.get("message"):
                return {"valid": False, "reason": "Message is required for conversation turn"}
            
            if not input_data.get("session_id"):
                return {"valid": False, "reason": "Session ID is required"}
        
        return {"valid": True}
    
    async def _process_conversation_turn(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single conversation turn"""
        
        session_id = input_data.get("session_id")
        user_message = input_data.get("message", "").strip()
        user_id = input_data.get("user_id", "anonymous")
        
        self.logger.info(f"💬 Processing conversation turn for session {session_id}")
        
        try:
            # Get or create session
            session = await self._get_or_create_session(session_id, user_id)
            
            # Add user message to conversation
            session["conversation"].append({
                "role": "user",
                "message": user_message,
                "timestamp": datetime.now().isoformat(),
                "intent": await self._detect_intent(user_message)
            })
            
            # Generate response
            response_data = await self._generate_response(session, user_message)
            
            # Add assistant response to conversation
            session["conversation"].append({
                "role": "assistant",
                "message": response_data["message"],
                "timestamp": datetime.now().isoformat(),
                "response_type": response_data["type"],
                "confidence": response_data.get("confidence", 1.0)
            })
            
            # Update session metadata
            session["last_activity"] = datetime.now()
            session["turn_count"] += 1
            
            # Maintain conversation length
            if len(session["conversation"]) > self.max_conversation_length:
                session["conversation"] = session["conversation"][-self.max_conversation_length:]
            
            # Update session context
            await self._update_session_context(session, user_message, response_data)
            
            return {
                "success": True,
                "session_id": session_id,
                "response": response_data["message"],
                "response_type": response_data["type"],
                "conversation_state": {
                    "turn_count": session["turn_count"],
                    "context_items": len(session["context"]),
                    "last_intent": session["conversation"][-2]["intent"]
                },
                "context_updates": {
                    "current_session": session_id,
                    "conversation_active": True,
                    "last_user_intent": session["conversation"][-2]["intent"]
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Conversation turn failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "response": "I'm sorry, I encountered an error. Please try again."
            }
    
    async def _start_conversation_session(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new conversation session"""
        
        user_id = input_data.get("user_id", "anonymous")
        session_id = input_data.get("session_id") or self._generate_session_id()
        
        self.logger.info(f"🆕 Starting conversation session {session_id}")
        
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "conversation": [],
            "context": {},
            "turn_count": 0,
            "preferences": input_data.get("preferences", {})
        }
        
        self.active_sessions[session_id] = session
        
        # Generate welcome message
        welcome_message = await self._generate_welcome_message(session)
        
        session["conversation"].append({
            "role": "assistant",
            "message": welcome_message,
            "timestamp": datetime.now().isoformat(),
            "response_type": "greeting"
        })
        
        return {
            "success": True,
            "session_id": session_id,
            "welcome_message": welcome_message,
            "session_info": {
                "created_at": session["created_at"].isoformat(),
                "user_id": user_id
            }
        }
    
    async def _end_conversation_session(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """End a conversation session"""
        
        session_id = input_data.get("session_id")
        save_history = input_data.get("save_history", True)
        
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Generate goodbye message
        goodbye_message = await self._generate_goodbye_message(session)
        
        session["conversation"].append({
            "role": "assistant",
            "message": goodbye_message,
            "timestamp": datetime.now().isoformat(),
            "response_type": "goodbye"
        })
        
        # Save session summary
        session_summary = {
            "session_id": session_id,
            "user_id": session["user_id"],
            "duration_minutes": (datetime.now() - session["created_at"]).total_seconds() / 60,
            "total_turns": session["turn_count"],
            "ended_at": datetime.now().isoformat()
        }
        
        if save_history:
            # In a real implementation, this would save to database
            self.logger.info(f"💾 Saving conversation history for session {session_id}")
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        self.logger.info(f"👋 Ended conversation session {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "goodbye_message": goodbye_message,
            "session_summary": session_summary
        }
    
    async def _get_conversation_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get conversation context for a session"""
        
        session_id = input_data.get("session_id")
        include_history = input_data.get("include_history", False)
        
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        context_data = {
            "session_id": session_id,
            "context": session["context"].copy(),
            "current_turn": session["turn_count"],
            "session_age_minutes": (datetime.now() - session["created_at"]).total_seconds() / 60
        }
        
        if include_history:
            context_data["conversation_history"] = session["conversation"][-self.context_window_size:]
        
        return {
            "success": True,
            "context_data": context_data
        }
    
    async def _get_or_create_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Get existing session or create new one"""
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Check if session has expired
            if self._is_session_expired(session):
                del self.active_sessions[session_id]
                return await self._create_new_session(session_id, user_id)
            
            return session
        else:
            return await self._create_new_session(session_id, user_id)
    
    async def _create_new_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Create a new conversation session"""
        
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "conversation": [],
            "context": {},
            "turn_count": 0,
            "preferences": {}
        }
        
        self.active_sessions[session_id] = session
        return session
    
    def _is_session_expired(self, session: Dict[str, Any]) -> bool:
        """Check if session has expired"""
        last_activity = session["last_activity"]
        timeout_delta = timedelta(minutes=self.session_timeout_minutes)
        return datetime.now() - last_activity > timeout_delta
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        import uuid
        return f"session_{uuid.uuid4().hex[:8]}"
    
    async def _detect_intent(self, message: str) -> str:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    return intent
        
        # Default intent based on content
        if any(word in message_lower for word in ["show", "get", "find", "how many", "list", "count"]):
            return "query"
        elif "?" in message:
            return "question"
        else:
            return "statement"
    
    async def _generate_response(self, session: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Generate appropriate response based on conversation context"""
        
        last_user_intent = session["conversation"][-1]["intent"]
        conversation_history = session["conversation"][-self.context_window_size:]
        
        # Determine response type
        if last_user_intent == "greeting":
            return {
                "message": self._get_template_response("greeting"),
                "type": "greeting",
                "confidence": 1.0
            }
        
        elif last_user_intent == "goodbye":
            return {
                "message": self._get_template_response("goodbye"),
                "type": "goodbye",
                "confidence": 1.0
            }
        
        elif last_user_intent == "help":
            return {
                "message": await self._generate_help_response(),
                "type": "help",
                "confidence": 1.0
            }
        
        elif last_user_intent == "query":
            return await self._generate_query_response(session, user_message)
        
        elif last_user_intent == "clarification":
            return {
                "message": self._get_template_response("clarification"),
                "type": "clarification",
                "confidence": 0.8
            }
        
        else:
            # Context-aware response
            return await self._generate_contextual_response(session, user_message)
    
    async def _generate_query_response(self, session: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Generate response for query intent"""
        
        # Check if this is a follow-up query
        recent_queries = [
            turn for turn in session["conversation"][-5:]
            if turn["role"] == "user" and turn.get("intent") == "query"
        ]
        
        if len(recent_queries) > 1:
            # Follow-up query
            message = f"I understand you want to know about: '{user_message}'. Let me process this query for you."
            response_type = "followup_query"
        else:
            # New query
            message = f"I'll help you with that query: '{user_message}'. Processing your request now."
            response_type = "new_query"
        
        return {
            "message": message,
            "type": response_type,
            "confidence": 0.9,
            "requires_processing": True,
            "query_text": user_message
        }
    
    async def _generate_contextual_response(self, session: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """Generate contextual response based on conversation history"""
        
        # Analyze recent conversation for context
        recent_turns = session["conversation"][-3:]
        
        # Check for patterns
        if any("error" in turn.get("response_type", "") for turn in recent_turns):
            message = "I notice you've been having some issues. Let me try to help you more specifically. What exactly are you looking for?"
            response_type = "recovery"
        
        elif len([t for t in recent_turns if t["role"] == "user"]) > 1:
            message = f"Thanks for the additional information. Regarding '{user_message}', let me see how I can assist you."
            response_type = "continuation"
        
        else:
            message = f"I understand you mentioned: '{user_message}'. How can I help you with this?"
            response_type = "acknowledgment"
        
        return {
            "message": message,
            "type": response_type,
            "confidence": 0.7
        }
    
    async def _generate_welcome_message(self, session: Dict[str, Any]) -> str:
        """Generate personalized welcome message"""
        
        user_id = session["user_id"]
        preferences = session.get("preferences", {})
        
        base_welcome = self._get_template_response("greeting")
        
        # Personalize based on preferences
        if preferences.get("language") == "hindi":
            base_welcome = "नमस्ते! मैं आपका CCTNS सहायक हूँ। आज मैं आपकी कैसे मदद कर सकता हूँ?"
        elif preferences.get("language") == "telugu":
            base_welcome = "నమస్కారం! నేను మీ CCTNS సహాయకుడను. ఈరోజు నేను మీకు ఎలా సహాయం చేయగలను?"
        
        if user_id != "anonymous":
            base_welcome = f"Welcome back! {base_welcome}"
        
        return base_welcome
    
    async def _generate_goodbye_message(self, session: Dict[str, Any]) -> str:
        """Generate personalized goodbye message"""
        
        duration = (datetime.now() - session["created_at"]).total_seconds() / 60
        turn_count = session["turn_count"]
        
        base_goodbye = self._get_template_response("goodbye")
        
        if turn_count > 5:
            base_goodbye = f"Thank you for the engaging conversation! {base_goodbye}"
        elif duration > 30:
            base_goodbye = f"Thanks for spending time with me today. {base_goodbye}"
        
        return base_goodbye
    
    async def _generate_help_response(self) -> str:
        """Generate help response"""
        
        return """I can help you with various CCTNS queries:

🔍 **Query Examples:**
- "Show me FIRs from Guntur district"
- "How many arrests were made last month?"
- "List officers in Krishna district"

🎤 **Voice Support:**
- Speak in Telugu, Hindi, or English
- Upload audio files for transcription

📊 **Visualizations:**
- Automatic charts from your data
- Crime statistics and trends

💬 **Conversation:**
- Ask follow-up questions
- I remember our conversation context

Just ask me anything about police data and I'll help you find the information you need!"""
    
    def _get_template_response(self, template_type: str) -> str:
        """Get random response from template"""
        import random
        templates = self.conversation_templates.get(template_type, ["I understand."])
        return random.choice(templates)
    
    async def _update_session_context(self, session: Dict[str, Any], user_message: str, response_data: Dict[str, Any]):
        """Update session context with relevant information"""
        
        # Extract entities and keywords from user message
        keywords = await self._extract_keywords(user_message)
        entities = await self._extract_entities(user_message)
        
        # Update context
        session["context"].update({
            "last_user_message": user_message,
            "last_response_type": response_data["type"],
            "recent_keywords": keywords,
            "entities": entities,
            "last_intent": session["conversation"][-2]["intent"]
        })
        
        # Maintain context size
        if len(session["context"]) > 20:
            # Keep only most recent context items
            recent_keys = ["last_user_message", "last_response_type", "recent_keywords", "entities", "last_intent"]
            session["context"] = {k: v for k, v in session["context"].items() if k in recent_keys}
    
    async def _extract_keywords(self, message: str) -> List[str]:
        """Extract keywords from message"""
        # Simple keyword extraction
        import re
        
        # CCTNS-specific keywords
        cctns_keywords = ["fir", "arrest", "officer", "station", "district", "crime", "police"]
        
        message_lower = message.lower()
        found_keywords = []
        
        for keyword in cctns_keywords:
            if keyword in message_lower:
                found_keywords.append(keyword)
        
        # Extract district names
        districts = ["guntur", "vijayawada", "visakhapatnam", "krishna", "kurnool"]
        for district in districts:
            if district in message_lower:
                found_keywords.append(district)
        
        return found_keywords
    
    async def _extract_entities(self, message: str) -> Dict[str, List[str]]:
        """Extract named entities from message"""
        # Simple entity extraction
        entities = {
            "districts": [],
            "dates": [],
            "numbers": []
        }
        
        # Extract districts
        districts = ["Guntur", "Vijayawada", "Visakhapatnam", "Krishna", "Kurnool"]
        for district in districts:
            if district.lower() in message.lower():
                entities["districts"].append(district)
        
        # Extract numbers
        import re
        numbers = re.findall(r'\d+', message)
        entities["numbers"] = numbers
        
        return entities
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if self._is_session_expired(session):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
            self.logger.info(f"🧹 Cleaned up expired session: {session_id}")
        
        return len(expired_sessions)
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        active_count = len(self.active_sessions)
        total_turns = sum(session["turn_count"] for session in self.active_sessions.values())
        
        avg_session_duration = 0
        if self.active_sessions:
            durations = [
                (datetime.now() - session["created_at"]).total_seconds() / 60
                for session in self.active_sessions.values()
            ]
            avg_session_duration = sum(durations) / len(durations)
        
        return {
            "agent_stats": self.get_status(),
            "conversation_specific": {
                "active_sessions": active_count,
                "total_conversation_turns": total_turns,
                "avg_session_duration_minutes": round(avg_session_duration, 2),
                "max_conversation_length": self.max_conversation_length,
                "session_timeout_minutes": self.session_timeout_minutes,
                "available_intents": list(self.intent_patterns.keys()),
                "template_types": list(self.conversation_templates.keys())
            }
        }
    
    async def export_conversation(self, session_id: str) -> Dict[str, Any]:
        """Export conversation history"""
        
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        export_data = {
            "session_id": session_id,
            "user_id": session["user_id"],
            "created_at": session["created_at"].isoformat(),
            "last_activity": session["last_activity"].isoformat(),
            "total_turns": session["turn_count"],
            "conversation": session["conversation"],
            "final_context": session["context"],
            "exported_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "export_data": export_data
        }