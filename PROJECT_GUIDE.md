Absolutely. This document is the **complete technical documentation of your F.R.I.D.A.Y. AI Voice Assistant project**. I’ll explain it in **very simple language**, section by section, so you can understand it and explain it in your **viva/presentation**.

The project is:

> **F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant for You**

It is basically an **Iron Man–style AI voice assistant** that listens to your voice, understands it using an LLM, can use external tools such as web search/news/system information, and replies back using voice. turn0file0

---

# 1. What exactly is your project?

Think of F.R.I.D.A.Y. as a combination of:

**Microphone + Speech Recognition + AI Brain + Tools + Voice Output**

The basic flow is:

```text
             👤 USER
                │
                │ Speaks
                ▼
        🎙️ Speech Input
                │
                ▼
        🧠 Speech-to-Text
                │
                ▼
          🤖 LLM / AI Brain
                │
        ┌───────┴────────┐
        │                │
   Simple Answer     Need Tool?
        │                │
        │               YES
        │                ▼
        │          🔧 MCP Server
        │          /     |      \
        │       News   Web    System
        │                │
        │                ▼
        │          Tool Result
        │                │
        └────────┬───────┘
                 ▼
             🧠 LLM
                 │
                 ▼
          🔊 Text-to-Speech
                 │
                 ▼
              👤 USER
```

So, in one sentence:

**F.R.I.D.A.Y. listens → understands → thinks → uses tools if necessary → generates an answer → speaks the answer.**

---

# 2. Why was this project created?

The documentation says traditional assistants like Siri, Alexa and Google Assistant have limitations when it comes to **custom tools, extensibility and provider flexibility**.

Your project tries to solve this by creating a customizable voice assistant where developers can add their own tools.

For example, you can tell F.R.I.D.A.Y.:

> "What's the latest world news?"

It can use its news tool.

Or:

> "Search the web for the latest AI developments."

It can use the web-search tool.

Or:

> "What operating system am I using?"

It can use the system-information tool.

The documentation identifies four major requirements:

1. Real-time voice interaction
2. Extensible tools
3. Ability to change AI providers
4. Multilingual support turn0file0

---

# 3. Main features of your project

Your documentation identifies **8 major needs**.

## 3.1 Voice-first interaction

The user doesn't need to type.

You speak through your microphone.

```text
Your Voice
    ↓
Speech Recognition
    ↓
AI
    ↓
Voice Response
```

For example:

> User: "Hello Friday"

F.R.I.D.A.Y.:

> "Good evening, boss."

---

# 4. Live News Retrieval 📰

F.R.I.D.A.Y. can retrieve current news.

It uses RSS feeds from:

- BBC
- CNBC
- New York Times
- Al Jazeera

These feeds are fetched concurrently.

So if you ask:

> "Give me today's world news."

The system can retrieve headlines from these sources and provide a briefing.

This is implemented through the **MCP Server**. turn0file0

---

# 5. Web Search 🌐

F.R.I.D.A.Y. has a `search_web` tool.

Suppose you ask:

> "Search the web for Python 3.13."

The AI can call:

```text
search_web()
```

and get search results.

This is important because the LLM itself doesn't necessarily have to know everything beforehand.

Instead:

```text
User Question
      ↓
LLM
      ↓
Needs external information?
      ↓
YES
      ↓
search_web()
      ↓
Search Results
      ↓
LLM
      ↓
Final Answer
```

---

# 6. URL Fetching

Another tool is:

```text
fetch_url()
```

This allows F.R.I.D.A.Y. to retrieve text from a particular webpage.

For example:

> "Read this webpage and tell me what it says."

The tool retrieves the page content, with the documented output truncated to **4000 characters**. turn0file0

---

# 7. System Information 💻

F.R.I.D.A.Y. can inspect the computer it's running on.

For example, it can provide:

- Current date
- Current time
- Operating system
- OS version
- Machine architecture
- Python version

So you could ask:

> "Friday, what operating system am I using?"

The system can call:

```text
get_system_info()
```

---

# 8. World Monitor 🌍

Your project can also open:

```text
worldmonitor.app
```

in the user's browser.

This gives a visual dashboard for global information.

The documentation says this can also happen automatically after requesting a news briefing. turn0file0

---

# 9. The most important concept: MCP

This is probably one of the **most important things to understand for your viva**.

