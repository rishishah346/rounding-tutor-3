"""Helper functions for session management with enhanced student profiling."""
from flask import session
from datetime import datetime
from models.student_profile import StudentProfile

def prepare_session_data(learning_sequence, section="decimal1"):
    """Convert session data to JSON-serializable format with section prefix."""
    return {
        'section': section,
        'stage': learning_sequence.get_current_stage(),
        'correct_answers': learning_sequence.correct_answers,
        'consecutive_correct': learning_sequence.consecutive_correct,
        'questions_attempted': learning_sequence.questions_attempted,
        'showing_example': learning_sequence.showing_example,
        'current_example': learning_sequence.current_example,
        'stage_results': learning_sequence.stage_results,
        'used_questions': {k: list(v) for k, v in learning_sequence.used_questions.items()}  # Convert sets to lists
    }

def load_learning_sequence_from_session(learning_sequence, section="decimal1"):
    """Update learning sequence from session data for a specific section."""
    session_key = 'learning_state'
    
    if session_key not in session:
        return learning_sequence
        
    # Only load session data if it's for the correct section
    if session[session_key].get('section') != section:
        return learning_sequence
    
    # Update from session
    learning_sequence.current_stage = session[session_key]['stage']
    learning_sequence.correct_answers = session[session_key]['correct_answers']
    learning_sequence.consecutive_correct = session[session_key]['consecutive_correct']
    learning_sequence.questions_attempted = session[session_key]['questions_attempted']
    learning_sequence.showing_example = session[session_key].get('showing_example', True)
    learning_sequence.current_example = session[session_key].get('current_example', 1)
    
    if 'stage_results' in session[session_key]:
        learning_sequence.stage_results = session[session_key]['stage_results']
    
    if 'used_questions' in session[session_key]:
        used_questions_dict = session[session_key]['used_questions']
        learning_sequence.used_questions = {k: set(v) for k, v in used_questions_dict.items()}
    
    return learning_sequence

def save_learning_sequence_to_session(learning_sequence):
    """Save learning sequence state to session."""
    session['learning_state'] = prepare_session_data(learning_sequence)

# NEW FUNCTIONS FOR STUDENT PROFILE MANAGEMENT

def get_student_profile() -> StudentProfile:
    """Get or create student profile from session"""
    if 'student_profile' not in session:
        # Create new profile
        profile = StudentProfile()
        session['student_profile'] = profile.to_dict()
        return profile
    else:
        # Load existing profile
        return StudentProfile.from_dict(session['student_profile'])

def save_student_profile(profile: StudentProfile):
    """Save student profile to session"""
    session['student_profile'] = profile.to_dict()

def update_student_profile_with_question(question_data: dict, verification_result: dict, response_time: float = 0):
    """Update student profile with new question result"""
    from models.student_profile import QuestionResult
    
    # Get current profile
    profile = get_student_profile()
    
    # Create question result
    result = QuestionResult(
        question_id=f"{question_data.get('number', 'unknown')}_{question_data.get('decimal_places', 1)}",
        stage=session.get('learning_state', {}).get('stage', '1.1'),
        is_correct=verification_result.get('is_correct', False),
        student_answer=verification_result.get('student_answer', ''),
        correct_answer=verification_result.get('correct_answer', ''),
        response_time_seconds=response_time,
        misconception_type=extract_misconception_type(verification_result.get('misconception', ''))
    )
    
    # Update profile
    profile.add_question_result(result)
    profile.current_stage = session.get('learning_state', {}).get('stage', '1.1')
    
    # Calculate session time
    time_diff = (datetime.now() - profile.session_start_time).total_seconds() / 60
    profile.total_time_spent_minutes = time_diff
    
    # Save back to session
    save_student_profile(profile)
    
    return profile

def extract_misconception_type(misconception_data) -> str:
        """Extract misconception type from verification data (handles both old and new formats)"""

        # Handle None case
        if not misconception_data:
            return None

        # Handle new enhanced format (dictionary)
        if isinstance(misconception_data, dict):
            # First try to get the structured type
            if 'type' in misconception_data:
                return misconception_data['type']

            # Fallback to analyzing the original text
            original_text = misconception_data.get('original_text', '')
            if original_text:
                return _extract_misconception_from_text(original_text)

            # Fallback to student action
            student_action = misconception_data.get('student_action', '')
            if student_action:
                return student_action

            return "general_rounding_error"

        # Handle old format (string)
        if isinstance(misconception_data, str):
            return _extract_misconception_from_text(misconception_data)

        # Fallback
        return "unknown_error"


def _extract_misconception_from_text(misconception_text: str) -> str:
        """Extract misconception type from text (helper function)"""
        if not misconception_text:
            return None

        misconception_lower = misconception_text.lower()

        # Map common misconception phrases to types
        if "round up" in misconception_lower and "should" in misconception_lower:
            return "rounding_direction_confusion"
        elif "round down" in misconception_lower and "should" in misconception_lower:
            return "rounding_direction_confusion"
        elif "decimal place" in misconception_lower or "wrong place" in misconception_lower:
            return "decimal_place_confusion"
        elif "whole number" in misconception_lower:
            return "rounding_to_whole_number"
        elif "trailing zero" in misconception_lower:
            return "trailing_zero_error"
        elif "9" in misconception_lower:
            return "nines_difficulty"
        else:
            return "general_rounding_error"


def reset_student_profile():
    """Reset student profile (for lesson restart)"""
    if 'student_profile' in session:
        del session['student_profile']

def get_student_context_for_ai() -> dict:
    """Get student context formatted for AI consumption"""
    profile = get_student_profile()
    
    return {
        "performance_summary": {
            "total_questions": profile.total_questions,
            "success_rate": round(profile.success_rate, 2),
            "consecutive_correct": profile.consecutive_correct,
            "consecutive_errors": profile.consecutive_errors,
            "current_stage": profile.current_stage
        },
        "recent_performance": profile.get_recent_performance_summary(),
        "learning_indicators": {
            "is_struggling": profile.is_struggling,
            "is_excelling": profile.is_excelling,
            "engagement_level": profile.engagement_level,
            "response_time_trend": profile.response_time_trend
        },
        "misconception_patterns": profile.misconception_patterns,
        "learning_preferences": {
            "learns_from_mistakes_quickly": profile.learns_from_mistakes_quickly,
            "prefers_encouragement": profile.prefers_encouragement,
            "responds_to_challenges": profile.responds_to_challenges
        }
    }