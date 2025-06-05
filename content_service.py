"""Provides explanations and feedback for rounding questions."""

class ContentService:
    """Handles generation of explanations and feedback for rounding questions."""

    def get_explanation(self, question, verification_steps):
        """
        Gets a hardcoded explanation for a question.
        Used for modeling examples.
        """
        number = question['original_question']['number']
        decimal_places = question['original_question']['decimal_places']
        answer = question['original_question']['answer']
        
        # Find the target digit and the digit to its right
        target_digit = verification_steps['target_digit']
        right_digit = verification_steps['right_digit']
        should_round_up = verification_steps['round_up']
        
        # Build the explanation
        ordinal = self._get_ordinal_suffix(decimal_places)
        round_action = "round up" if should_round_up else "keep the same"
        
        change_text = f"This means we change {target_digit} to {int(target_digit) + 1}." if should_round_up else f"This means we keep {target_digit} as is."
        
        explanation = f"""
        Let's work through how to round {number} to {decimal_places} decimal place(s).

        Step 1: Identify the digit in the target decimal place.
        
        The target decimal place is the {decimal_places}{ordinal} digit after the decimal point.
        
        In {number}, this digit is {target_digit}.
        
        Step 2: Look at the digit to the right of this target digit.
        
        The digit to the right of {target_digit} is {right_digit}.
        
        Step 3: Apply the rounding rule.
        
        Since {right_digit} is {'5 or more' if should_round_up else 'less than 5'}, we {round_action} the target digit.
        
        {change_text}
        
        Step 4: Remove all digits after the target decimal place.
        
        The final answer is {answer}.
        """
        
        return explanation

    def get_feedback(self, question, verification_steps, is_correct, misconception_data=None):
        """Gets feedback for a student's answer with enhanced formatting and conciseness."""
        
        # Handle the enhanced misconception data safely
        misconception_text = None
        if misconception_data:
            if isinstance(misconception_data, dict):
                # New format: extract original text
                misconception_text = misconception_data.get('original_text', '')
            else:
                # Old format: use as is
                misconception_text = str(misconception_data)
        
        # CRITICAL FIX: Ensure feedback uses the correct question data
        expected_number = question["original_question"]["number"]
        if verification_steps["original_number"] != expected_number:
            print(f"ERROR: Feedback using wrong number - expected {expected_number}, got {verification_steps['original_number']}")
            # Fix the mismatch
            verification_steps["original_number"] = expected_number
        
        student_answer = question.get("student_answer", "")
        
        if is_correct:
            feedback = f"""
            Well done! You correctly rounded {verification_steps['original_number']} to {verification_steps['decimal_places']} decimal place{'s' if verification_steps['decimal_places'] > 1 else ''}.
            
            Your answer of {verification_steps['correct_answer']} is correct!
            """
        else:
            # Get the student's choice and the correct answer
            student_choice = question['choices'].get(student_answer, "Unknown")
            correct_choice = question['choices'][question['correct_letter']]
            
            # Build the core feedback using example-style language
            target_digit = verification_steps['target_digit']
            next_digit = verification_steps['right_digit']
            decimal_places = verification_steps['decimal_places']
            original_number = verification_steps['original_number']
            correct_answer = verification_steps['correct_answer']
            
            # Determine the ordinal (1st, 2nd, 3rd, etc.)
            ordinal = self._get_ordinal_suffix(decimal_places)
            
            # Check if rounding up was needed
            should_round_up = verification_steps['round_up']
            
            # Enhanced feedback with HTML line breaks for proper display
            feedback = f"""Not quite right.<br><br>Let's work through rounding {original_number} to {decimal_places} decimal place{'s' if decimal_places > 1 else ''}:<br>1) Identify the digit in the {decimal_places}{ordinal} decimal place. This is {target_digit}.<br>2) Look at the digit to the right. This is {next_digit}.<br>3) Since {next_digit} is {'5 or more' if should_round_up else 'less than 5'}, we {'round up' if should_round_up else 'keep the digit the same'}.<br><br>The correct answer is {correct_answer}."""

            
            # Add specific misconception guidance if available
            if misconception_data and isinstance(misconception_data, dict):
                ai_context = misconception_data.get('ai_context', {})
                what_student_did = ai_context.get('what_student_did', '')
                
                # Clean up the "Student" references and make it more concise
                if what_student_did:
                    # Replace "Student" with "You" and make it more direct
                    student_action = what_student_did.replace('Student ', 'You ').replace('student ', 'you ')
                    
                    # Add this as a brief hint at the end
                    feedback += f"<br>Hint: {student_action}."
        
        return feedback.strip()  # Remove extra whitespace

    def _get_ordinal_suffix(self, n):
        """Return the ordinal suffix for a number."""
        if n == 1:
            return "st"
        elif n == 2:
            return "nd"
        elif n == 3:
            return "rd"
        else:
            return "th"