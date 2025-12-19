from openai import AsyncOpenAI
from typing import List, AsyncGenerator
from fastapi.concurrency import run_in_threadpool
from fastmcp import Client

import json
import httpx
import aiohttp
import asyncio
import re

from copy import deepcopy

from services import chat
from app.mcp.server import mcp

from config import LIGHTRAG_URL, LLAMA_SERVER_URL

mcp_client = Client(mcp)

active_agent_tasks = {}

async def query_context(query: str, model: str, mode: str = "hybrid"):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "query": query,
                "mode": mode,
                "only_need_context": True,
                "only_need_prompt": False,
                "response_type": "Multiple Paragraphs",
                "top_k": 60,
                "chunk_top_k": 10,
                "max_entity_tokens": 1000,
                "max_relation_tokens": 1000,
                "max_total_tokens": 4096,
                "enable_rerank": False,
                "include_references": False,
                "include_chunk_content": False,
                "stream": False
            }

            response = await client.post(f"{LIGHTRAG_URL[model]}/query/stream", json=payload)
            
            if response.status_code != 200:
                return f"Error: LLM Server returned status {response.status_code}"
            
            return response.text
        
    except Exception as e:
        return f"Failed to reach {LIGHTRAG_URL[model]}: {e}"

async def response_generator(payload, current_session_id, model: str):
    full_response_text = []
    
    async with aiohttp.ClientSession() as client:
        async with client.post(f"{LIGHTRAG_URL[model]}/query/stream", json=payload) as response:
            if response.status != 200:
                yield f"data: {json.dumps({'error': f'LLM Server Error: {response.status}'})}\n\n"
                return

            async for line_bytes in response.content:
                line = line_bytes.decode('utf-8').strip()
                if not line:
                    continue

                if line.startswith("data:"):
                    line = line[5:].strip()

                try:
                    data = json.loads(line)
                    
                    if "references" in data:
                        continue

                    if "response" in data:
                        text = data["response"]

                        if text:
                            full_response_text.append(text)
                            # Safe Yield
                            yield f"data: {json.dumps({'text': text})}\n\n"

                except json.JSONDecodeError:
                    continue

    if full_response_text:
        complete = "".join(full_response_text)
        await run_in_threadpool(
            chat.save_chat_message,
            current_session_id,
            "assistant",
            complete
        )

