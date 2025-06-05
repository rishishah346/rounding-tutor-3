"""AI companion that provides motivational messages and learning narration."""

import logging
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

class AICompanion:
    """Manages AI interactions with students."""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service or LLMService()
        self.conversation_history = []
        self.student_profile = {}
        self.current_stage = None
        self.message_count = 0
        
    def generate_message(self, message_type, context=None):
        """Generates appropriate AI messages based on type and context."""
        logger.info(f"Generating AI message of type: {message_type}")
        
        # Limit conversation history to last 5 messages to save tokens
        if len(self.conversation_history) > 5:
            self.conversation_history = self.conversation_history[-5:]
        
        # Clean conversation history before using it
        cleaned_history = []
        for msg in self.conversation_history:
            if isinstance(msg, dict) and 'content' in msg:
                cleaned_msg = msg.copy()
                cleaned_msg['content'] = str(msg['content']).strip()
                cleaned_history.append(cleaned_msg)
        
        # Create prompt based on message type and context
        prompt = self._create_prompt(message_type, context or {})
        
        # Get completion from LLM
        message = self.llm_service.get_completion(prompt, cleaned_history)
        
        # Store this interaction in history (make sure to strip the content)
        self.conversation_history.append({"role": "user", "content": prompt["user"].strip()})
        self.conversation_history.append({"role": "assistant", "content": message.strip()})
        
        # Increment message counter
        self.message_count += 1
        
        return message

    
    def _create_prompt(self, message_type, context):
        """Creates a prompt for the LLM based on message type and context."""
        # Enrich context with current state
        enriched_context = {**context}
        if self.current_stage:
            enriched_context["current_stage"] = self.current_stage
        if self.student_profile:
            enriched_context.update(self.student_profile)
            
        # Add message count to context
        enriched_context["message_count"] = self.message_count
        
        # Base system prompt
        system_prompt = """
        You are an encouraging math tutor assistant helping students learn how to round decimal numbers. 
        Your name is Math Helper. Your personality is friendly, patient, and slightly playful but focused on learning.
        You should be concise (2-3 sentences max per message) and engaging for students aged 10-14.
        
        Your primary goals are:
        1. Motivate students by acknowledging their efforts and progress
        2. Provide age-appropriate encouragement when they struggle
        3. Explain the learning journey clearly
        4. Celebrate achievements meaningfully
        
        Never directly solve problems for students but guide their thinking process.
        """
        
        # Different prompt templates based on message type
        if message_type == "welcome":
            user_prompt = f"""
            Introduce yourself briefly as Math Helper. Mention you're here to help with rounding practice.
            Express enthusiasm about working with the student. Keep it to 2 sentences maximum.
            Current stage: {enriched_context.get('current_stage', 'beginning')}
            """
        elif message_type == "stage_transition":
            user_prompt = f"""
            The student is transitioning from stage {enriched_context.get('previous_stage', 'previous')} to {enriched_context.get('current_stage', 'new')}.
            Previous stage focus: {enriched_context.get('previous_stage_description', 'rounding basics')}
            New stage focus: {enriched_context.get('current_stage_description', 'advanced rounding')}
            Congratulate them on their progress and briefly explain what they'll learn next.
            """
        elif message_type == "encouragement":
            user_prompt = f"""
            The student has answered {enriched_context.get('consecutive_correct', 'several')} questions correctly in a row.
            They've attempted {enriched_context.get('questions_attempted', 'multiple')} questions total in this stage.
            Give them specific encouragement about their consistency or improvement.
            """
        elif message_type == "struggle_support":
            user_prompt = f"""
            The student has made {enriched_context.get('wrong_answers', 'some')} incorrect attempts recently.
            The concept they're working on is {enriched_context.get('current_concept', 'rounding to decimal places')}.
            Their specific error pattern might be {enriched_context.get('error_pattern', 'inconsistent application of rounding rules')}.
            Provide supportive encouragement and a gentle reminder about the concept.
            Don't directly tell them the answer or approach.
            """
        else:
            user_prompt = "Provide a helpful response about decimal rounding practice."
            
        return {
            "system": system_prompt,
            "user": user_prompt
        }