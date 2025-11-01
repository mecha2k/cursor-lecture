# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Korean-language educational repository** focused on Python async programming, WebSockets, cryptography, and FastAPI. The project contains standalone tutorial files (01-06 series) that demonstrate progressively complex concepts through executable examples. All comments and documentation are written in Korean.

## Architecture

### File Organization Pattern

Files follow a numerical progression pattern indicating learning sequence:

- **01_asyncio_basics.py**: Foundation - coroutines, event loops, Task objects, timeouts, and cancellation
- **02_websocket_basics.py**: WebSocket server/client implementation, message broadcasting, connection management
- **03_realtime_chat.py**: Production-like chat system with user management, message history, heartbeat monitoring
- **04_advanced_websocket.py**: Real-time data streaming, aggregation, anomaly detection, server metrics
- **05_aes_*.py**: Three-part encryption series (basics, security practices, advanced patterns)
- **06_fastapi_*.py**: Four-part FastAPI series (basics, advanced features, database integration, auth/security, deployment)

### Key Architectural Patterns

**Async-First Design**: All networking code uses asyncio. The websocket modules implement:
- Connection pooling via `Dict[str, User/Connection]` tracking
- Broadcast patterns using `asyncio.gather()` for concurrent message delivery
- Heartbeat monitoring with background tasks
- Graceful shutdown handling with proper connection cleanup

**State Management**:
- ChatRoom class (03_realtime_chat.py) maintains user registry and message history as in-memory state
- Advanced examples use dataclasses (@dataclass) for structured data
- Enum classes define message types and states

**Error Handling Strategy**:
- Websocket exceptions caught at connection level, logged but don't crash server
- ValidationError for Pydantic models in FastAPI examples
- Specific exception types (ConnectionClosed, TimeoutError) handled individually

## Common Development Commands

### Running Examples

Each numbered file is independently executable. Most have interactive menus:

```bash
# Run asyncio basics (direct execution)
python 01_asyncio_basics.py

# Run websocket examples (direct execution with prompts)
python 02_websocket_basics.py

# Run chat application - will prompt for server (1) or client (2)
python 03_realtime_chat.py

# Run advanced websocket - prompts for server (1), basic client (2), or analytics client (3)
python 04_advanced_websocket.py

# FastAPI examples - starts uvicorn server, access docs at http://localhost:8000/docs
python 06_fastapi_basics.py
python 06_fastapi_advanced.py
python 06_fastapi_database.py
python 06_fastapi_auth_security.py
```

### Environment Setup

```bash
# Install all dependencies
pip install -r requirements.txt

# Key dependencies:
# - websockets>=11.0.0 for WebSocket implementation
# - fastapi>=0.104.0 + uvicorn[standard] for web API
# - cryptography>=41.0.0 for AES encryption
# - sqlalchemy>=2.0.0 for database ORM
# - pydantic>=2.0.0 for data validation
```

### Testing Client-Server Applications

When testing WebSocket examples (02, 03, 04):
1. Run server in one terminal: `python 0X_*.py` → select server option
2. Run client(s) in separate terminal(s): `python 0X_*.py` → select client option
3. Default port is usually 8765 for WebSocket, 8000 for FastAPI

## Critical Cursor Rules

This project has strict Cursor rules in `.cursor/rules/`:

### Type Safety & Error Handling (python-core.mdc)
- **MANDATORY**: Type hints for all function parameters and return types
- **MANDATORY**: Use `Optional[T]` for nullable values
- **NEVER**: Use bare `except:` - always catch specific exceptions
- **NEVER**: Use `Any` type unless absolutely necessary
- Follow PEP 8 strictly, 88 char line limit (Black formatter standard)

### Security (security.mdc)
- **MANDATORY**: Validate all user inputs at application boundaries
- **MANDATORY**: Use allowlists for validation, not blocklists
- **NEVER**: Use `eval()` or `exec()` with user data
- **NEVER**: Hardcode secrets, API keys, or passwords
- **NEVER**: Use `subprocess` with `shell=True` and user input
- **NEVER**: Use `pickle` with untrusted data
- For passwords: Always use bcrypt/scrypt/Argon2 (see security.mdc examples)
- For database: Always use parameterized queries (see security.mdc line 102-116)

### Performance (performance.mdc)
- **MANDATORY**: Use generators for large datasets, not lists
- **MANDATORY**: Use `async`/`await` for I/O-bound operations
- **MANDATORY**: Implement connection pooling for databases
- **NEVER**: Make synchronous calls in async functions
- **NEVER**: Use string concatenation in loops (use `join()`)
- Cache expensive computations with `functools.lru_cache`

## Code Conventions

### Import Organization
Standard library → Third-party → Local imports, separated by blank lines

### Function Docstrings
All public functions must have docstrings explaining:
- Purpose (Korean language acceptable)
- Args with types
- Returns with type
- Raises (if applicable)

### Async Patterns
- Use `asyncio.gather()` for concurrent operations
- Use `asyncio.create_task()` for fire-and-forget background tasks
- Always handle `asyncio.CancelledError` in long-running tasks
- Use `async with` for async context managers (WebSocket connections, database connections)

### WebSocket Connection Management
Pattern from 03_realtime_chat.py:
```python
async def handler(websocket: WebSocketServerProtocol):
    try:
        # Register connection
        await chat_room.add_user(websocket, username)
        # Message loop
        async for message in websocket:
            await process_message(message)
    except ConnectionClosed:
        logger.info("Connection closed")
    finally:
        # Always cleanup
        await chat_room.remove_user(websocket)
```

### FastAPI Patterns
- Use Pydantic models for request/response validation
- Use dependency injection for shared resources (see 06_fastapi_advanced.py)
- Use lifespan events (not deprecated @app.on_event) for startup/shutdown
- Enable automatic API docs at /docs and /redoc

## Development Notes

- **Python Version**: Requires Python 3.10+ (uses match statements and modern type hints)
- **Encoding**: All files use UTF-8, Korean characters are prevalent
- **Logging**: Uses Python logging module, configured at module level
- **Testing**: No test files present - examples are self-contained demonstrations
- **Database**: Examples use SQLite (aiosqlite) for demos, show patterns for PostgreSQL/MySQL/MongoDB
- **Security Demos**: AES examples (05_*) demonstrate proper cryptography patterns - do NOT modify encryption implementations without understanding security implications

## Common Issues

### Import Errors
If you see "No module named 'websockets'" or similar:
```bash
pip install websockets  # or the specific missing package
pip install -r requirements.txt  # install all at once
```

### Connection Refused
- Verify server is running before starting client
- Check port numbers match between server and client (default: 8765 for WebSocket, 8000 for FastAPI)

### Memory Growth
- Message history is limited (max_history = 100 in ChatRoom)
- Long-running servers may need periodic connection cleanup
- Monitor with metrics patterns shown in 04_advanced_websocket.py

## Reference Documentation

Code examples align with official documentation for:
- Python asyncio: https://docs.python.org/3/library/asyncio.html
- websockets library: https://websockets.readthedocs.io/
- FastAPI: https://fastapi.tiangolo.com/
- cryptography library: https://cryptography.io/
- SQLAlchemy: https://docs.sqlalchemy.org/
