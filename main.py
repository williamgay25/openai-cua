import subprocess
import time
import base64
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    api_key = input("Enter your OpenAI API key: ")

client = OpenAI(api_key=api_key)

def docker_exec(cmd: str, container_name: str, decode=True) -> str:
    """Executes a command inside a Docker container."""
    try:
        docker_cmd = f'docker exec {container_name} sh -c "{cmd}"'
        output = subprocess.check_output(docker_cmd, shell=True)
        return output.decode("utf-8", errors="ignore") if decode else output
    except subprocess.CalledProcessError as e:
        print(f"Error executing command '{cmd}': {e}")
        return ""


class VM:
    """Represents a virtual machine running inside a Docker container."""
    def __init__(self, display: str, container_name: str):
        self.display = display
        self.container_name = container_name


def get_screenshot(vm: VM) -> bytes:
    """Captures a screenshot from the VM and returns raw image bytes."""
    cmd = f"DISPLAY={vm.display} import -window root png:-"
    return docker_exec(cmd, vm.container_name, decode=False)


def handle_model_action(vm: VM, action):
    """Executes the corresponding action inside the VM."""
    try:
        if action.type == "click":
            x, y = int(action.x), int(action.y)
            button_map = {"left": 1, "middle": 2, "right": 3}
            button = button_map.get(action.button, 1)
            docker_exec(f"DISPLAY={vm.display} xdotool mousemove {x} {y} click {button}", vm.container_name)

        elif action.type == "scroll":
            x, y = int(action.x), int(action.y)
            scroll_y = int(action.scroll_y)
            docker_exec(f"DISPLAY={vm.display} xdotool mousemove {x} {y}", vm.container_name)
            button = 4 if scroll_y < 0 else 5
            for _ in range(abs(scroll_y)):
                docker_exec(f"DISPLAY={vm.display} xdotool click {button}", vm.container_name)

        elif action.type == "keypress":
            for key in action.keys:
                key = "Return" if key.lower() == "enter" else key
                docker_exec(f"DISPLAY={vm.display} xdotool key '{key}'", vm.container_name)

        elif action.type == "type":
            docker_exec(f"DISPLAY={vm.display} xdotool type '{action.text}'", vm.container_name)

        elif action.type == "wait":
            time.sleep(2)

        elif action.type == "screenshot":
            pass  # Handled separately

        else:
            print(f"Unrecognized action: {action}")

    except Exception as e:
        print(f"Error handling action {action}: {e}")


def computer_use_loop(vm: VM, response):
    """Loops through and executes computer actions until none remain."""
    while True:
        computer_calls = [item for item in response.output if item.type == "computer_call"]
        if not computer_calls:
            print("No computer call found. Model output:")
            for item in response.output:
                print(item)
            break

        action = computer_calls[0].action
        last_call_id = computer_calls[0].call_id

        handle_model_action(vm, action)
        time.sleep(1)

        screenshot_bytes = get_screenshot(vm)
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        response = client.responses.create(
            model="computer-use-preview",
            previous_response_id=response.id,
            tools=[
                {
                    "type": "computer_use_preview",
                    "display_width": 1024,
                    "display_height": 768,
                    "environment": "browser",
                }
            ],
            input=[
                {
                    "call_id": last_call_id,
                    "type": "computer_call_output",
                    "output": {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{screenshot_base64}",
                    },
                }
            ],
            truncation="auto",
        )

    return response


if __name__ == "__main__":
    vm_instance = VM(display=":99", container_name="cua-image")
    user_input = input("Enter command or action: ")
    response = client.responses.create(model="computer-use-preview", input=[{"type": "text", "text": user_input}])
    computer_use_loop(vm_instance, response)
