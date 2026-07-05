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
    
    # SFTP 上传修改过的后端文件
    sftp = client.open_sftp()
    files_to_upload = [
        ("backend/app/api/auth.py", "/opt/echolearn/backend/app/api/auth.py"),
        ("backend/app/services/auth_service.py", "/opt/echolearn/backend/app/services/auth_service.py")
    ]
    
    for local_path, remote_path in files_to_upload:
        print(f"Uploading {local_path} to {remote_path}...")
        try:
            sftp.put(local_path, remote_path)
            print("Done.")
        except Exception as e:
            print(f"Failed to upload {local_path}: {e}")
            
    sftp.close()
    
    commands = [
        "apt-get update && apt-get install -y nginx",
        "echo 'server { listen 80; server_name _; location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; } }' > /etc/nginx/sites-available/default",
        "systemctl restart nginx",
        "sed -i 's/127.0.0.1/0.0.0.0/g' /etc/systemd/system/echolearn-backend.service",
        "systemctl daemon-reload",
        "systemctl restart echolearn-backend"
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
