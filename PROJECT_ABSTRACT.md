# [Format of the Abstract]

**Project Title** : F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant for You

**Project Group No.** : _______.

**Number of Scholar(s)** : _______.

**Supervisor Name** : _______________________________________.

---

## *Abstract:*

**F.R.I.D.A.Y. (Fully Responsive Intelligent Digital Assistant for You)** is a Tony Stark-inspired, real-time voice-controlled AI assistant built upon a modular, provider-agnostic architecture. The system addresses a critical gap in the current landscape of voice assistants — the absence of an open-source, extensible platform that combines low-latency voice interaction with a dynamically extensible tool ecosystem. Unlike vendor-locked assistants such as Siri, Alexa, or Google Assistant, F.R.I.D.A.Y. enables developers and users to plug in custom back-end capabilities and swap AI providers without modifying core application logic.

The system is architected as two cooperating services. The first component is an **MCP (Model Context Protocol) Server**, built using the FastMCP framework, which exposes a suite of tools — including live global news retrieval from RSS feeds (BBC, CNBC, NYT, Al Jazeera), web search, URL content fetching, system introspection, a visual World Monitor dashboard launcher, and text utility functions — over a Server-Sent Events (SSE) transport. The second component is a **LiveKit Voice Agent** that implements a real-time speech pipeline: user speech is captured via microphone, processed through a Voice Activity Detection module (Silero VAD), transcribed using a configurable Speech-to-Text provider (Sarvam Saaras v3 or OpenAI Whisper), reasoned upon by a Large Language Model (Google Gemini 2.5 Flash or OpenAI GPT-4o), and the generated response is synthesized back into natural speech using a Text-to-Speech provider (OpenAI TTS with the "nova" voice or Sarvam Bulbul v3). The voice agent connects to the MCP server in real time, enabling the LLM to invoke any registered tool dynamically during a conversation.

The key technical contributions of the project are: a **plug-in tool architecture** where new capabilities can be added by simply creating a Python file in the `friday/tools/` directory and registering it — requiring no changes to the core server code; a **provider-agnostic AI pipeline** allowing STT, LLM, and TTS providers to be swapped via a single configuration constant; **multilingual support** with automatic language detection, enabling the assistant to respond in the same language the user speaks (including multiple Indian languages); real-time **concurrent RSS feed aggregation** using Python's `asyncio.gather` for parallel HTTP requests; and a **React-based web playground** front-end with LiveKit integration, featuring real-time audio bar visualization, room connection management via a dedicated token server, and quick-command discovery cards.

*The development environment and tools used for this project include **Visual Studio Code (VS Code):** a free, open-source, and highly customizable code editor serving as the primary IDE for both Python back-end and React/TypeScript front-end development. **uv:** a fast Python package manager by Astral, used for dependency resolution, virtual environment management, and running project scripts. **Vite:** a next-generation front-end build tool providing instant Hot Module Replacement (HMR) for the React playground UI. **Git:** a distributed version control system used for source code management and collaboration. **LiveKit Cloud:** a real-time WebRTC-based audio/video infrastructure service providing room management, token-based authentication, and low-latency audio streaming. **Node.js and npm:** used for managing front-end dependencies and running the React development server.*

---

---

## **Scholar(s) Details**

| Name of the Scholar | IAR Reg. No. |
|---|---|
| _______________________________________ | ________________ |
| _______________________________________ | ________________ |
| _______________________________________ | ________________ |
