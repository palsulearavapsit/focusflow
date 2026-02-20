"""
Cognitive Performance Engine
Analyzes user performance in break activities to determine cognitive state.
"""

from schemas import GameType, CognitiveState, RecommendedAction

def analyze_cognitive_performance(
    game_type: GameType,
    current_metrics: dict,
    previous_metrics: dict = None,
    focus_score: float = 0
):
    """
    Core logic for evaluating cognitive refresh status.
    """
    refresh_score = 0.0
    state = CognitiveState.STABLE
    action = RecommendedAction.RETURN
    
    # --- 1. GAME-SPECIFIC LOGIC ---
    
    if game_type == GameType.STROOP:
        # Metrics: accuracy (0-1), avg_response_time (ms), error_count
        acc = current_metrics.get("accuracy", 0.0)
        rt = current_metrics.get("avg_response_time", 1000)
        errors = current_metrics.get("error_count", 0)
        
        # Base score from accuracy (60%) and RT (40%)
        # RT normalization: Assume 500ms is great (1.0), 1500ms is poor (0.0)
        rt_score = max(0, min(1, (1500 - rt) / 1000))
        refresh_score = (acc * 60) + (rt_score * 40)
        
        # Adjust for errors
        if errors > 5:
            refresh_score -= 10
            
        # Comparison logic
        if previous_metrics:
            prev_acc = previous_metrics.get("accuracy", 0)
            if acc < prev_acc * 0.8:
                state = CognitiveState.FATIGUED
            elif acc > prev_acc * 1.05:
                state = CognitiveState.REFRESHED
                refresh_score += 10 # Bonus for improvement

    elif game_type == GameType.REACTION:
        # Metrics: avg_reaction_time (ms), best_reaction_time
        avg_rt = current_metrics.get("avg_reaction_time", 400)
        
        # Normalization: <200ms = 100, >500ms = 0
        refresh_score = max(0, min(100, (500 - avg_rt) / 3))
        
        if previous_metrics:
            prev_avg = previous_metrics.get("avg_reaction_time", 400)
            if avg_rt > prev_avg * 1.2: # 20% slower
                state = CognitiveState.FATIGUED
            elif avg_rt < prev_avg * 0.9: # 10% faster
                state = CognitiveState.REFRESHED
                refresh_score += 10

    elif game_type == GameType.RECALL:
        # Metrics: max_digit_length, accuracy
        length = current_metrics.get("max_digit_length", 4)
        acc = current_metrics.get("accuracy", 0.0)
        
        # Score: Length * 10 + Accuracy * 20
        # E.g. 7 digits -> 70 + 20 = 90
        refresh_score = min(100, (length * 10) + (acc * 20))
        
        if previous_metrics:
            prev_len = previous_metrics.get("max_digit_length", 0)
            if length < prev_len - 1:
                state = CognitiveState.FATIGUED
            elif length > prev_len:
                state = CognitiveState.REFRESHED

    elif game_type == GameType.BREATHING:
        # Metrics: stability_score (0-1), pre_focus, post_focus
        stability = current_metrics.get("stability_score", 0.5)
        pre = current_metrics.get("pre_exercise_focus_score", 50)
        post = current_metrics.get("post_exercise_focus_score", 50)
        
        # Score heavily heavily on stability and improvement
        improvement = max(0, post - pre)
        refresh_score = (stability * 70) + (improvement * 10) # simplified
        if refresh_score > 100: refresh_score = 100
        
        if stability > 0.8 or improvement > 10:
             state = CognitiveState.REFRESHED
        elif stability < 0.4:
             state = CognitiveState.FATIGUED # Actually means "did not regulate well"

    # --- 2. GLOBAL OVERRIDES ---
    refresh_score = max(0, min(100, refresh_score))
    
    # State determination based on absolute score if not already set by comparison
    if state == CognitiveState.STABLE:
        if refresh_score > 75:
            state = CognitiveState.REFRESHED
        elif refresh_score < 40:
            state = CognitiveState.FATIGUED

    # --- 3. RECOMMENDATION ENGINE ---
    analysis_text = ""
    motivation_text = ""

    if state == CognitiveState.REFRESHED:
        action = RecommendedAction.RETURN
        analysis_text = f"Your performance in {game_type.value} was excellent (Score: {int(refresh_score)}). This indicates your cognitive control and alertness are fully restored."
        motivation_text = "You are sharp and ready! This is the perfect time to tackle your most difficult verification tasks."
    
    elif state == CognitiveState.STABLE:
        if focus_score < 50:
            # Low focus previously, but stable game -> Extend
            action = RecommendedAction.EXTEND
            analysis_text = f"While your game performance was stable (Score: {int(refresh_score)}), your previous focus was low. A few more minutes of break might help secure a reset."
            motivation_text = "You're doing okay, but let's take 2 more minutes to ensure you're fully recharged before jumping back in."
        else:
            action = RecommendedAction.RETURN
            analysis_text = f"Your cognitive metrics are within normal ranges (Score: {int(refresh_score)}). You have maintained your mental baseline."
            motivation_text = "Good job maintaining stability. You are ready to continue your session."
            
    elif state == CognitiveState.FATIGUED:
        if game_type == GameType.BREATHING:
             # Already did breathing, still low -> Extend
             action = RecommendedAction.EXTEND
             analysis_text = "Your physiological stability remains lower than optimal. Rushing back now might lead to quick burnout."
             motivation_text = "Take a moment. There is no rush. Let's try to relax for 2 more minutes."
        else:
             # Failed a game -> Breathing
             action = RecommendedAction.BREATHE
             analysis_text = f"Your reaction times and accuracy (Score: {int(refresh_score)}) show signs of cognitive fatigue compared to your baseline."
             motivation_text = "Your brain is tired, and that's okay. Instead of forcing it, let's try a breathing exercise to reset your nervous system."

    return {
        "cognitive_refresh_score": refresh_score,
        "cognitive_state": state,
        "recommended_action": action,
        "analysis": analysis_text,
        "motivation_message": motivation_text
    }
