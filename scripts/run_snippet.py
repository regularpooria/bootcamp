# import subprocess, logging

# def run_code(code):
#     with open("/tmp/temp_code.py", "w") as f:
#         f.write(code)
#     result = subprocess.run([
#         "docker", "run", "--rm", "-v", "/tmp:/sandbox", "bootcamp-env",
#         "python", "/sandbox/temp_code.py"
#     ], capture_output=True, timeout=10)
#     logging.info("Output:%s", result.stdout.decode())
#     logging.error("Errors:%s", result.stderr.decode())
from podman import PodmanClient

def setup_podman():
    try:
        client = PodmanClient(base_url='unix:///run/user/1000/podman/podman.sock')
        client.ping()
        
        try:
            # Check if the container already exists
            container = client.containers.get("sandbox_container")
            if container.status != "running":
                print("Container is not running. Starting it...")
                container.start()

            return client, container
        except Exception:
            pass
        
        client.images.pull("python:3.9.19-slim")
        container = client.containers.create(
            image="python:3.9.19-slim",
            command=["tail", "-f", "/dev/null"],  # Keeps the container alive
            tty=True,
            name="sandbox_container",
            stdin_open=True,
            detach=True
        )
        
        container.start()
        
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Podman: {e}")
    
    return client, container

client, container = setup_podman()


def run_code(code):
    # Write code to a temp file inside the container
    escaped_code = code.replace('"', '\\"')  # Escape double quotes for shell
    container.exec_run(
        cmd=["sh", "-c", f'echo "{escaped_code}" > /tmp/temp_code.py'],
    )
    output = container.exec_run(
        ["python3", "/tmp/temp_code.py"],
        demux=True,
    )
    print("Output:", output)
    return output[1][0].decode("utf-8")

if __name__ == "__main__":
    code = "print('Hello, World!')"
    result = run_code(code)
    print("Output:", result)
    assert result == "Hello, World!\n"
    