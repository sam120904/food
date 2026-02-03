import google.generativeai as genai
import os
import random

# HARDCODED FOR DEMO - In production, use environment variables
API_KEY = "AIzaSyD7MxJdkrgIg-51mM8JVJsyvO7oDtNmNPk"

def get_surplus_prediction(listings_data=None):
    """
    Connects to Gemini to predict future surplus based on patterns.
    Accepts context data: list of dicts with 'food_type', 'quantity', 'date'.
    """
    if not API_KEY:
        return {
            "prediction": "AI API Key is missing. Please configure the system.",
            "status": "error"
        }

    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        # internal mock fallback if no data provided, just to show something
        if not listings_data:
            context_str = "No recent data available. Provide general tips."
        else:
            # Format data for the prompt
            context_str = "Here is the recent food waste/donation data for this hotel:\n"
            for item in listings_data:
                context_str += f"- {item['date']}: {item['quantity']}kg of {item['food_type']}\n"

        prompt = (
            f"You are an AI Food Waste Analyst for a hotel. {context_str}\n\n"
            "Based on this data (or lack thereof), provide a concise strategic insight (max 3 sentences) "
            "identifying patterns and predicting what might be surplus tomorrow. "
            "Be professional and actionable."
        )
        
        response = model.generate_content(prompt)
        return {
            "prediction": response.text,
            "status": "real"
        }
    except Exception as e:
        return {
            "prediction": f"AI Experience Error: {str(e)}",
            "status": "error"
        }
