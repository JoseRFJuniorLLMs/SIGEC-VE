# LLM Prompts Configuration

SYSTEM_PROMPT = """You are an expert generic AI assistant for an EV Charging System (CSMS).
Your goal is to assist operators in managing the charging network, diagnosing issues, and optimizing energy usage.
You have access to tools to interact with the system via the Model Context Protocol (MCP).
"""

DIAGNOSTIC_PROMPT = """Analyze the following logs from Charge Point {charge_point_id} and identify potential root causes for the failure.
Logs:
{logs}
"""

SMART_CHARGING_ADVICE_PROMPT = """Given the current grid load is {grid_load}% and electricity price is {price}/kWh.
Suggest a charging schedule for a vehicle connecting now that needs 30kWh by 8:00 AM tomorrow.
"""