async def run_agent_loop(topology_id: str, user_query: str, history: List[dict], model: str, session_id: str = None) -> AsyncGenerator[str, None]:
    """
    Runs the ReAct (Reasoning + Acting) loop.
    """
    
    cancel_flag = {"cancelled": False}
    if session_id:
        active_agent_tasks[session_id] = cancel_flag
    
    base_url = LLAMA_SERVER_URL[model] if isinstance(LLAMA_SERVER_URL, dict) else LLAMA_SERVER_URL
    
    client = AsyncOpenAI(
        api_key="secret",
        base_url=base_url,
        timeout=60.0
    )

    SYSTEM_PROMPT = f"""
    You are a Senior Network Automation Engineer managing Topology ID: {topology_id}.

    ### CORE PRINCIPLE: "KNOWLEDGE FIRST"
    You are PROHIBITED from generating or pushing any configuration commands until you have:
    1. Queried the Knowledge Base (`fetch_related_knowledge`) for correct syntax and SOPs
    2. Fetched live config (`fetch_live_config`) to understand current device state
    
    Your mental model: "I do not know the correct syntax or SOP until I check the database."

    ### CONFIGURATION TOOL USAGE
    **Batch Operations are MANDATORY**:
    - Call `push_configuration` ONCE with all device configurations.

    Structure arguments:
    1. **Single Device**: `device_configs=[{{"device_name": "R1", "commands": [...], "parent": "..."}}]`
    2. **Multiple Devices**: `device_configs=[{{"device_name": "R1", ...}}, {{"device_name": "R2", ...}}]`
    3. **Global Config**: `parent=""` or omit parent field

    ### EXECUTION PROTOCOL (STRICT SEQUENCE)

    1. **PHASE 1: DISCOVERY & KNOWLEDGE (First Turn)**
    - **Objective**: Gather all necessary information.
    - **Internal Thought**: Plan your steps in the `<think>` block.
    - **Action A**: IMMEDIATELY call `fetch_related_knowledge` (e.g., "How to configure OSPF on Cisco IOS").
    - **Action B**: Call `fetch_live_config` for ALL affected devices (can run in parallel with Action A).
    - **CONSTRAINT**: Do NOT output any conversational text outside of `<think>` in this phase. Only Tool Calls.

    2. **PHASE 2: VALIDATION & EXECUTION (Second Turn)**
    - **Trigger**: You now have KB results and Live Configs.
    - **Action**: Analyze the outputs carefully:
      * Verify syntax from KB matches your planned commands
      * Check live config for conflicts or dependencies (e.g., remove old IP before adding new)
      * Ensure commands won't break connectivity
    - **Action**: Explain to user what you're about to do and why it's safe
    - **Action**: Call `push_configuration` with validated commands
    - **Text**: After push completes, summarize what was changed

    ### GUIDELINES
    - **Context**: `topology_id` is injected automatically.
    - **Start**: Your first thought should always be: "I need to check the Knowledge Base for SOPs."
    - **Safety**: Always validate against KB and live config before pushing
    - **No Approval**: After validation, proceed directly to push - no user approval needed

    ### EXAMPLE START
    User: "Change IP on R1 Gi0/0 to 10.1.1.1/24"
    You:
    <think>
    User wants IP change on R1.
    Plan:
    1. Check KB for Cisco IOS IP configuration syntax
    2. Fetch R1 current config to see existing IP
    3. Validate and push commands
    </think>
    [TOOL_CALL: fetch_related_knowledge(query="Cisco IOS configure IP address on interface")]
    [TOOL_CALL: fetch_live_config(device_name="R1")]
    """

    async with mcp_client:
        mcp_tools = await mcp_client.list_tools()

        openai_tools = []
        
        for tool in mcp_tools:
            schema = deepcopy(tool.inputSchema) if tool.inputSchema else {"type": "object", "properties": {}}

            props = schema.get("properties", {})
            required = schema.get("required", [])
            
            if "topology_id" in props: del props["topology_id"]
            if "topology_id" in required: required.remove("topology_id")
                
            if "model_name" in props: del props["model_name"]
            if "model_name" in required: required.remove("model_name")

            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema
                }
            })

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_query}]
        
        for msg in messages:
            if "content" not in msg or msg["content"] is None:
                msg["content"] = ""
            if isinstance(msg.get("content"), str) == False:
                msg["content"] = str(msg.get("content", ""))

        max_iterations = 10
        iteration = 0
        ansible_retry_count = {}
        
        while iteration < max_iterations:
            if cancel_flag.get("cancelled", False):
                yield json.dumps({"text": "\n\n⚠️ **Agent stopped by user**\n\n"})
                break
            
            iteration += 1
            
            total_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4
            if total_tokens > 45000:
                messages_truncated = [messages[0]]
                for msg in reversed(messages[1:]):
                    msg_tokens = len(str(msg.get("content", ""))) // 4
                    if total_tokens - msg_tokens < 45000:
                        messages_truncated.insert(1, msg)
                        total_tokens -= msg_tokens
                    else:
                        break
                messages = messages_truncated
            
            for msg in messages:
                if "content" not in msg or msg["content"] is None:
                    msg["content"] = ""
                # else:
                #     msg["content"] = re.sub(r'<think>.*?</think>', ' ', msg["content"], flags=re.DOTALL).strip()
                if "role" in msg and msg["role"] == "assistant":
                    if "tool_calls" in msg and msg["tool_calls"]:
                        if not msg.get("content"):
                            msg["content"] = ""
            
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto",
                    stream=True,
                )
            except Exception as e:
                error_msg = f"\n\n❌ **Error**: LLM server connection failed - {str(e)}\n\nPlease ensure the server is running at `{base_url}`"
                yield json.dumps({"text": error_msg})
                return

            tool_calls = []
            current_content = ""
            reasoning_content = ""
            finish_reason = None

            first_reason = True
            
            try:
                async for chunk in response:
                    delta = chunk.choices[0].delta
                    finish_reason = chunk.choices[0].finish_reason

                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        if first_reason:
                            reasoning_content += "<think>"
                            yield json.dumps({"text": "<think>"})
                            first_reason = False

                        reasoning_content += delta.reasoning_content
                        yield json.dumps({"text": delta.reasoning_content})
                    
                    if not hasattr(delta, 'reasoning_content') and not first_reason and not delta.content and not delta.tool_calls:
                        reasoning_content += "</think> "
                        yield json.dumps({"text": "</think> "})
                    
                    if delta.content:
                        current_content += delta.content
                        yield json.dumps({"text": delta.content})

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if len(tool_calls) <= tc.index:
                                tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                            if tc.id: tool_calls[tc.index]["id"] = tc.id
                            if tc.function.name: tool_calls[tc.index]["function"]["name"] = tc.function.name
                            if tc.function.arguments: tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments
            except Exception as e:
                error_msg = f"\n\n❌ **Streaming Error**: {str(e)}"
                yield json.dumps({"text": error_msg})
                return

            if finish_reason == "stop" and not tool_calls:
                break
            
            if not tool_calls:
                break
            
            assistant_msg = {
                "role": "assistant",
                "content": current_content or "",
                "tool_calls": [
                    {
                        "id": tc["id"] or "call_default",
                        "type": "function",
                        "function": tc["function"]
                    } for tc in tool_calls
                ]
            }

            messages.append(assistant_msg)

            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except:
                    args = {}

                args["topology_id"] = topology_id
                if func_name == "fetch_related_knowledge":
                    args["model_name"] = model

                yield json.dumps({"text": f"\n\n> Calling Tool: `{func_name}`...\n\n"})
                
                if func_name == "push_configuration":
                    device_configs = args.get("device_configs", [])
                    skip_execution = False
                    
                    for config in device_configs:
                        device_key = config.get("device_name", "unknown")
                        if device_key not in ansible_retry_count:
                            ansible_retry_count[device_key] = 0
                        
                        if ansible_retry_count[device_key] >= 2:
                            result_str = f"Error: Maximum retry limit (2) reached for device {device_key}. Please check device connectivity and try again later."
                            yield json.dumps({"text": f"\n\n❌ **Max Retries Exceeded for {device_key}**: {result_str}\n\n"})
                            skip_execution = True
                    
                    if skip_execution:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"] or "call_default",
                            "name": func_name,
                            "content": "Execution cancelled due to max retry limit on one or more devices."
                        })
                        continue
                
                try:
                    result = await asyncio.wait_for(
                        mcp_client.call_tool(func_name, args),
                        timeout=120.0
                    )
                    
                    if result.content and len(result.content) > 0:
                        result_str = result.content[0].text or ""
                    else:
                        result_str = str(result) or ""
                    
                    if not result_str:
                        result_str = "Tool executed successfully (no output)"
                    
                    if func_name == "push_configuration":
                        device_configs = args.get("device_configs", [])
                        for config in device_configs:
                            device_key = config.get("device_name", "unknown")
                            if "Error" in result_str or "Failed" in result_str:
                                ansible_retry_count[device_key] += 1
                            else:
                                ansible_retry_count[device_key] = 0
                        
                except asyncio.TimeoutError:
                    result_str = f"Error: Tool '{func_name}' timed out after 120 seconds. This may indicate the Ansible runner is stuck or the device is unreachable."
                    yield json.dumps({"text": f"\n\n⚠️ **Timeout**: {result_str}\n\n"})
                    if func_name == "push_configuration":
                        device_configs = args.get("device_configs", [])
                        for config in device_configs:
                            device_key = config.get("device_name", "unknown")
                            ansible_retry_count[device_key] += 1
                except Exception as e:
                    result_str = f"Error: {str(e)}"
                    yield json.dumps({"text": f"\n\n❌ **Tool Error**: {result_str}\n\n"})
                    if func_name == "push_configuration":
                        device_configs = args.get("device_configs", [])
                        for config in device_configs:
                            device_key = config.get("device_name", "unknown")
                            ansible_retry_count[device_key] += 1

                if func_name == "push_configuration":
                    yield json.dumps({"text": f"\n\n✅ **Configuration Pushed Successfully**\n\n{result_str}\n\n"})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"] or "call_default",
                    "name": func_name,
                    "content": str(result_str) if result_str else "Success"
                })
                
                await asyncio.sleep(0.1)
        
        if session_id and session_id in active_agent_tasks:
            del active_agent_tasks[session_id]

def stop_agent_task(session_id: str):
    if session_id in active_agent_tasks:
        active_agent_tasks[session_id]["cancelled"] = True
        return True
    return False