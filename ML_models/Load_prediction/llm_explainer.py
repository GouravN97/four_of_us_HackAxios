import json
import requests
from datetime import datetime

# GROQ API INTEGRATION

class LLMExplainer:
    """
    Converts model predictions to clinical explanations using Groq LLM
    """
    
    def __init__(self, api_key):
        """
        Initialize Groq LLM explainer
        
        Args:
            api_key: Groq API key (required - get from https://console.groq.com)
        """
        if not api_key:
            raise ValueError("Groq API key is required! Get one from https://console.groq.com")
        
        self.api_key = api_key
        self.endpoint = 'https://api.groq.com/openai/v1/chat/completions'
        self.model = 'llama-3.3-70b-versatile'
    
    def explain_prediction(self, prediction_data, historical_context=None):
        """
        Generate clinical explanation for prediction using Groq
        
        Args:
            prediction_data: Dict from predict_next_hour_enhanced()
            historical_context: Optional recent trends/patterns
            
        Returns:
            Dict with explanation and metadata
        """
        
        # Build prompt
        prompt = self._build_explanation_prompt(prediction_data, historical_context)
        
        # Call Groq API
        response = self._call_groq(prompt)
        
        return response
    
    def _build_explanation_prompt(self, prediction_data, historical_context):
        """
        Create structured prompt for Groq LLM
        """
        
        pred = prediction_data.copy()
        pred['predicted_arrivals'] = int(pred['predicted_arrivals'])
        pred['lower_bound'] = int(round(pred['lower_bound']))
        pred['upper_bound'] = int(round(pred['upper_bound']))
        
        reasoning = pred.get('reasoning', {})
        
        # Format timestamp
        timestamp = pred['timestamp']
        time_str = timestamp.strftime('%I:%M %p')
        day_str = timestamp.strftime('%A, %B %d')
        
        prompt = f"""You are an ER operations advisor. Explain this forecast to hospital staff in clear, actionable language.

PREDICTION SUMMARY:
- Time: {time_str} on {day_str}
- Expected arrivals: {pred['predicted_arrivals']} patients
- Expected range: {pred['lower_bound']} to {pred['upper_bound']} patients
- Confidence level: {pred['confidence_level'].upper()}

CONTEXT:
- Hour of day: {reasoning.get('hour', 'N/A')}
- Night time: {'Yes' if reasoning.get('is_night') else 'No'}
- Evening rush: {'Yes' if reasoning.get('is_evening_rush') else 'No'}
- Recent trend: {reasoning.get('recent_trend', 'stable')}
- High load recently: {'Yes' if reasoning.get('high_load_recent') else 'No'}

INSTRUCTIONS:
1. Provide a concise 2-3 sentence explanation of WHY we expect this arrival rate
2. Give ONE specific, actionable recommendation for ER staff
3. Flag any concerns if confidence is LOW or surge is predicted
4. Use simple language - avoid jargon
5. Be direct and practical

Keep response under 150 words. Structure as:
FORECAST: [brief explanation]
RECOMMENDATION: [one clear action]
[ALERT if needed]

Do not include any preamble, just provide the structured response."""

        if historical_context:
            prompt += f"\n\nRECENT PATTERNS:\n{historical_context}"
        
        return prompt
    
    def explain_custom_prompt(self, prompt):
        return self._call_groq(prompt)

    def _call_groq(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
        payload = {
        "model": self.model,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert ER operations advisor. Be concise and practical."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 300
    }

    
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )
    
        # 🔍 Debug if it fails again
        if response.status_code != 200:
            raise Exception(
                f"Groq API Error {response.status_code}: {response.text}"
            )
    
        result = response.json()
    
        return {
            "explanation": result["choices"][0]["message"]["content"].strip(),
        }

def explain_6_hour_forecast(predictions, groq_api_key):
    """
    Generate a single strategic explanation for the next 6 hours.
    
    This is an AGGREGATED explanation intended for ER decision-making,
    not a per-hour micro explanation.

    Args:
        predictions: List of dicts from predict_next_6_hours()
        groq_api_key: Groq API key (from env / secrets)

    Returns:
        dict with:
            - overall_explanation (LLM text)
            - total_expected
            - peak_hour
            - peak_count
            - hourly_predictions
    """

    explainer = LLMExplainer(api_key=groq_api_key)

    # -----------------------------
    # Summary statistics
    # -----------------------------
    total_expected = sum(p['predicted_arrivals'] for p in predictions)
    avg_per_hour = total_expected / len(predictions)

    peak_pred = max(predictions, key=lambda x: x['predicted_arrivals'])
    low_pred = min(predictions, key=lambda x: x['predicted_arrivals'])

    # -----------------------------
    # Build structured context
    # -----------------------------
    summary_context = f"""
6-HOUR FORECAST SUMMARY:
- Total expected arrivals: {total_expected} patients
- Average per hour: {avg_per_hour:.1f} patients
- Peak hour: {peak_pred['timestamp'].strftime('%I:%M %p')} 
  ({peak_pred['predicted_arrivals']} patients)
- Lowest hour: {low_pred['timestamp'].strftime('%I:%M %p')} 
  ({low_pred['predicted_arrivals']} patients)

HOURLY BREAKDOWN:
"""

    for i, pred in enumerate(predictions, start=1):
        summary_context += (
            f"Hour {i} ({pred['timestamp'].strftime('%I:%M %p')}): "
            f"{pred['predicted_arrivals']} patients "
            f"[{pred['lower_bound']}-{pred['upper_bound']}] "
            f"({pred['confidence_level']})\n"
        )

    # -----------------------------
    # LLM Prompt
    # -----------------------------
    prompt = f"""You are an ER operations advisor.

{summary_context}

INSTRUCTIONS:
1. Summarize the overall arrival trend (increasing, decreasing, or stable)
2. Identify the most critical hour requiring attention
3. Give ONE clear staffing or operational recommendation
4. Flag any surge or risk concerns if present

Keep the response under 200 words.

Format exactly as:
FORECAST: ...
CRITICAL PERIOD: ...
RECOMMENDATION: ...
[ALERT if needed]
"""

    # -----------------------------
    # Call LLM safely
    # -----------------------------
    llm_response = explainer.explain_custom_prompt(prompt)

    # -----------------------------
    # Final API-ready output
    # -----------------------------
    return {
        "overall_explanation": llm_response["explanation"],
        "total_expected": total_expected,
        "peak_hour": peak_pred["timestamp"],
        "peak_count": peak_pred["predicted_arrivals"],
        "hourly_predictions": predictions
    }