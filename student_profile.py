"""
Enhanced Student Profile for AI Personalization
File: models/student_profile.py
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class QuestionResult:
    """Individual question result for tracking"""
    question_id: str
    stage: str
    is_correct: bool
    student_answer: str
    correct_answer: str
    response_time_seconds: float
    misconception_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class StudentProfile:
    """Comprehensive student profile for AI personalization"""
    
    # Basic performance tracking
    total_questions: int = 0
    total_correct: int = 0
    consecutive_correct: int = 0
    consecutive_errors: int = 0
    current_stage: str = "1.1"
    
    # Detailed tracking
    question_history: List[QuestionResult] = field(default_factory=list)
    misconception_patterns: Dict[str, int] = field(default_factory=dict)
    stage_performance: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Session context
    session_start_time: datetime = field(default_factory=datetime.now)
    total_time_spent_minutes: float = 0
    questions_this_session: int = 0
    
    # Emotional/behavioral indicators
    average_response_time: float = 0
    response_time_trend: str = "stable"  # "improving", "declining", "stable"
    engagement_level: str = "normal"  # "high", "normal", "low"
    
    # Learning preferences (discovered over time)
    learns_from_mistakes_quickly: bool = True
    prefers_encouragement: bool = True
    responds_to_challenges: bool = False
    
    def add_question_result(self, result: QuestionResult):
        """Add a new question result and update all metrics"""
        
        # Add to history
        self.question_history.append(result)
        
        # Update basic counters
        self.total_questions += 1
        self.questions_this_session += 1
        
        if result.is_correct:
            self.total_correct += 1
            self.consecutive_correct += 1
            self.consecutive_errors = 0
        else:
            self.consecutive_correct = 0
            self.consecutive_errors += 1
            
        # Update misconception tracking
        if result.misconception_type:
            if result.misconception_type not in self.misconception_patterns:
                self.misconception_patterns[result.misconception_type] = 0
            self.misconception_patterns[result.misconception_type] += 1
            
        # Update stage performance
        if result.stage not in self.stage_performance:
            self.stage_performance[result.stage] = {"attempted": 0, "correct": 0}
        self.stage_performance[result.stage]["attempted"] += 1
        if result.is_correct:
            self.stage_performance[result.stage]["correct"] += 1
            
        # Update response time tracking
        self._update_response_time_metrics(result.response_time_seconds)
        
        # Update behavioral indicators
        self._update_behavioral_indicators()
        
    def _update_response_time_metrics(self, new_time: float):
        """Update response time trends"""
        if self.total_questions == 1:
            self.average_response_time = new_time
        else:
            # Rolling average
            self.average_response_time = (
                (self.average_response_time * (self.total_questions - 1) + new_time) / 
                self.total_questions
            )
            
        # Analyze trend (simple version)
        if len(self.question_history) >= 3:
            recent_times = [q.response_time_seconds for q in self.question_history[-3:]]
            if recent_times[-1] < recent_times[0] * 0.8:
                self.response_time_trend = "improving"
            elif recent_times[-1] > recent_times[0] * 1.2:
                self.response_time_trend = "declining"
            else:
                self.response_time_trend = "stable"
                
    def _update_behavioral_indicators(self):
        """Update learning preferences and engagement"""
        
        # Check if student learns from mistakes quickly
        if self.consecutive_errors >= 2:
            self.learns_from_mistakes_quickly = False
        elif self.consecutive_correct >= 3 and any(not q.is_correct for q in self.question_history[-5:]):
            self.learns_from_mistakes_quickly = True
            
        # Determine engagement level
        if self.questions_this_session > 10 and self.total_time_spent_minutes < 20:
            self.engagement_level = "high"
        elif self.average_response_time > 30:
            self.engagement_level = "low"
        else:
            self.engagement_level = "normal"
            
        # Check if student responds to challenges
        if self.success_rate > 0.8 and self.consecutive_correct >= 4:
            self.responds_to_challenges = True
            
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate"""
        if self.total_questions == 0:
            return 0.0
        return self.total_correct / self.total_questions
    
    @property
    def current_stage_success_rate(self) -> float:
        """Success rate for current stage"""
        if self.current_stage not in self.stage_performance:
            return 0.0
        stage_data = self.stage_performance[self.current_stage]
        if stage_data["attempted"] == 0:
            return 0.0
        return stage_data["correct"] / stage_data["attempted"]
    
    @property
    def most_common_misconception(self) -> Optional[str]:
        """Get the most frequent misconception type"""
        if not self.misconception_patterns:
            return None
        return max(self.misconception_patterns.items(), key=lambda x: x[1])[0]
    
    @property
    def is_struggling(self) -> bool:
        """Determine if student is currently struggling"""
        return (
            self.consecutive_errors >= 2 or
            self.success_rate < 0.4 or
            self.current_stage_success_rate < 0.3
        )
    
    @property
    def is_excelling(self) -> bool:
        """Determine if student is excelling"""
        return (
            self.consecutive_correct >= 4 or
            (self.success_rate > 0.8 and self.total_questions >= 5)
        )
    
    def get_recent_performance_summary(self, last_n: int = 5) -> Dict[str, Any]:
        """Get summary of recent performance"""
        if len(self.question_history) == 0:
            return {"questions": 0, "correct": 0, "success_rate": 0.0}
            
        recent_questions = self.question_history[-last_n:]
        correct_count = sum(1 for q in recent_questions if q.is_correct)
        
        return {
            "questions": len(recent_questions),
            "correct": correct_count,
            "success_rate": correct_count / len(recent_questions),
            "average_time": sum(q.response_time_seconds for q in recent_questions) / len(recent_questions),
            "misconceptions": [q.misconception_type for q in recent_questions if q.misconception_type]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for session storage"""
        return {
            "total_questions": self.total_questions,
            "total_correct": self.total_correct,
            "consecutive_correct": self.consecutive_correct,
            "consecutive_errors": self.consecutive_errors,
            "current_stage": self.current_stage,
            "misconception_patterns": self.misconception_patterns,
            "stage_performance": self.stage_performance,
            "session_start_time": self.session_start_time.isoformat(),
            "total_time_spent_minutes": self.total_time_spent_minutes,
            "questions_this_session": self.questions_this_session,
            "average_response_time": self.average_response_time,
            "response_time_trend": self.response_time_trend,
            "engagement_level": self.engagement_level,
            "learns_from_mistakes_quickly": self.learns_from_mistakes_quickly,
            "prefers_encouragement": self.prefers_encouragement,
            "responds_to_challenges": self.responds_to_challenges,
            # Note: question_history excluded for session storage size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StudentProfile':
        """Create from dictionary (session restoration)"""
        profile = cls()
        
        profile.total_questions = data.get("total_questions", 0)
        profile.total_correct = data.get("total_correct", 0)
        profile.consecutive_correct = data.get("consecutive_correct", 0)
        profile.consecutive_errors = data.get("consecutive_errors", 0)
        profile.current_stage = data.get("current_stage", "1.1")
        profile.misconception_patterns = data.get("misconception_patterns", {})
        profile.stage_performance = data.get("stage_performance", {})
        profile.total_time_spent_minutes = data.get("total_time_spent_minutes", 0)
        profile.questions_this_session = data.get("questions_this_session", 0)
        profile.average_response_time = data.get("average_response_time", 0)
        profile.response_time_trend = data.get("response_time_trend", "stable")
        profile.engagement_level = data.get("engagement_level", "normal")
        profile.learns_from_mistakes_quickly = data.get("learns_from_mistakes_quickly", True)
        profile.prefers_encouragement = data.get("prefers_encouragement", True)
        profile.responds_to_challenges = data.get("responds_to_challenges", False)
        
        # Parse session start time
        if "session_start_time" in data:
            try:
                profile.session_start_time = datetime.fromisoformat(data["session_start_time"])
            except:
                profile.session_start_time = datetime.now()
        
        return profile