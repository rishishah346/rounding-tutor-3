"""
Rounding Tutor - Main Application
A Flask application that teaches students to round decimal numbers.
"""
from flask import Flask, render_template, request, jsonify, session, url_for, redirect
import os
import json
import logging
from functools import wraps
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Local imports
from config import SESSION_KEY, STAGES
from models.learning_sequence import LearningSequence
from models.question_generator import QuestionGenerator
from models.verifier import Verifier
from models.ai_companion import AICompanion
from services.content_service import ContentService
from helpers.session_helper import prepare_session_data, load_learning_sequence_from_session
from helpers.response_helper import (
    format_example_response, 
    format_practice_response, 
    format_complete_response,
    format_error_response
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = SESSION_KEY if 'SESSION_KEY' in globals() else os.urandom(24)

# Initialize services
learning_sequence = LearningSequence()
question_generator = QuestionGenerator()
verifier = Verifier()
content_service = ContentService()

# Error handler decorator
def handle_errors(f):
    """Decorator to handle errors in route handlers."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {e}", exc_info=True)
            return format_error_response(e)
    return decorated_function

# Session setup - MUST be before any routes
@app.before_request
def before_request():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    if 'ai_conversation' not in session:
        session['ai_conversation'] = []

# AI Companion Route - Place early in the file
@app.route('/api/ai/message', methods=['POST'])
@handle_errors
def get_ai_message():
    """API endpoint to get AI companion messages."""
    logger.info("=== AI MESSAGE ENDPOINT CALLED ===")
    
    try:
        data = request.json
        if not data:
            logger.error("No JSON data provided")
            return jsonify({'error': 'No JSON data provided'}), 400
            
        message_type = data.get('message_type', 'general')
        context = data.get('context', {})
        
        logger.info(f"Message type: {message_type}")
        logger.info(f"Context: {context}")
        
        # Get current learning state
        current_sequence = load_learning_sequence_from_session(learning_sequence)
        
        # Set up AI companion with current state
        ai_companion = AICompanion()
        ai_companion.current_stage = current_sequence.get_current_stage()
        ai_companion.student_profile = {
            'correct_answers': current_sequence.correct_answers,
            'questions_attempted': current_sequence.questions_attempted,
            'consecutive_correct': current_sequence.consecutive_correct
        }
        
        # Load conversation history from session
        ai_companion.conversation_history = session.get('ai_conversation', [])
        
        # Generate message
        logger.info("Generating AI message...")
        message = ai_companion.generate_message(message_type, context)
        logger.info(f"Generated message: {message}")
        
        # Save updated conversation history to session
        session['ai_conversation'] = ai_companion.conversation_history
        
        return jsonify({'message': message})
        
    except Exception as e:
        logger.error(f"Error in AI message endpoint: {e}", exc_info=True)
        # Return a fallback message instead of an error
        fallback_messages = {
            'welcome': "Hi there! I'm Math Helper, ready to support your decimal rounding practice.",
            'encouragement': "Great job! You're doing really well with your rounding practice.",
            'stage_transition': "Excellent progress! You're ready to move on to the next level.",
            'struggle_support': "Don't worry, everyone makes mistakes while learning. Keep practicing!",
            'completion': "Congratulations! You've done an amazing job completing this lesson."
        }
        
        message_type = data.get('message_type', 'welcome') if data else 'welcome'
        fallback_message = fallback_messages.get(message_type, "I'm here to help with your math practice!")
        
        return jsonify({'message': fallback_message})

# Routes
@app.route('/')
def index():
    """Home page route."""
    # Reset the learning sequence when starting
    session.clear()
    learning_sequence.reset()
    return render_template('pages/index.html')

@app.route('/lesson')
def lesson():
    """Main lesson page route."""
    return render_template('lesson.html')

@app.route('/api/next-step', methods=['GET'])
@handle_errors
def next_step():
    """API endpoint to get the next learning step."""
    logger.info("--- NEXT STEP REQUEST ---")
    
    # Load or create learning sequence from session
    current_sequence = load_learning_sequence_from_session(learning_sequence)
    logger.debug(f"Current stage: {current_sequence.get_current_stage()}")
    
    # Get current stage details
    current_stage = current_sequence.get_current_stage()
    
    # Check if we've reached the end of the lesson
    if current_stage == STAGES["COMPLETE"]:
        logger.info("Lesson complete, returning completion message")
        return format_complete_response()
    
    stage_rules = current_sequence.get_stage_rules()
    
    # Check if we should model an example
    should_model = current_sequence.should_model_example()
    logger.debug(f"Current stage: {current_stage}")
    logger.debug(f"Questions attempted: {current_sequence.questions_attempted}")
    logger.debug(f"Showing example: {current_sequence.showing_example}")
    logger.debug(f"Current example: {current_sequence.current_example}")
    logger.debug(f"Should model: {should_model}")
    
    if should_model:
        return serve_example(current_sequence, stage_rules)
    else:
        return serve_practice_question(current_sequence, stage_rules)

def serve_example(current_sequence, stage_rules):
    """Redirect to appropriate examples page instead of generating examples."""
    logger.info(f"Redirecting for example #{current_sequence.current_example}")
    
    # Update session state
    session['learning_state'] = prepare_session_data(current_sequence)
    
    # Redirect to the appropriate examples page based on stage
    if current_sequence.current_stage == STAGES["ROUNDING_1DP_NO_UP"]:
        logger.info("Stage 1.1 detected - redirecting to examples page")
        return jsonify({'redirect': url_for('examples')})
    elif current_sequence.current_stage == STAGES["ROUNDING_2DP"]:
        if session['learning_state']['showing_example']:
            logger.info("Redirecting to decimal2_examples from current_stage check")
            return jsonify({'redirect': url_for('decimal2_examples')})
        else:
            logger.info("Redirecting to decimal23_practice from current_stage check")
            return jsonify({'redirect': url_for('decimal23_practice')})
    elif current_sequence.current_stage == STAGES["ROUNDING_2DP_STAGE_2"]:
        logger.info("Redirecting to decimal23_practice from current_stage check for stage 2.2")
        return jsonify({'redirect': url_for('decimal23_practice')})
    elif current_sequence.current_stage == STAGES["STRETCH"]:
            logger.info("Stretch stage detected - redirecting to stretch_examples page")
            return jsonify({'redirect': url_for('stretch_examples')})
    else:
        # For other stages, redirect to practice
        logger.info(f"Stage {current_sequence.current_stage} - redirecting to practice")
        return jsonify({'redirect': url_for('practice')})

def serve_practice_question(current_sequence, stage_rules):
    """Generate and serve a practice question."""
    logger.info("Returning practice question")
    
    question = question_generator.generate_question(stage_rules, current_sequence)
    formatted_question = question_generator.format_multiple_choice(question)
    
    # Store the question in session for verification later
    session['current_question'] = json.dumps(formatted_question)
    
    # Update session
    session['learning_state'] = prepare_session_data(current_sequence)
    
    return format_practice_response(current_sequence, formatted_question)

@app.route('/api/verify-answer', methods=['POST'])
@handle_errors
def verify_answer():
    """API endpoint to verify a student's answer."""
    # Get the student's answer
    data = request.json
    student_answer = data.get('answer')
    logger.info(f"Received answer: {student_answer}")
    
    # Store the current stage before any updates
    old_stage = learning_sequence.current_stage
    old_consecutive = learning_sequence.consecutive_correct
    
    # Debug info
    logger.info(f"BEFORE - Stage: {old_stage}, Consecutive correct: {old_consecutive}")
    
    # Retrieve the current question from session
    if 'current_question' not in session:
        return jsonify({'error': 'No active question found'}), 400
        
    current_question = json.loads(session['current_question'])
    
    # Log the question being verified
    logger.info(f"Verifying answer for question: {current_question['question_text']}")
    logger.info(f"Student selected: {student_answer} - {current_question['choices'].get(student_answer, 'Unknown')}")
    logger.info(f"Correct answer is: {current_question['correct_letter']} - {current_question['choices'][current_question['correct_letter']]}")
    
    # Add the student's answer to the question dict
    current_question["student_answer"] = student_answer
    
    # Verify the answer
    is_correct, verification_steps, misconception = verifier.verify_answer(
        current_question,
        student_answer
    )
    
    # CRITICAL FIX: Ensure verification steps use the correct question data
    if verification_steps["original_number"] != current_question["original_question"]["number"]:
        logger.error(f"MISMATCH: Verification steps use {verification_steps['original_number']} but question is {current_question['original_question']['number']}")
        # Fix the mismatch
        verification_steps["original_number"] = current_question["original_question"]["number"]
    
    # Update learning sequence based on the answer
    learning_sequence.update_progress(is_correct)

    # NEW: Track student profile data
    from helpers.session_helper import update_student_profile_with_question
    student_profile = update_student_profile_with_question(
        current_question,
        {
            'is_correct': is_correct,
            'student_answer': student_answer,
            'correct_answer': current_question['choices'][current_question['correct_letter']],
            'misconception': misconception
        },
        response_time=0  # We'll add response time tracking later
    )

    
    # After state
    new_stage = learning_sequence.current_stage
    new_consecutive = learning_sequence.consecutive_correct
    
    # Debug info
    logger.info(f"AFTER - Stage: {new_stage}, Consecutive correct: {new_consecutive}")
    logger.info(f"Showing example: {learning_sequence.showing_example}")
    logger.info(f"Stage changed: {old_stage != new_stage}")
    
    # Special handling for transition to stage 2.1
    if old_stage == STAGES["ROUNDING_1DP_BOTH"] and new_stage == STAGES["ROUNDING_2DP"]:
        logger.info("Detected transition from 1.3 to 2.1 - setting up to show examples")
        learning_sequence.showing_example = True
        learning_sequence.current_example = 1
    
    # Check if stage has changed (which means criteria were met)
    stage_completed = old_stage != new_stage
    
    # Check if showing examples for the new stage
    showing_new_examples = stage_completed and learning_sequence.showing_example
    
    # Update session with new state
    session['learning_state'] = prepare_session_data(learning_sequence)
    
    # Get feedback (enhanced with misconception data)
    logger.info("Generating feedback...")
    feedback = content_service.get_feedback(
        current_question,
        verification_steps,
        is_correct,
        misconception  # This is now the enhanced misconception data from verifier.py
    )
    logger.info("Feedback generated")
    
    # Instead of immediately redirecting, set a flag to redirect after the next question button
    if old_stage == STAGES["ROUNDING_1DP_BOTH"] and new_stage == STAGES["ROUNDING_2DP"]:
        logger.info("Setting next_stage_redirect flag for transition to decimal2_examples")
        return jsonify({
            'is_correct': is_correct,
            'feedback': feedback,
            'verification_steps': verification_steps,
            'next_stage': new_stage,
            'stage_completed': stage_completed,
            'showing_new_examples': True,
            'lesson_complete': False,
            'next_stage_redirect': url_for('decimal2_examples') # Flag for next button to handle
        })
    
    # Normal response
    return jsonify({
        'is_correct': is_correct,
        'feedback': feedback,
        'verification_steps': verification_steps,
        'next_stage': new_stage,
        'stage_completed': stage_completed,
        'showing_new_examples': showing_new_examples,
        'lesson_complete': new_stage == STAGES["COMPLETE"]
    })

@app.route('/api/next-example', methods=['POST'])
@handle_errors
def next_example():
    """API endpoint to advance to the next example or to practice."""
    logger.info("--- /api/next-example CALLED ---")
    logger.debug(f"Before update: stage={learning_sequence.current_stage}, "
                f"example={learning_sequence.current_example}, "
                f"showing={learning_sequence.showing_example}")
    
    # Check specific progression conditions
    if ('learning_state' in session and
        session['learning_state']['stage'] == STAGES["ROUNDING_1DP_NO_UP"] and
        session['learning_state']['current_example'] == 1 and
        session['learning_state']['showing_example'] == True):
        # Force set to example 2 instead of incrementing
        learning_sequence.current_example = 2
        learning_sequence.showing_example = True
        logger.debug("Fixed progression: Setting directly to example 2")
    elif ('learning_state' in session and
          session['learning_state']['stage'] == STAGES["ROUNDING_1DP_NO_UP"] and
          session['learning_state']['current_example'] == 2 and
          session['learning_state']['showing_example'] == True):
        # Force transition to practice after second example
        learning_sequence.current_example = 3  # This should trigger practice mode
        learning_sequence.showing_example = False
        logger.debug("Fixed progression: Setting to practice mode after example 2")
    # Add similar logic for 2 decimal place examples
    elif ('learning_state' in session and
          session['learning_state']['stage'] == STAGES["ROUNDING_2DP"] and
          session['learning_state']['current_example'] == 1 and
          session['learning_state']['showing_example'] == True):
        # Force set to example 2
        learning_sequence.current_example = 2
        learning_sequence.showing_example = True
        logger.debug("Fixed progression: Setting directly to 2DP example 2")
    elif ('learning_state' in session and
          session['learning_state']['stage'] == STAGES["ROUNDING_2DP"] and
          session['learning_state']['current_example'] == 2 and
          session['learning_state']['showing_example'] == True):
        # Force transition to practice after second example
        learning_sequence.current_example = 3  # This should trigger practice mode
        learning_sequence.showing_example = False
        logger.debug("Fixed progression: Setting to practice mode after 2DP example 2")
    else:
        # Normal progression
        learning_sequence.next_example()
    
    logger.debug(f"After update: stage={learning_sequence.current_stage}, "
                f"example={learning_sequence.current_example}, "
                f"showing={learning_sequence.showing_example}")
    
    # Update session
    session['learning_state'] = prepare_session_data(learning_sequence)
    logger.debug(f"Session updated: {session['learning_state']}")
    
    return jsonify({'status': 'success'})

@app.route('/api/reset', methods=['POST'])
@handle_errors
def reset_lesson():
    """API endpoint to reset the lesson."""
    logger.info("Reset endpoint called")
    
    # Clear session including student profile
    from helpers.session_helper import reset_student_profile
    session.clear()
    reset_student_profile()
    
    # Reset learning sequence
    learning_sequence.reset()
    logger.info("Session cleared and learning sequence reset")
    
    # Return a redirect instruction
    return jsonify({'status': 'reset', 'redirect': '/'})

@app.route('/lesson-intro')
def lesson_intro():
    """Lesson introduction page route."""
    # Reset the learning sequence when starting the intro
    learning_sequence.reset()
    session.clear()
    return render_template('pages/lesson_intro.html')

@app.route('/api/current-stage')
@handle_errors
def current_stage():
    """API endpoint to get the current stage and determine where the user should be."""
    if 'learning_state' not in session:
        # New user, should stay on intro page
        return jsonify({})

    # Check current stage and redirect if needed
    current_stage = session['learning_state']['stage']
    logger.info(f"Current stage check: {current_stage}")
    logger.info(f"Should show examples? {session['learning_state']['showing_example']}")
    
    if current_stage == STAGES["ROUNDING_1DP_NO_UP"]:
        # Show examples for stage 1.1
        if session['learning_state']['showing_example']:
            return jsonify({'redirect': url_for('examples')})
        else:
            return jsonify({'redirect': url_for('practice')})
    elif current_stage == STAGES["ROUNDING_1DP_WITH_UP"]:
        return jsonify({'redirect': url_for('practice')})
    elif current_stage == STAGES["ROUNDING_1DP_BOTH"]:
        return jsonify({'redirect': url_for('practice')})
    elif current_stage == STAGES["ROUNDING_2DP"]:
        if session['learning_state']['showing_example']:
            logger.info("Redirecting to decimal2_examples from current_stage check")
            return jsonify({'redirect': url_for('decimal2_examples')})
        else:
            logger.info("Redirecting to decimal23_practice from current_stage check")
            return jsonify({'redirect': url_for('decimal23_practice')})
    elif current_stage == STAGES["STRETCH"]:
        if session['learning_state']['showing_example']:
            return jsonify({'redirect': url_for('stretch_examples')})
        else:
            return jsonify({'redirect': url_for('stretch_practice')})
    elif current_stage == STAGES["COMPLETE"]:
        return jsonify({'redirect': url_for('complete')})
    
    # Default: stay on current page
    return jsonify({})

@app.route('/examples')
def examples():
    """Examples page route."""
    # Check if user is in the correct stage
    if 'learning_state' not in session:
        # New user, initialize the learning sequence
        learning_sequence.reset()
        learning_sequence.current_stage = STAGES["ROUNDING_1DP_NO_UP"]
        learning_sequence.showing_example = True
        learning_sequence.current_example = 1
        session['learning_state'] = prepare_session_data(learning_sequence)
    elif session['learning_state']['stage'] != STAGES["ROUNDING_1DP_NO_UP"] or not session['learning_state']['showing_example']:
        # User is in the wrong stage, redirect to appropriate page
        return redirect(url_for('current_stage'))
    
    # Use the correct template name
    return render_template('pages/decimal1_examples.html')

@app.route('/api/decimal1/examples/first')
@handle_errors
def decimal1_examples_first():
    """API endpoint to get the first example data."""
    # Update session state
    learning_sequence.current_example = 1
    learning_sequence.showing_example = True
    session['learning_state'] = prepare_session_data(learning_sequence)

    # Hardcoded example data - no dependency on question_generator
    example_data = {
        "question_text": "Round 12.632 to 1 decimal place",
        "steps": [
            {
                "image": "/static/images/stage1_1_step1.jpg",
                "explanation": "Identify the digit in the 1st decimal place. This is the first digit after the decimal point. We will call it the \"rounding digit\". Draw a \"cut off\" line after the rounding digit."
            },
            {
                "image": "/static/images/stage1_1_step2.jpg",
                "explanation": "Check the digit to the right of the \"cut off\" line. If this digit is less than 5 we keep our rounding digit the same."
            },
            {
                "image": "/static/images/stage1_1_step3.jpg",
                "explanation": "Remove all digits after the \"cut off\" line. We have now rounded the number to 1 decimal place."
            }
        ],
        "answer": "12.6"
    }
    
    return jsonify(example_data)

@app.route('/api/decimal1/examples/second')
@handle_errors
def decimal1_examples_second():
    """API endpoint to get the second example data."""
    # Update learning sequence to show second example
    learning_sequence.current_example = 2
    session['learning_state'] = prepare_session_data(learning_sequence)
    
    # Hardcoded example data - no dependency on question_generator
    example_data = {
        "question_text": "Round 12.682 to 1 decimal place",
        "steps": [
            {
                "image": "/static/images/stage1_2_step1.jpg",
                "explanation": "Identify the digit in the 1st decimal place. This is the first digit after the decimal point. We will call it the \"rounding digit\". Draw a \"cut off\" line after the rounding digit."
            },
            {
                "image": "/static/images/stage1_2_step2.jpg",
                "explanation": "Check the digit to the right of the \"cut off\" line. If this digit is 5 or bigger we need to round up. We do this by adding 1 to the rounding digit."
            },
            {
                "image": "/static/images/stage1_2_step3.jpg",
                "explanation": "Remove all digits after the \"cut off\" line. We have now rounded the number to 1 decimal place. Notice that the 6 has changed to a 7 as we rounded up."
            }
        ],
        "answer": "12.7"
    }
    
    return jsonify(example_data)

@app.route('/api/decimal1/examples/complete', methods=['POST'])
@handle_errors
def decimal1_examples_complete():
    """API endpoint to mark examples as complete and move to practice."""
    # Update learning sequence to show practice
    learning_sequence.showing_example = False
    learning_sequence.current_example = 3  # This should trigger practice mode based on your code
    session['learning_state'] = prepare_session_data(learning_sequence)
    
    return jsonify({"status": "success"})

@app.route('/practice')
def practice():
    """Practice page route."""
    # Check if user is in the correct stage
    if 'learning_state' not in session:
        # New user, should start from intro
        return redirect(url_for('lesson_intro'))
    
    # Check the current stage and whether we're done with examples
    if session['learning_state']['showing_example']:
        # Still in example mode, redirect to examples page
        return redirect(url_for('examples'))
    
    # User is ready for practice
    return render_template('pages/decimal1_practice.html')

@app.route('/api/decimal1/practice/question')
@handle_errors
def decimal1_practice_question():
    """API endpoint to get a practice question."""
    # Load current sequence from session
    current_sequence = load_learning_sequence_from_session(learning_sequence)
    
    # Check if we've reached the end of the lesson
    if current_sequence.get_current_stage() == STAGES["COMPLETE"]:
        return jsonify({
            'lesson_complete': True,
            'message': "Congratulations! You've completed all the stages in this lesson."
        })
    
    # Get current stage rules
    stage_rules = current_sequence.get_stage_rules()
    
    # Generate a question
    question = question_generator.generate_question(stage_rules, current_sequence)
    formatted_question = question_generator.format_multiple_choice(question)
    
    # Store the question in session for verification later
    session['current_question'] = json.dumps(formatted_question)
    
    # Update session
    session['learning_state'] = prepare_session_data(current_sequence)
    
    return jsonify({
        'lesson_complete': False,
        'stage': current_sequence.get_current_stage(),
        'question': formatted_question
    })

@app.route('/decimal1/practice')
def decimal1_practice():
    """Decimal 1 Practice page route."""
    # Check if user is in the correct stage
    if 'learning_state' not in session:
        # New user, should start from intro
        return redirect(url_for('lesson_intro'))
    
    # Check the current stage and whether we're done with examples
    if session['learning_state']['showing_example']:
        # Still in example mode, redirect to examples page
        return redirect(url_for('examples'))
    
    # User is ready for practice
    return render_template('pages/decimal1_practice.html')

@app.route('/decimal2/examples')
def decimal2_examples():
    """Decimal 2 Examples page route."""
    logger.info("Decimal2 examples page requested")
    
    # Check if user is in the correct stage
    if 'learning_state' not in session:
        logger.info("No learning state found, redirecting to intro")
        # New user, should start from intro
        return redirect(url_for('lesson_intro'))
    
    # If we're in stage 2.1 but not showing examples, redirect to practice
    if session['learning_state']['stage'] == STAGES["ROUNDING_2DP"] and not session['learning_state']['showing_example']:
        logger.info("Stage 2.1 but showing_example is False, redirecting to practice")
        return redirect(url_for('decimal2_practice'))
    
    # Set up for examples if needed - force example mode
    if session['learning_state']['stage'] == STAGES["ROUNDING_2DP"]:
        logger.info("Setting up session for stage 2.1 examples")
        learning_sequence.current_stage = STAGES["ROUNDING_2DP"]  # Ensure correct stage
        learning_sequence.showing_example = True
        learning_sequence.current_example = 1
        session['learning_state'] = prepare_session_data(learning_sequence)
    else:
        # If not in the right stage, update to proper stage
        logger.info(f"Not in stage 2.1, currently in {session['learning_state']['stage']}")
        # Force set to stage 2.1 for testing purposes
        learning_sequence.current_stage = STAGES["ROUNDING_2DP"]
        learning_sequence.showing_example = True
        learning_sequence.current_example = 1
        session['learning_state'] = prepare_session_data(learning_sequence)
    
    # Log current state for debugging
    logger.info(f"Rendering decimal23_examples.html with session state: {session['learning_state']}")
    
    # Use the correct template
    return render_template('pages/decimal23_examples.html')

@app.route('/decimal2/practice')
def decimal2_practice():
    """Decimal 2 Practice page route."""
    # Check if user is in the correct stage
    if 'learning_state' not in session:
        # New user, should start from intro
        return redirect(url_for('lesson_intro'))
    
    # Check if we should be showing examples
    if session['learning_state']['stage'] == STAGES["ROUNDING_2DP"] and session['learning_state']['showing_example']:
        logger.info("Should be showing examples, redirecting to decimal2_examples")
        return redirect(url_for('decimal2_examples'))
    
    # Set up practice mode
    learning_sequence.showing_example = False
    session['learning_state'] = prepare_session_data(learning_sequence)
    
    # Use a practice template
    return render_template('pages/decimal23_practice.html')

@app.route('/api/decimal2/examples/first')
@handle_errors
def decimal2_examples_first():
    """API endpoint to get the first example data for decimal2."""
    # Update session state
    learning_sequence.current_example = 1
    learning_sequence.showing_example = True
    session['learning_state'] = prepare_session_data(learning_sequence)
    
    # Hardcoded example data - no dependency on question_generator
    example_data = {
        'question_text': 'Round 12.632 to 2 decimal places',
        'steps': [
            {
                'explanation': 'Identify the digit in the 2nd decimal place. This is the second digit after the decimal point. We will call it the "rounding digit". Draw a "cut off" line after the rounding digit.',
                'image': '/static/images/stage2_1_step1.jpg'
            },
            {
                'explanation': 'Check the digit to the right of the "cut off" line. If this digit is less than 5 we keep our rounding digit the same.',
                'image': '/static/images/stage2_1_step2.jpg'
            },
            {
                'explanation': 'Remove all digits after the "cut off" line. We have now rounded the number to 2 decimal places.',
                'image': '/static/images/stage2_1_step3.jpg'
            }
        ],
        'answer': '12.63'
    }
    
    return jsonify(example_data)

@app.route('/api/decimal2/examples/second')
@handle_errors
def decimal2_examples_second():
    """API endpoint to get the second example data for decimal2."""
    # Update learning sequence to show second example
    learning_sequence.current_example = 2
    session['learning_state'] = prepare_session_data(learning_sequence)
    
    # Hardcoded example data - no dependency on question_generator
    example_data = {
        'question_text': 'Round 12.678 to 3 decimal places',
        'steps': [
            {
                'explanation': 'Identify the digit in the 3rd decimal place. This is the third digit after the decimal point. We will call it the "rounding digit". Draw a "cut off" line after the rounding digit.',
                'image': '/static/images/stage2_2_step1.jpg'
            },
            {
                'explanation': 'Check the digit to the right of the "cut off" line. If this digit is 5 or bigger we need to round up. We do this by adding 1 to the rounding digit.',
                'image': '/static/images/stage2_2_step2.jpg'
            },
            {
                'explanation': 'Remove all digits after the "cut off" line. We have now rounded the number to 3 decimal places. Notice that the 7 has changed to an 8 as we rounded up.',
                'image': '/static/images/stage2_2_step3.jpg'
            }
        ],
        'answer': '12.68'
    }
    
    return jsonify(example_data)

@app.route('/api/decimal2/examples/complete', methods=['POST'])
@handle_errors
def decimal2_examples_complete():
   """API endpoint to mark decimal2 examples as complete and move to practice."""
   # Update learning sequence to show practice
   learning_sequence.showing_example = False
   learning_sequence.current_example = 3  # This should trigger practice mode
   session['learning_state'] = prepare_session_data(learning_sequence)
   
   return jsonify({"status": "success"})

@app.route('/api/decimal2/practice/question')
@handle_errors
def decimal2_practice_question():
   """API endpoint to get a practice question for decimal2 stage."""
   # Load current sequence from session
   current_sequence = load_learning_sequence_from_session(learning_sequence)
   
   # Check if we've reached the end of the lesson
   if current_sequence.get_current_stage() == STAGES["COMPLETE"]:
       return jsonify({
           'lesson_complete': True,
           'message': "Congratulations! You've completed all the stages in this lesson."
       })
   
   # Get current stage rules
   stage_rules = current_sequence.get_stage_rules()
   
   # Generate a question
   question = question_generator.generate_question(stage_rules, current_sequence)
   formatted_question = question_generator.format_multiple_choice(question)
   
   # Store the question in session for verification later
   session['current_question'] = json.dumps(formatted_question)
   
   # Update session
   session['learning_state'] = prepare_session_data(current_sequence)
   
   return jsonify({
       'lesson_complete': False,
       'stage': current_sequence.get_current_stage(),
       'question': formatted_question
   })

@app.route('/decimal23/practice')
def decimal23_practice():
   """Decimal 2 and 3 Practice page route."""
   # Check if user is in the correct stage
   if 'learning_state' not in session:
       # New user, should start from intro
       return redirect(url_for('lesson_intro'))
   
   # Check if we should be showing examples
   if session['learning_state']['stage'] == STAGES["ROUNDING_2DP"] and session['learning_state']['showing_example']:
       logger.info("Should be showing examples, redirecting to decimal23_examples")
       return redirect(url_for('decimal2_examples'))
   
   # Set up practice mode
   learning_sequence.showing_example = False
   session['learning_state'] = prepare_session_data(learning_sequence)
   
   # Use a practice template
   return render_template('pages/decimal23_practice.html')

@app.route('/api/decimal23/practice/question')
@handle_errors
def decimal23_practice_question():
   """API endpoint to get a practice question for decimal 2 and 3 stage."""
   # Load current sequence from session
   current_sequence = load_learning_sequence_from_session(learning_sequence)
   
   # Check if we've reached the end of the lesson
   if current_sequence.get_current_stage() == STAGES["COMPLETE"]:
       return jsonify({
           'lesson_complete': True,
           'message': "Congratulations! You've completed all the stages in this lesson."
       })
   
   # Get current stage rules
   stage_rules = current_sequence.get_stage_rules()
   
   # Generate a question
   question = question_generator.generate_question(stage_rules, current_sequence)
   formatted_question = question_generator.format_multiple_choice(question)
   
   # Store the question in session for verification later
   session['current_question'] = json.dumps(formatted_question)
   
   # Update session
   session['learning_state'] = prepare_session_data(current_sequence)
   
   return jsonify({
       'lesson_complete': False,
       'stage': current_sequence.get_current_stage(),
       'question': formatted_question
   })

# Routes for stretch content
@app.route('/stretch/examples')
def stretch_examples():
   """Stretch Examples page route."""
   # Check if user is in the correct stage
   if 'learning_state' not in session:
       # New user, should start from intro
       return redirect(url_for('lesson_intro'))
   
   # If we're in stretch stage but not showing examples, redirect to practice
   if session['learning_state']['stage'] == STAGES["STRETCH"] and not session['learning_state']['showing_example']:
       return redirect(url_for('stretch_practice'))
   
   # Set up for examples if needed
   if session['learning_state']['stage'] == STAGES["STRETCH"]:
       learning_sequence.showing_example = True
       learning_sequence.current_example = 1
       session['learning_state'] = prepare_session_data(learning_sequence)
   
   # Use the correct template
   return render_template('pages/stretch_examples.html')

@app.route('/stretch/practice')
def stretch_practice():
   """Stretch Practice page route."""
   # Check if user is in the correct stage
   if 'learning_state' not in session:
       # New user, should start from intro
       return redirect(url_for('lesson_intro'))
   
   # Check if we should be showing examples
   if session['learning_state']['stage'] == STAGES["STRETCH"] and session['learning_state']['showing_example']:
       return redirect(url_for('stretch_examples'))
   
   # Use a practice template
   return render_template('pages/stretch_practice.html')

@app.route('/complete')
def complete():
   """Lesson completion page route."""
   # Check if user has actually completed the lesson
   if 'learning_state' not in session or session['learning_state']['stage'] != STAGES["COMPLETE"]:
       return redirect(url_for('lesson_intro'))
   
   return render_template('pages/complete.html')

# Debug endpoint to view session data
@app.route('/debug-session')
def debug_session():
   """Debug endpoint to view current session data."""
   return jsonify({
       'learning_state': session.get('learning_state', {}),
       'current_question': session.get('current_question', {}),
       'ai_conversation': session.get('ai_conversation', [])
   })

# Test endpoint for debugging
@app.route('/api/test', methods=['GET', 'POST'])
def test_endpoint():
   """Simple test endpoint to verify Flask is working."""
   return jsonify({
       'status': 'working', 
       'method': request.method,
       'session_id': session.get('user_id', 'no session')
   })

if __name__ == '__main__':
   print("Starting Rounding Tutor Flask app...")
   print(f"Debug mode: {app.debug}")
   app.run(debug=True, host='127.0.0.1', port=5000)