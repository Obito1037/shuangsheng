import paramiko
import sys
import time

host = "8.148.69.255"
port = 22
username = "root"
password = "Zhang.3839963"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host}...")
    client.connect(host, port, username, password, timeout=10)
    print("Connected.")
    
    # 停止不需要的单独文件上传
    sftp = client.open_sftp()
    sftp.close()
    
    commands = [
        "cd /opt && rm -rf shuangsheng_tmp && git clone https://github.com/Obito1037/shuangsheng.git shuangsheng_tmp",
        "cp -r /opt/shuangsheng_tmp/backend/* /opt/echolearn/backend/",
        "cd /opt/echolearn/backend && if [ -d .venv ]; then source .venv/bin/activate; fi && pip install -r requirements.txt",
        "systemctl restart echolearn-backend",
        "systemctl status echolearn-backend --no-pager"
    ]
    
    for cmd in commands:
        print(f"Running: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if out: print(out)
        if err: print(f"ERROR: {err}")
        
except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
