from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import subprocess
import json

def get_devices():

    result = []

    process = subprocess.run("/usr/bin/lsblk --json -o NAME,MOUNTPOINT,SIZE,FSTYPE".split(),
                            capture_output=True, text=True)

    output = json.loads(process.stdout)["blockdevices"]

    for device in output:
        
        if device["name"].startswith("loop") or device["name"].startswith("sr"):
            continue
    
        if "children" in device:
            for child in device["children"]:
                result.append(child)
        else:
            result.append(device)

    return result


### Initialization ### 

app = FastAPI()
templates = Jinja2Templates(directory='templates')


### Endpoints ###

@app.get("/", response_class=HTMLResponse)
def disks_page(request: Request):
    devices = get_devices()
    return templates.TemplateResponse("disks.html", {"request" : request, "devices": devices})

@app.post("/mount/{name}")
def mount_disk(name: str, request: Request, mountpoint: str = Form(...)):
    try:
        subprocess.run(["mkdir", "-p", mountpoint], check=True, capture_output=True, text=True)
        subprocess.run(["mount", f"/dev/{name}", mountpoint], check=True, capture_output=True, text=True)
        return RedirectResponse(url="/", status_code=303)
    except subprocess.CalledProcessError as e:
        devices = get_devices()
        error_msg = e.stderr if e.stderr else str(e)
        return templates.TemplateResponse("disks.html", {
            "request": request,
            "devices": devices,
            "error": error_msg
    })

@app.post("/unmount/{name}")
def unmount_disk(name: str, request: Request):
    try: 
        subprocess.run(["umount", f"/dev/{name}"], check=True, capture_output=True, text=True)
        return RedirectResponse(url="/", status_code=303)
    except subprocess.CalledProcessError as e:
        devices = get_devices()
        error_msg = e.stderr if e.stderr else str(e)
        return templates.TemplateResponse("disks.html", {
            "request": request,
            "devices": devices,
            "error": error_msg
    })

@app.post("/format_disk/{name}")
def format_disk(name: str, request: Request, fstype: str = Form(...)):
    try:
        cmd = ["mkfs", "-t", fstype]

        if fstype == "ext4":
            cmd.append("-F")
        else:
            cmd.append("-f")

        cmd.append(f"/dev/{name}")

        subprocess.run(cmd, check=True, capture_output=True, text=True)

        devices = get_devices()
        return templates.TemplateResponse("disks.html", {
            "request": request,
            "devices": devices,
            "message": f"Диск {name} успешно отформатирован в {fstype}"
        })

    except subprocess.CalledProcessError as e:
        devices = get_devices()
        error_msg = e.stderr if e.stderr else str(e)
        return templates.TemplateResponse("disks.html", {
            "request": request,
            "devices": devices,
            "error": error_msg
        })


    