## What is MCP?

**MCP = Model Context Protocol**

It provides a standardized way for an AI model to communicate with external tools, resources and prompts.

Your MCP server is built using:

**FastMCP**

The documentation describes MCP as the protocol used for exposing tools, prompts and resources to LLMs. turn0file0

Think of MCP as a **bridge between the AI brain and external functionality**.

```text
                🤖 LLM
                  │
                  │ MCP
                  ▼
            🔧 MCP SERVER
             /    |    \
            /     |     \
         News    Web   System
         Tool    Tool   Tool
```

Without tools:

```text
User → LLM → Answer
```

With MCP:

```text
User
 ↓
LLM
 ↓
MCP
 ↓
External Tool
 ↓
Result
 ↓
LLM
 ↓
Answer
```

---

# 10. Your MCP tools

Your MCP server contains different categories of functionality.

### Web tools

```text
search_web()
fetch_url()
open_world_monitor()
get_world_news()
```

### System tools

```text
get_current_time()
get_system_info()
```

### Utility tools

For example:

```text
format_json()
count_words()
```

### Prompt templates

You also have:

```text
summarize
explain_code
```

These are reusable prompts exposed through MCP. turn0file0

---

# 11. Speech-to-Text — STT 🎙️➡️📝

**STT = Speech-to-Text**

It converts your voice into text.

Example:

```text
🎙️ "What is artificial intelligence?"
              ↓
       Speech-to-Text
              ↓
"What is artificial intelligence?"
```

Your documentation specifies:

### Default

**Sarvam Saaras v3**

### Alternative

**OpenAI Whisper**

Deepgram is also listed as an optional STT service. turn0file0

---

# 12. LLM — The Brain 🧠

After speech becomes text, the text goes to the **Large Language Model**.

Your documented options are:

### Default

**Google Gemini 2.5 Flash**

### Alternative

**OpenAI GPT-4o**

The LLM decides what the user wants and whether it needs to use a tool. turn0file0

Example:

```text
User:
"What's the current time?"

        ↓

STT

        ↓

"What is the current time?"

        ↓

LLM

        ↓

"I need the current system time."

        ↓

get_current_time()

        ↓

Result

        ↓

LLM

        ↓

"The current time is..."
```

---

# 13. Text-to-Speech — TTS 🔊

**TTS = Text-to-Speech**

It converts the final AI response into voice.

Example:

```text
AI Text:
"The current time is 11:30 PM."

       ↓

      TTS

       ↓

🔊 Spoken response
```

Your documented providers are:

- OpenAI TTS — `nova`
- Sarvam Bulbul v3

turn0file0

---

# 14. VAD — Voice Activity Detection

Your project also uses:

**Silero VAD**

VAD means:

> **Voice Activity Detection**

Its job is to determine when the user is actually speaking.

For example:

```text
Silence
   ↓
"Hello Friday"
   ↓
Speech detected
   ↓
Process audio
   ↓
Silence
```

So it helps separate **speech from silence/noise**.

---

# 15. Complete Voice Pipeline

This is one of the most important diagrams to memorize.

Your documentation breaks the Voice Agent into five stages:

```text
🎙️ Audio Input
      │
      ▼
1. Voice Activity Detection
      │
      ▼
2. Speech-to-Text
      │
      ▼
3. LLM Reasoning
      │
      ▼
4. Tool Dispatcher
      │
      ▼
5. Text-to-Speech
      │
      ▼
🔊 Audio Output
```

The detailed documentation specifically defines these as VAD, STT, LLM reasoning, MCP tool dispatching and TTS. turn0file0

---

# 16. What is LiveKit?

**LiveKit** is responsible for the real-time audio communication.

Think of LiveKit as the **real-time communication layer**.

```text
User Microphone
       ↓
   LiveKit Room
       ↓
  Voice Agent
       ↓
   LiveKit Room
       ↓
User Speaker
```

Your project uses:

**LiveKit Agents SDK**

and

**LiveKit Cloud**

for real-time audio/video room infrastructure. turn0file0 turn0file0

---

# 17. What is the Frontend?

Your frontend is basically the **visual interface** of F.R.I.D.A.Y.

It uses:

- React 19
- TypeScript
- Vite 8
- LiveKit React Components
- Lucide React

turn0file0

The user can:

