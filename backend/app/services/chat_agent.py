"""Tool-using conversational agent for the RealityShield-AI dashboard."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Prototype storage only. Move this to Redis or a database for production deployments.
_SESSION_HISTORY: Dict[str, List[Dict[str, Any]]] = {}
_MAX_HISTORY_MESSAGES = 12
_MAX_TOOL_ROUNDS = 4

SYSTEM_PROMPT = """You are RealityShield-AI's road-safety assistant.
Answer using the uploaded recorded-video context supplied in the conversation and the
available backend tools. Never ask for a camera ID: this application analyzes an uploaded
recorded video, not a live camera. Explain results in plain language, mention uncertainty,
and never claim that you performed a calculation outside the tools. Ground every number in
the supplied context. Detection totals are observations across sampled frames and do not
necessarily represent unique people or vehicles. Never invent measurements, locations, routes,
weather, or risk factors. The displayed risk score is a prototype estimate, not a guarantee.
Route ids such as route_a and route_b come from demo candidates, not a live map service.
If a reliable input is unavailable, say so directly instead of filling it with a guess.
"""

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_risk_score",
            "description": "Get the current safety risk score for a location using the risk agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Road, area, or landmark."},
                    "context": {
                        "type": "object",
                        "description": "Optional known scene context such as camera_id or traffic features.",
                        "additionalProperties": True,
                    },
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_route_recommendation",
            "description": "Compare route candidates and return the safest route.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Trip origin."},
                    "destination": {"type": "string", "description": "Trip destination."},
                    "context": {"type": "object", "description": "Existing route recommendation, if available."},
                },
                "required": ["source", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_risk",
            "description": "Explain the main factors behind a risk assessment for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Road, area, or landmark."},
                    "context": {"type": "object", "description": "Current risk score and factors from the dashboard."},
                },
                "required": ["location"],
            },
        },
    },
]


def _call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Return only facts available in the analyzed-video context."""
    context = arguments.get("context") if isinstance(arguments.get("context"), dict) else {}

    if name == "get_risk_score":
        location = str(arguments.get("location", "")).strip()
        if not location:
            return {"clarification_needed": "Which location or road should I assess?"}
        risk = context.get("risk")
        if isinstance(risk, dict) and risk.get("score") is not None:
            return {"location": location, "risk": risk, "source": "uploaded-video dashboard analysis"}
        return {"unavailable": "No analyzed risk score was supplied. Do not estimate one from missing measurements."}

    if name == "get_route_recommendation":
        source = str(arguments.get("source", "")).strip()
        destination = str(arguments.get("destination", "")).strip()
        if not source or not destination:
            return {"clarification_needed": "Please provide both the starting point and destination."}
        route = context.get("route")
        if isinstance(route, dict) and route:
            return {"route": route, "source": "uploaded-video dashboard context"}
        return {"unavailable": "No live road-network route candidates are available, so do not invent a route."}

    if name == "explain_risk":
        location = str(arguments.get("location", "")).strip()
        risk = context.get("risk")
        if isinstance(risk, dict) and risk.get("factors"):
            return {"location": location or context.get("location", "Location not provided"), "risk": risk, "source": "uploaded-video dashboard analysis"}
        return {"unavailable": "No risk factors were supplied for this video."}

    return {"error": f"Unsupported tool: {name}"}

def _parse_arguments(raw_arguments: Any) -> Dict[str, Any]:
    """Normalize provider-specific function arguments into a dictionary."""
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if isinstance(raw_arguments, str):
        try:
            parsed = json.loads(raw_arguments)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return dict(raw_arguments or {})


def _configuration_message(provider: str) -> str:
    """Return an actionable response when the selected provider is not configured."""
    key_name = "GEMINI_API_KEY" if provider == "gemini" else "GROQ_API_KEY"
    return f"Chatbot is not configured yet. Set LLM_PROVIDER={provider} and {key_name} in backend/.env, then restart the backend."


def _chat_with_groq(messages: List[Dict[str, Any]], tools_used: List[str]) -> str:
    """Run the tool loop through the Groq OpenAI-compatible API."""
    from groq import Groq

    client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=5.0, max_retries=0)
    messages_for_api = list(messages)
    for _ in range(_MAX_TOOL_ROUNDS):
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            messages=messages_for_api,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
        )
        message = completion.choices[0].message
        tool_calls = message.tool_calls or []
        if not tool_calls:
            return message.content or "I could not produce a response from the available road-safety data."

        messages_for_api.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [call.model_dump() for call in tool_calls],
        })
        for tool_call in tool_calls:
            name = tool_call.function.name
            tools_used.append(name)
            result = _call_tool(name, _parse_arguments(tool_call.function.arguments))
            messages_for_api.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": json.dumps(result, default=str),
            })
    return "I could not complete the tool-assisted answer. Please try the question again."


