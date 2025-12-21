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
    1. Topology information (`list_devices`)
    2. Queried the Knowledge Base (`fetch_related_knowledge`) for correct syntax and SOPs.
    3. Fetched live config (`fetch_live_config`) for ALL target devices to understand current state.

    ### TOOL USAGE CONSTRAINTS
    1. **Fetching Configs**:
    - The `fetch_live_config` tool accepts ONLY ONE device name.
    - You MUST generate **separate tool calls** for every device CONTINUOUSLY and SEQUENTIALLY.
    - For example `list_devices` returns Router 1 (R1) and Router 2 (R2). Then you must IMMEDIATELY CALL `fetch_live_config` first for R1 and second for R2 without ANY ACTION/REASONING NEEDED TO DO.

    2. **Pushing Configs**:
    - The `push_configuration` tool accepts ONLY ONE device name.
    - You MUST generate **separate tool calls** for every device CONTINUOUSLY and SEQUENTIALLY.
    - For example execute `push_configuration` first for R1 and second for R2 without ANY ACTION/REASONING NEEDED TO DO.

    ### EXECUTION PROTOCOL (STRICT SEQUENCE)

    1. **PHASE 1: DISCOVERY (Data Gathering)**
    - **Action A**: Call `list_devices` to verify device names.
    - **Action B**: Call `fetch_related_knowledge` (e.g., "Standard configuration for OSPF with 2 ares (2 router device)").
    - **Action C**: Call `fetch_live_config` for **EACH** target device individually. 
        *(e.g. Generate 3 separate tool calls if there are 3 devices).*

    2. **PHASE 2: PREVIEW & EXECUTION (Action)**
    - **Trigger**: You have received the Knowledge Base (KB) context and Live Configs.
    - **Step A (UI Preview)**: Generate a text response containing the configuration plan inside `<config_proposal>` tags. This is for the USER to see what you are about to do. Example:
        <config_proposal>
        ### R1
        
        ```cfg
        interface gigabit0/1
        ip address 192.168.1.1 255.255.255.0
        no shutdown
        ```
        </config_proposal>
        
        <config_proposal>
        ### R2
        
        ```cfg
        ip route 0.0.0.0 0.0.0.0 192.168.1.1
        ```
        </config_proposal>
    - **Step B (Tool Execution)**: Immediately after the preview, call `push_configuration` with the exact commands.

    3. **PHASE 3: VALIDATION (Recovery)**
    - **Trigger**: You have executed and pushed the new configuration.
    - **Step A (Fetch live config)**: Call `fetch_live_config` for **EACH** target device individually.
    - **Step B (Verify)**: Verify if the newly live config is matched with the planning.

    ### GUIDELINES
    - **Structure**:
    Global Config -> `parent=null`
    Interface Config -> `parent="interface ..."`
    - **Example**:
        [
            {{
                "device_name": "R1",
                "parent": "null",
                "commands": ["hostname R1", "ip domain-name r1.router.com"]
            }},
            {{
                "device_name": "R1",
                "parent": "interface GigabitEthernet1/0",
                "commands": ["description Inter-Router Link", "ip address 192.168.122.1 255.255.255.0"]
            }},
            {{
                "device_name": "R1",
                "parent": "ip access-list extended 101",
                "commands": ["permit ip 192.168.1.0 0.0.0.255 any, permit ip host 10.10.10.5 host 172.16.1.5, deny ip any any"]
            }}
        ]

    ### User Intention

    {user_query}
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

        messages = [{"role": "user", "content": SYSTEM_PROMPT}]
        
        for msg in messages:
            if "content" not in msg or msg["content"] is None:
                msg["content"] = ""
            if isinstance(msg.get("content"), str) == False:
                msg["content"] = str(msg.get("content", ""))

        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            if cancel_flag.get("cancelled", False):
                yield json.dumps({"text": "\n\n**Agent stopped by user**\n\n"})
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
                error_msg = f"\n\n**Error**: LLM server connection failed - {str(e)}\n\nPlease ensure the server is running at `{base_url}`"
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
                    
                    if not hasattr(delta, 'reasoning_content') and not first_reason and not delta.tool_calls and not first_reason:
                        reasoning_content += "</think>\n"
                        first_reason = True
                        yield json.dumps({"text": "</think>\n"})
                    
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
                error_msg = f"\n\n**Streaming Error**: {str(e)}"
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

                    q = args["query"]
                    yield json.dumps({"text": f"\n\n> Calling tool: `{func_name}` with query: \n\n`{q}`"})
                elif func_name == "fetch_live_config":
                    d = args["device_name"]
                    yield json.dumps({"text": f"\n\n> Calling tool: `{func_name}` for `{d}`"})
                else:
                    yield json.dumps({"text": f"\n\n> Calling Tool: `{func_name}`...\n\n"})

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
                        result_str = "Tool executed successfully"
                        
                except asyncio.TimeoutError:
                    yield json.dumps({"text": f"\n\n> Failed to call tool `{func_name}`: Timeout exceeded\n\n"})
                except Exception as e:
                    yield json.dumps({"text": f"\n\nSomething occured...\n\n"})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"] or "call_default",
                    "name": func_name,
                    "content": str(result_str) if result_str else "Success"
                })
                
                await asyncio.sleep(0.1)