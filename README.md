Minimal execution of test task requirements

API has protocols of Graceful shutdown, broadcasting, and SIGTERM processing (SIGTERM is called shutdown_initiated)

runnable by 

```
uvicorn main:app --workers 1
```
