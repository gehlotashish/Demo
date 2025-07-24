import datetime
 
def log_error(msg: str):
    with open('error.log', 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n") 