1. Enter room name
2. Enter identity
3. Get LiveKit token
4. Connect to the assistant
5. See audio visualization
6. Use quick commands

---

# 18. Frontend Architecture

The frontend works approximately like this:

```text
                 React Frontend
                       │
              Enter Room + Identity
                       │
                       ▼
                Token Server
                       │
                  JWT Token
                       │
                       ▼
                LiveKit Cloud
                       │
                       ▼
                 Voice Agent
```

The documentation specifies that the frontend requests a JWT from the token server and then connects to LiveKit Cloud. turn0file0

---

# 19. What is the Token Server?

The token server is a small backend service.

Its job is to generate a:

**JWT = JSON Web Token**

for LiveKit authentication.

The frontend sends:

```text
GET /api/token
```

and receives:

```text
JWT Token
+
WebSocket URL
```

Then the frontend uses those credentials to connect to LiveKit.

---

# 20. Backend Architecture

Your backend has three major pieces:

```text
                BACKEND
                   │
       ┌───────────┼────────────┐
       │           │            │
       ▼           ▼            ▼
 Voice Agent   MCP Server   Token Server
 LiveKit       FastMCP      aiohttp
```

### Voice Agent

Responsible for:

- Audio
- STT
- LLM
- TTS
- Tool calling

### MCP Server

Responsible for:

- News
- Web search
- URL fetching
- System information
- Utilities
- Prompts
- Resources

### Token Server

Responsible for:

- LiveKit authentication

---

# 21. Why FastMCP?

FastMCP is the framework used to build your MCP server.

Instead of writing one huge backend, you can expose individual tools.

For example:

```python
def get_current_time():
    ...
```

or:

```python
def search_web(query):
    ...
```

The LLM can then access those tools through MCP.

---

# 22. Why is your project modular?

This is another important viva point.

Suppose tomorrow you want to add:

```text
weather_tool.py
```

You don't have to completely rewrite your application.

The documentation says a new MCP tool can be added by creating a file inside:

```text
friday/tools/
```

and defining/registering:

```text
register(mcp)
```

turn0file0

So the architecture is:

```text
friday/tools/

    news.py
    web.py
    system.py
    utilities.py
    weather.py       ← new tool
```

This makes the project **extensible**.

---

# 23. Provider Agnostic Architecture

This is a major feature.

You aren't permanently tied to one AI provider.

For example:

### STT

```text
Sarvam
   OR
Whisper
```

### LLM

```text
Gemini
   OR
GPT-4o
```

### TTS

```text
OpenAI TTS
   OR
Sarvam
```

So conceptually:

```text
              F.R.I.D.A.Y.
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
      STT         LLM         TTS
       │           │           │
   Sarvam/      Gemini/     OpenAI/
   Whisper      GPT-4o      Sarvam
```

The documentation says providers can be changed through configuration rather than rewriting the core application. turn0file0

---

# 24. Complete Project Workflow

This is the **most important thing to understand for your presentation**.

Suppose you say:

> **"Friday, give me today's world news."**

### Step 1 — User speaks

```text
🎙️ User
"Friday, give me today's world news."
```

### Step 2 — LiveKit receives audio

```text
Microphone
    ↓
LiveKit
```

### Step 3 — VAD detects speech

```text
Silero VAD
    ↓
Speech detected
```

### Step 4 — STT converts speech to text

```text
Audio
 ↓
Sarvam / Whisper
 ↓
"Give me today's world news."
```

### Step 5 — LLM understands request

```text
Gemini / GPT
       ↓
"I need current news."
```

### Step 6 — LLM requests MCP tool

```text
LLM
 ↓
MCP
 ↓
get_world_news()
```

### Step 7 — MCP retrieves RSS feeds

```text
             MCP
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
    BBC      CNBC     NYT
              │
              ▼
          Al Jazeera
```

### Step 8 — News results return

```text
RSS
 ↓
MCP
 ↓
Voice Agent
```

### Step 9 — LLM creates summary

```text
News Articles
     ↓
    LLM
     ↓
3–5 sentence briefing
```

### Step 10 — TTS converts response

```text
Text
 ↓
OpenAI TTS / Sarvam
 ↓
Audio
```

### Step 11 — User hears answer

```text
🔊 "Here are today's major world headlines..."
```

This complete flow is represented by the project's Level 1 and Level 2 DFDs. turn0file0

