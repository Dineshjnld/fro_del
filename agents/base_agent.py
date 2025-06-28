"""
Base Agent class for CCTNS Copilot Engine
Provides common functionality for all specialized agents
"""
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime
import uuid

class BaseAgent(ABC):
    """Base class for all CCTNS agents"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"Agent.{name}")
        
        # Agent state
        self.agent_id = str(uuid.uuid4())
        self.is_active = False
        self.created_at = datetime.now()
        self.last_activity = None
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "total_response_time": 0.0
        }
        
        # Context management
        self.context = {}
        self.conversation_history = []
        
        self.logger.info(f"🤖 Agent {self.name} initialized with ID: {self.agent_id}")
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return result - must be implemented by subclasses"""
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method with error handling and metrics"""
        start_time = time.time()
        self.metrics["total_requests"] += 1
        self.last_activity = datetime.now()
        
        try:
            self.logger.info(f"🔄 Processing request: {input_data.get('type', 'unknown')}")
            
            # Validate input
            validation_result = await self._validate_input(input_data)
            if not validation_result["valid"]:
                raise ValueError(f"Input validation failed: {validation_result['reason']}")
            
            # Pre-processing
            processed_input = await self._preprocess_input(input_data)
            
            # Main processing
            result = await self.process(processed_input)
            
            # Post-processing
            final_result = await self._postprocess_output(result)
            
            # Update metrics
            execution_time = time.time() - start_time
            self._update_success_metrics(execution_time)
            
            # Update context
            await self._update_context(input_data, final_result)
            
            self.logger.info(f"✅ Request completed in {execution_time:.2f}s")
            
            return {
                "success": True,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "result": final_result,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_failure_metrics(execution_time)
            
            self.logger.error(f"❌ Processing failed: {str(e)}")
            
            return {
                "success": False,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "error": str(e),
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input data - can be overridden by subclasses"""
        if not isinstance(input_data, dict):
            return {"valid": False, "reason": "Input must be a dictionary"}
        
        return {"valid": True}
    
    async def _preprocess_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess input data - can be overridden by subclasses"""
        return input_data
    
    async def _postprocess_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess output data - can be overridden by subclasses"""
        return output_data
    
    async def _update_context(self, input_data: Dict[str, Any], result: Dict[str, Any]):
        """Update agent context with interaction history"""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "input": input_data,
            "result": result,
            "agent": self.name
        }
        
        self.conversation_history.append(interaction)
        
        # Keep only last 50 interactions
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
        
        # Update context with relevant information
        if "context_updates" in result:
            self.context.update(result["context_updates"])
    
    def _update_success_metrics(self, execution_time: float):
        """Update metrics for successful execution"""
        self.metrics["successful_requests"] += 1
        self.metrics["total_response_time"] += execution_time
        self.metrics["avg_response_time"] = (
            self.metrics["total_response_time"] / self.metrics["total_requests"]
        )
    
    def _update_failure_metrics(self, execution_time: float):
        """Update metrics for failed execution"""
        self.metrics["failed_requests"] += 1
        self.metrics["total_response_time"] += execution_time
        self.metrics["avg_response_time"] = (
            self.metrics["total_response_time"] / self.metrics["total_requests"]
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status and metrics"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "metrics": self.metrics.copy(),
            "context_size": len(self.context),
            "conversation_history_size": len(self.conversation_history)
        }
    
    def get_context(self) -> Dict[str, Any]:
        """Get current agent context"""
        return self.context.copy()
    
    def set_context(self, context: Dict[str, Any]):
        """Set agent context"""
        self.context = context
        self.logger.info(f"🧠 Context updated with {len(context)} items")
    
    def clear_context(self):
        """Clear agent context and conversation history"""
        self.context.clear()
        self.conversation_history.clear()
        self.logger.info("🧹 Context and history cleared")
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        return self.conversation_history[-limit:] if limit > 0 else self.conversation_history
    
    async def activate(self):
        """Activate the agent"""
        self.is_active = True
        self.logger.info(f"🟢 Agent {self.name} activated")
    
    async def deactivate(self):
        """Deactivate the agent"""
        self.is_active = False
        self.logger.info(f"🔴 Agent {self.name} deactivated")
    
    async def reset(self):
        """Reset agent state"""
        self.clear_context()
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "total_response_time": 0.0
        }
        self.logger.info(f"🔄 Agent {self.name} reset")


class AgentCoordinator:
    """Coordinates multiple agents working together"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("AgentCoordinator")
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the coordinator"""
        self.agents[agent.name] = agent
        self.logger.info(f"📝 Registered agent: {agent.name}")
    
    def unregister_agent(self, agent_name: str):
        """Unregister an agent"""
        if agent_name in self.agents:
            del self.agents[agent_name]
            self.logger.info(f"🗑️ Unregistered agent: {agent_name}")
    
    async def execute_workflow(self, workflow: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a workflow across multiple agents"""
        results = {}
        context = {}
        
        try:
            for step in workflow:
                agent_name = step.get("agent")
                input_data = step.get("input", {})
                
                # Add shared context
                input_data["shared_context"] = context
                
                if agent_name not in self.agents:
                    raise ValueError(f"Agent '{agent_name}' not found")
                
                agent = self.agents[agent_name]
                result = await agent.execute(input_data)
                
                results[agent_name] = result
                
                # Update shared context
                if result.get("success") and "context_updates" in result.get("result", {}):
                    context.update(result["result"]["context_updates"])
                
                # Stop on failure if required
                if not result.get("success") and step.get("stop_on_failure", True):
                    break
            
            return {
                "success": True,
                "results": results,
                "final_context": context
            }
            
        except Exception as e:
            self.logger.error(f"❌ Workflow execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "partial_results": results
            }
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all registered agents"""
        return {
            name: agent.get_status() 
            for name, agent in self.agents.items()
        }
    
    async def activate_all(self):
        """Activate all agents"""
        for agent in self.agents.values():
            await agent.activate()
    
    async def deactivate_all(self):
        """Deactivate all agents"""
        for agent in self.agents.values():
            await agent.deactivate()