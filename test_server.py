import json, requests, time, subprocess, os, sys

base = r'D:\26-1\Canchasí\prueba safepath'
python = os.path.join(base, 'venv', 'Scripts', 'python.exe')
server_script = os.path.join(base, 'safepath_mvp', 'server.py')

server_proc = subprocess.Popen([python, server_script], cwd=os.path.join(base, 'safepath_mvp'))
time.sleep(3)
print('Servidor iniciado\n')

formatos = [
    {'ax': 2.1, 'ay': 0.3, 'az': 9.8},
    {'accelerometerAccelerationX': 2.1, 'accelerometerAccelerationY': 0.3, 'accelerometerAccelerationZ': 9.8},
    {'x': 2.1, 'y': 0.3, 'z': 9.8},
    {'payload': {'x': 2.1, 'y': 0.3, 'z': 9.8}},
    [{'x': 0.5, 'y': 0.1, 'z': 9.7}, {'x': 2.1, 'y': 0.3, 'z': 9.8}],
    {'ax': 25.0, 'ay': 5.0, 'az': 3.0},
]

print('=' * 60)
for i, fmt in enumerate(formatos):
    try:
        r = requests.post('http://localhost:5000/sensor', json=fmt, timeout=2)
        short = json.dumps(fmt)[:80]
        print(f'[Test {i+1}] {short}')
        print(f'          -> {r.status_code}  {r.json()}\n')
    except Exception as e:
        print(f'[Test {i+1}] ERROR: {e}\n')

r = requests.get('http://localhost:5000/state')
print(f'Estado final: {r.json()}')

server_proc.terminate()
server_proc.wait()
