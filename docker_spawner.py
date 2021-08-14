from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import uvicorn
# web page, table
from fastapi.responses import HTMLResponse
import datetime
import secrets
import random
import datetime
from requests import get

# docker
import docker 

# server config
import server_config

app = FastAPI()

# handling cors
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# port use
def is_port_in_use(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


app.ip = get('https://api.ipify.org').text


ports = server_config.ports
ports_ = []
for port in ports:
    if "-" in port:
        p1, p2 = port.split('-')
        ports_.extend(list(range(int(p1), int(p2) + 1)))
    else:
        ports_.append(int(port))
# refine ports
app.ports = []
for port in ports_:
    if not is_port_in_use(port):
        app.ports.append(port)

app.ports = list(set(app.ports))

print(f"available ports: {app.ports}")

app.client = docker.from_env()

print(f"docker client: {app.client}")

print(f"host ip: {app.ip}")

class User(BaseModel):
    username: str
    password: str


@app.get("/")
def read_root(): # will change later, security flaws
    return {"msg": "The server is live!", "success": 1}

# route for getting recomendation just from an user id without any additional data
# returns a list of video 
@app.get("/run_image/{image_id}")
def user_recom(image_id: str, user: User, request: Request):
    client_host = request.client.host
    dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # log the client host
    ip_logger = open("ip_logger.txt", "a+")
    ip_logger.write(f"{client_host}, {dt}.")
    correct_username = secrets.compare_digest(user.username, server_config.uname)
    correct_password = secrets.compare_digest(user.password, server_config.pword)
    if not (correct_username and correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Basic"},
            )
    else:
        try:
            if image_id in server_config.image_paths:
                # build the image first, will optimize later

                build_r = app.client.images.build(path = server_config.image_paths[image_id], tag = f'{server_config.uname}/{image_id}:latest')
                r_port = random.sample(app.ports, 1)[0]
                
                app.client.containers.run(build_r[0].tags[0], ports = {'5000/tcp': r_port}, detach = True) # all the apps internally runs on port 5000

                app.ports.remove(r_port) # remove ports if the running is successful

                return {'msg': f'The app is running on {app.ip}:{r_port}', 'url': f'http://{app.ip}:{r_port}'}
        except:
            return {'msg': 'Could not perform the operation.'}




if __name__ == '__main__':
    uvicorn.run(app, port=80, host='0.0.0.0')