def _chat_with_gemini(messages: List[Dict[str, Any]], tools_used: List[str]) -> str:
    """Run the tool loop through Google's Gemini function-calling API."""
    import google.generativeai as genai
    from google.generativeai import protos

    def to_gemini_schema(schema: Dict[str, Any]) -> Any:
        """Convert JSON Schema's lowercase type strings to Gemini proto enums."""
        type_name = str(schema.get("type", "object")).upper()
        schema_fields: Dict[str, Any] = {"type": getattr(protos.Type, type_name)}
        if schema.get("description"):
            schema_fields["description"] = schema["description"]
        if schema.get("required"):
            schema_fields["required"] = schema["required"]
        if schema.get("properties"):
            schema_fields["properties"] = {
                name: to_gemini_schema(property_schema)
                for name, property_schema in schema["properties"].items()
            }
        if schema.get("items"):
            schema_fields["items"] = to_gemini_schema(schema["items"])
        return protos.Schema(**schema_fields)

    function_declarations = [
        protos.FunctionDeclaration(
            name=tool["function"]["name"],
            description=tool["function"]["description"],
            parameters=to_gemini_schema(tool["function"]["parameters"]),
        )
        for tool in TOOL_SCHEMAS
    ]
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(
        os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        system_instruction=SYSTEM_PROMPT,
        tools=[protos.Tool(function_declarations=function_declarations)],
    )
    history = [
        {"role": "model" if item["role"] == "assistant" else "user", "parts": [item["content"]]}
        for item in messages[:-1]
        if item.get("content")
    ]
    session = model.start_chat(history=history)
    response = session.send_message(messages[-1]["content"], request_options={"timeout": 5.0})
    for _ in range(_MAX_TOOL_ROUNDS):
        calls = [part.function_call for part in response.parts if getattr(part, "function_call", None)]
        if not calls:
            return response.text
        function_responses = []
        for call in calls:
            name = call.name
            tools_used.append(name)
            result = _call_tool(name, dict(call.args))
            function_responses.append(
                protos.Part(function_response=protos.FunctionResponse(name=name, response={"result": result}))
            )
        response = session.send_message(protos.Content(role="user", parts=function_responses), request_options={"timeout": 5.0})
    return "I could not complete the tool-assisted answer. Please try the question again."


