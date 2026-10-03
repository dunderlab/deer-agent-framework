# DEER: Deterministic Executable Engine for Runtime Agents

### **Stop building "Vibe-based" Agents. Start Engineering Deterministic Systems.**

----

## Customer Support AI Example

This example demonstrates the implementation of a deterministic retail assistant using the `deer` library. The agent is
designed to handle customer inquiries regarding store policies, operational hours, and product information with high
precision and strict boundary enforcement.

### Core Architecture

Unlike agentic workflows that rely on tool-calling or external API interactions, this agent operates as a
**Knowledge-Based Specialist**. Its intelligence is derived from a combination of a high-authority identity and a
curated vector memory.

#### Key Technical Features

* **Deterministic Identity:** The agent is configured with a strict persona (Senior Commerce Orchestrator) that includes
  operational guardrails. This prevents the agent from answering off-topic questions or behaving as a general-purpose
  AI.
* **Tool-less Execution:** This implementation focuses exclusively on information retrieval. It does not use tools,
  ensuring faster response times and reducing the risk of unpredictable tool-calling loops.
* **Vector Memory via JSON:** Knowledge is decoupled from the code. The agent loads its factual base from external JSON
  files, allowing for easy updates to store policies without modifying the source code.
* **Multi-Language Support:** The agent supports multiple languages by loading separate memory files (e.g.,
  `memory.json`
  for English and `memory_es.json` for Spanish), enabling it to retrieve the correct factual data regardless of the
  user's
  language.

#### Project Structure

* `agent.py`: Main entry point containing the agent configuration and REPL loop.
* `memory.json`: English operational knowledge base.
* `memory_es.json`: Spanish operational knowledge base.

#### Behavioral Constraints

The agent is programmed to follow these strict rules:

1. **Single Source of Truth:** It only provides information present in the loaded JSON memories.
1. **Out-of-Bounds Protocol:** It politely declines any request unrelated to store operations.
1. **Zero Hallucination:** If data is missing from the vector memory, the agent is instructed to refer the user to a
   human representative rather than guessing.