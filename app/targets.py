# Extensible lookup of render targets. Add an entry here to support a new
# platform — nothing elsewhere needs to change (see README decision #3).
TARGETS = {
    "claude": {
        "label": "Claude",
        "style": (
            "Write the final prompt the way a clear, conversational system/user "
            "prompt to Claude would read: plain prose, natural structure, no "
            "rigid step numbering required."
        ),
    },
    "chatgpt": {
        "label": "ChatGPT",
        "style": (
            "Write the final prompt the way a clear ChatGPT system/user prompt "
            "would read: plain prose, direct instructions, similar register to "
            "the Claude version."
        ),
    },
    "dwos": {
        "label": "DWOS",
        "style": (
            "Write the final prompt in DWOS's strict/procedural house style: "
            "step-numbered instructions, explicit ALL-CAPS anti-pattern bans for "
            "things the agent must NEVER do, and the exact expected output format "
            "spelled out in prose — because DWOS agents run unattended inside a "
            "budgeted, auditable pipeline with no human in the loop to correct "
            "them mid-run."
        ),
    },
    "langchain": {
        "label": "LangChain",
        "style": (
            "Write the final prompt as a LangChain PromptTemplate body: plain "
            "instruction text with any variable slots written as "
            "{curly_brace_placeholders} (matching LangChain's own templating "
            "syntax) instead of being filled in literally, plus a one-line "
            "comment at the top listing the input_variables names so it drops "
            "straight into `PromptTemplate(template=..., input_variables=[...])`."
        ),
    },
    "generic": {
        "label": "Generic / Other",
        "style": (
            "Write the final prompt in a plain, platform-agnostic structure that "
            "would work reasonably on any chat-based LLM."
        ),
    },
}