---

# 25. Understanding the DFD

Your documentation contains **three levels of Data Flow Diagrams**.

## Level 0 — Context Diagram

This shows the entire project as **one system**.

```text
             User
              │
              ▼
        ┌─────────────┐
        │   F.R.I.D.A.Y│
        └─────────────┘
          │    │    │
          ▼    ▼    ▼
        News  AI   World
        RSS  APIs  Monitor
```

It answers:

> **Who interacts with the system and what external systems are involved?**

The documented Level 0 includes the User, RSS feeds, LiveKit Cloud, AI providers and World Monitor. turn0file0

---

# 26. Level 1 DFD

Level 1 breaks F.R.I.D.A.Y. into major components:

```text
F.R.I.D.A.Y.
     │
     ├── 1. Voice Agent
     │
     ├── 2. MCP Server
     │
     ├── 3. Token Server
     │
     └── 4. Frontend UI
```

This gives a much clearer architectural picture.

---

# 27. Level 2 DFD

Level 2 goes even deeper.

For the Voice Agent:

```text
Audio Input
    ↓
VAD
    ↓
STT
    ↓
LLM
    ↓
Tool Dispatcher
    ↓
TTS
    ↓
Audio Output
```

For MCP:

```text
MCP Request
     ↓
Request Router
     ↓
 ┌───┼────┬────┬────┐
 ▼   ▼    ▼    ▼    ▼
Web System Utility Prompt Resource
Tools Tools  Tools
```

This is useful for explaining the **internal working** of the system.

---

# 28. Use Case Diagram

The use case diagram answers:

> **"What can each type of user do with the system?"**

There are two main actors:

### User

Can:

- Talk to F.R.I.D.A.Y.
- Get news
- Search web
- Fetch URLs
- Get current time
- Get system information
- Format JSON
- Count words
- Use web playground
- Summarize text
- Explain code

### Developer/Admin

Can:

- Add new MCP tools
- Change AI providers

turn0file0

---

# 29. Technology Stack — Easy Way to Remember

For your viva, remember this:

| Layer | Technology |
|---|---|
| Programming | Python |
| Backend MCP | FastMCP |
| Voice | LiveKit Agents |
| STT | Sarvam / Whisper |
| LLM | Gemini / GPT-4o |
| TTS | OpenAI / Sarvam |
| VAD | Silero |
| Frontend | React |
| Language | TypeScript |
| Build Tool | Vite |
| Token Server | aiohttp |
| HTTP | httpx |
| Environment | python-dotenv |
| Package Manager | uv |
| Real-time | WebSocket |
| MCP Transport | SSE |
| News | RSS/XML |
| Cloud | LiveKit Cloud |

These technologies and roles are documented in the project's technology stack sections. turn0file0

---

# 30. Non-functional requirements

These are **not features**, but quality requirements.

For example:

### Performance

The target is:

> Voice input → voice output in under 2 seconds for typical queries.

### Reliability

If a news feed doesn't respond, the application should report the failure rather than crash.

### Security

API keys should not be directly written in the source code.

Instead:

```text
.env
```

should contain credentials.

### Extensibility

New MCP tools should be addable without changing the core architecture.

### Usability

The React frontend should work across modern desktop browsers.

turn0file0

---

# 31. Very important: `.env`

Your project uses environment variables for API keys.

Conceptually:

```text
.env

GEMINI_API_KEY=xxxxx
OPENAI_API_KEY=xxxxx
LIVEKIT_API_KEY=xxxxx
LIVEKIT_API_SECRET=xxxxx
```

Then Python loads them using:

```text
python-dotenv
```

The benefit is:

```text
❌ Don't:
API_KEY = "my-secret-key"

✅ Do:
API_KEY = environment_variable
```

This prevents credentials from being hard-coded into the application. turn0file0

---

# 32. One simple real-world analogy

Imagine F.R.I.D.A.Y. as a human assistant.

### Ears 👂

**STT**

Listens to you.

### Brain 🧠

**LLM**

Understands your request and decides what to do.

### Hands 🔧

**MCP Tools**

Perform actions such as:

- Search web
- Get news
- Read webpage
- Check system
- Open dashboard

### Mouth 🗣️

**TTS**

Speaks the answer.

### Telephone/Communication Network 📡