def _context_grounded_reply(user_message: str, context: Dict[str, Any]) -> str:
    """Give a limited but evidence-grounded answer if both hosted models fail."""
    question = user_message.casefold()
    file_name = context.get("video")
    counts = context.get("detections") if isinstance(context.get("detections"), dict) else {}
    risk = context.get("risk") if isinstance(context.get("risk"), dict) else {}
    route = context.get("route") if isinstance(context.get("route"), dict) else {}
    prefix = "I'm answering from the local dashboard data while the hosted language model is unavailable. "

    if question.strip(" !?.") in {"hi", "hello", "hey", "good morning", "good afternoon"} or any(
        phrase in question for phrase in ("what can you do", "how can you help", "what do you know")
    ):
        return prefix + "I can explain the analyzed video's object counts, risk score and factors, recorded location, or route result. Ask me about any of those dashboard results."

    if not file_name:
        if any(word in question for word in ("safe", "safety", "pedestrian", "speed", "road")):
            return prefix + "As general guidance, slow down near pedestrians, keep a safe following distance, and obey local signs. Upload and analyze a recording for video-specific findings."
        return prefix + "There is no analyzed video attached yet, so I cannot give recording-specific findings."

    if any(word in question for word in ("route", "destination", "way")):
        if route.get("route_id"):
            if route.get("route_id") in {"route_a", "route_b"}:
                return prefix + "The dashboard's route_a / route_b result is based on demonstration candidates, not live road-network data. It is not a verified turn-by-turn route."
            return prefix + f"The dashboard recommends {route['route_id']}. Its displayed route risk is {route.get('risk_score', 'not available')}. This is the route result currently supplied by the app."
        return prefix + "The dashboard has no live road-network route result for this recording. I cannot verify a route from the video alone."

    if any(word in question for word in ("why", "factor", "risk", "critical", "score")):
        score = risk.get("score")
        severity = risk.get("severity")
        factors = risk.get("factors") if isinstance(risk.get("factors"), dict) else {}
        details = []
        if score is not None:
            details.append(f"the dashboard score is {round(float(score) * 100)}% ({severity or 'severity unavailable'})")
        if factors:
            top_factors = sorted(factors.items(), key=lambda item: float(item[1] or 0), reverse=True)[:3]
            details.append("the strongest supplied factors are " + ", ".join(f"{name.replace('_', ' ')} ({value})" for name, value in top_factors))
        if details:
            return prefix + "; ".join(details) + ". The score is a prototype estimate from the dashboard inputs, not a guaranteed prediction."

    if any(word in question for word in ("how many", "count", "detected", "objects", "vehicles", "pedestrians", "people", "truck", "bike", "car")):
        normalized = {str(name).casefold(): value for name, value in counts.items()}
        if any(word in question for word in ("pedestrian", "people", "person")):
            number = normalized.get("pedestrian", normalized.get("person"))
            if number is not None:
                return prefix + f"The dashboard lists {number} pedestrians/people for this video."
        if "truck" in question and normalized.get("truck") is not None:
            return prefix + f"The dashboard lists {normalized['truck']} trucks for this video."
        if any(word in question for word in ("bike", "bicycle", "motorcycle")) and normalized.get("bike", normalized.get("motorcycle")) is not None:
            return prefix + f"The dashboard lists {normalized.get('bike', normalized.get('motorcycle'))} bikes for this video."
        if "car" in question and normalized.get("car") is not None:
            return prefix + f"The dashboard lists {normalized['car']} cars for this video."
        if any(word in question for word in ("vehicle", "vehicles")):
            vehicle_count = context.get("vehicles")
            if vehicle_count is not None:
                return prefix + f"The dashboard lists {vehicle_count} vehicles for this video."
        if context.get("total_detections") is not None:
            return prefix + f"The detector returned {context['total_detections']} observations across sampled frames. Those are not necessarily unique road users."

    if any(word in question for word in ("weather", "temperature", "rain")):
        return prefix + "Weather details are not included in the chatbot context, so I can't verify conditions for this recording."

    total = context.get("total_detections")
    observed = [f"{count} {name}" for name, count in counts.items() if count]
    summary = f"The analyzed file is {file_name}."
    if total is not None:
        summary += f" The detector returned {total} observations across sampled frames; those are not necessarily unique road users."
    if observed:
        summary += " Recorded classes: " + ", ".join(observed) + "."
    if risk.get("severity"):
        summary += f" The dashboard risk is {risk['severity']} ({round(float(risk.get('score', 0)) * 100)}%)."
    location = context.get("location")
    if location:
        summary += f" Video location: {location}."
    else:
        summary += " No video location was provided."
    return prefix + summary

def chat(session_id: str, user_message: str, conversation_history: Sequence[Dict[str, Any]] | None = None, context: Dict[str, Any] | None = None) -> Tuple[str, List[str], str]:
    """Answer a user message with provider-selected function calling and session memory."""
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider not in {"gemini", "groq"}:
        return "Unsupported LLM_PROVIDER. Choose gemini or groq in backend/.env.", [], "unavailable"

    history = _SESSION_HISTORY.setdefault(session_id, [])
    if not history and conversation_history:
        history.extend(list(conversation_history)[-_MAX_HISTORY_MESSAGES:])
    history.append({"role": "user", "content": user_message})
    context_message = "Uploaded video analysis context: " + json.dumps(context or {}, default=str)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context_message},
    ] + history[-_MAX_HISTORY_MESSAGES:]
    tools_used: List[str] = []

    providers = [provider]
    alternate = "gemini" if provider == "groq" else "groq"
    alternate_key = "GEMINI_API_KEY" if alternate == "gemini" else "GROQ_API_KEY"
    if os.getenv(alternate_key):
        providers.append(alternate)

    reply = None
    used_provider = "context"
    for active_provider in providers:
        key_name = "GEMINI_API_KEY" if active_provider == "gemini" else "GROQ_API_KEY"
        if not os.getenv(key_name):
            continue
        try:
            reply = _chat_with_gemini(messages, tools_used) if active_provider == "gemini" else _chat_with_groq(messages, tools_used)
            used_provider = active_provider
            break
        except Exception as error:
            logger.warning("Safety copilot provider %s failed (%s)", active_provider, type(error).__name__)
            tools_used.clear()
            if any(token in type(error).__name__.casefold() for token in ("connection", "timeout", "connecterror")):
                break

    if reply is None:
        reply = _context_grounded_reply(user_message, context or {})

    history.append({"role": "assistant", "content": reply})
    _SESSION_HISTORY[session_id] = history[-_MAX_HISTORY_MESSAGES:]
    return reply, tools_used, used_provider


def reset_session(session_id: str) -> None:
    """Clear the in-memory conversation history for one session."""
    _SESSION_HISTORY.pop(session_id, None)


def chat_timestamp() -> str:
    """Return a timezone-aware ISO timestamp for API responses."""
    return datetime.now(timezone.utc).isoformat()
