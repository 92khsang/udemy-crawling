# 📘 Udemy to Notion WebSocket Sync

This project implements an **async WebSocket server** that receives Udemy lecture transcript data and automatically creates structured lecture pages in **Notion**. It parses and formats section/lecture metadata, handles large transcripts by chunking them, and integrates seamlessly with the Notion API.

---

## 🔧 Features

* 📡 WebSocket server for receiving transcript data
* 🧵 Async message queuing and processing
* 🧱 Automatic creation of **Notion pages** for Udemy sections and lectures
* 🪄 Smart parsing and formatting of raw titles using `TitleSet`
* 🧩 Large transcript handling via automatic chunking (`2000 chars max`)
* 📝 Structured logging for debugging and monitoring

---

## 📦 Requirements

* Python 3.10+
* Valid Notion integration token and database ID
* Dependencies managed via Poetry or `pip install -r requirements.txt`

---

## 🚀 Running the Server

```bash
python -m udemy_crawling \
  --notion-token "<YOUR_NOTION_TOKEN>" \
  --database-id "<YOUR_DATABASE_ID>" \
  --websocket-port 8765
```

> The server will start listening on `ws://localhost:8765`.

---

## 📤 WebSocket Message Format

Send JSON messages structured like this:

```json
{
  "action": "save_transcript",
  "messageId": "uuid-1234",
  "raw_section": "Section 3: Advanced Topics",
  "raw_lecture": "12. Building WebSocket Clients",
  "transcripts": [
    "Welcome to the lecture...",
    "Let's start with WebSockets..."
  ]
}
```

---

## 🧠 How It Works

1. **WebSocket handler** receives a `save_transcript` action.
2. The `UdemyLecture` model parses:

   * `raw_section` → ➜ `section = TitleSet(name='Advanced Topics', number=3)`
   * `raw_lecture` → ➜ `lecture = TitleSet(name='Building WebSocket Clients', number=12)`
   * `transcripts` → ➜ `chunks = [chunk1, chunk2, ...]` with max width 2000 characters
3. It enqueues the lecture for processing.
4. The queue worker:

   * Creates the section page if missing
   * Links lecture to the section
   * Renders transcript chunks as collapsible code blocks in Notion

---

## 🗂 Key Components

| Module                | Responsibility                                    |
| --------------------- | ------------------------------------------------- |
| `server.py`           | WebSocket setup and lifecycle                     |
| `queue_handler.py`    | Manages message queue and Notion task processor   |
| `notion/creator.py`   | Creates and links lecture/section pages in Notion |
| `models.UdemyLecture` | Parses and normalizes incoming transcript data    |

---

## ✅ Notable Design Patterns

* **Hexagonal Architecture**: separates infrastructure (WebSocket), domain (`UdemyLecture`, `NotionClient`), and application logic.
* **Cached Properties**: efficient parsing of section/lecture metadata with `@cached_property`
* **Error Isolation**: decouples WebSocket I/O from Notion logic for resilience
* **Structured Logging**: human-readable logs with emoji-level debugging clarity