**LiveKit**

Handles real-time audio communication.

So:

```text
             F.R.I.D.A.Y.

        👂 STT
          ↓
       🧠 LLM
          ↓
     🔧 MCP Tools
          ↓
       🧠 LLM
          ↓
       🗣️ TTS
```

---

# 33. 30-second explanation for your presentation

If your professor asks:

> **"Explain your project."**

You can say:


Our project is F.R.I.D.A.Y., which stands for Fully Responsive Intelligent Digital Assistant for You. It is an AI-powered, voice-controlled assistant inspired by the F.R.I.D.A.Y. assistant from Iron Man.

The system takes voice input from the user, converts speech into text using Speech-to-Text technology, processes the request using an LLM such as Gemini or GPT-4o, and converts the generated response back into speech using Text-to-Speech.

A major feature of our project is the Model Context Protocol, or MCP. MCP allows the AI to dynamically use external tools such as web search, live news retrieval, URL fetching, system information, and the World Monitor dashboard.

The system uses LiveKit for real-time voice communication, FastMCP for the MCP server, Python for the backend, and React with TypeScript for the frontend. The architecture is modular and provider-independent, so different STT, LLM, and TTS providers can be configured without changing the core system.


---

# 34. Most important viva questions

### Q1. What is F.R.I.D.A.Y.?

**Answer:**  
F.R.I.D.A.Y. stands for **Fully Responsive Intelligent Digital Assistant for You**. It is a customizable AI-powered voice assistant.

### Q2. What is the main purpose?

**Answer:**  
To provide real-time voice interaction with an LLM and allow the LLM to dynamically use external tools.

### Q3. What is MCP?

**Answer:**  
MCP stands for **Model Context Protocol**. It provides a standardized mechanism for connecting an LLM with external tools, prompts and resources.

### Q4. Why did you use MCP?

**Answer:**  
To make the AI assistant extensible. New capabilities can be added as independent tools without modifying the entire core application.

### Q5. What is STT?

**Answer:**  
Speech-to-Text converts the user's spoken audio into text.

### Q6. What is TTS?

**Answer:**  
Text-to-Speech converts the AI-generated text into spoken audio.

### Q7. What is VAD?

**Answer:**  
Voice Activity Detection identifies when the user is speaking and separates speech from silence.

### Q8. Why use LiveKit?

**Answer:**  
LiveKit provides real-time audio communication and streaming between the user and voice agent.

### Q9. What is the role of the LLM?

**Answer:**  
The LLM understands the user's request, generates responses and determines when external tools are needed.

### Q10. What is FastMCP?

**Answer:**  
FastMCP is the framework used to implement the MCP server and expose tools, prompts and resources.

### Q11. What is the role of React?

**Answer:**  
React is used to create the web-based frontend/playground interface.

### Q12. Why use multiple AI providers?

**Answer:**  
It provides flexibility. The project can switch between different STT, LLM and TTS providers through configuration.

---

## ⭐ The one diagram you should memorize

If you remember only **one diagram**, remember this:

```text
                    👤 USER
                       │
                       │ Voice
                       ▼
                 ☁️ LIVEKIT
                       │
                       ▼
                 🎙️ VAD
                       │
                       ▼
                 📝 STT
              Sarvam / Whisper
                       │
                       ▼
                  🧠 LLM
             Gemini / GPT-4o
                       │
                ┌──────┴──────┐
                │             │
          Direct Answer    Need Tool?
                              │
                              ▼
                         🔧 MCP SERVER
                         /     |      \
                        /      |       \
                     📰 News  🌐 Web  💻 System
                        \      |       /
                         \     |      /
                              ▼
                           Result
                              │
                              ▼
                           🧠 LLM
                              │
                              ▼
                            🔊 TTS
                       OpenAI / Sarvam
                              │
                              ▼
                           ☁️ LIVEKIT
                              │
                              ▼
                          👤 USER
```

**In simple words:**

> **LiveKit handles the real-time voice → VAD detects speech → STT converts speech to text → LLM understands and reasons → MCP provides external tools → LLM generates the final response → TTS converts it into voice → LiveKit sends it back to the user.**

That is the **core of your entire F.R.I.D.A.Y. project**.

---

If you want, I can:

- Continue explaining MCP protocol
- Explain key viva questions answers
- Describe the interaction flow with external tools