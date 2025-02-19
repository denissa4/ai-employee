from flask import Flask, request, jsonify
from executor import execute_code

app = Flask(__name__)

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    user_code = data.get("code", "")

    if not user_code:
        return jsonify({"error": "No code provided"}), 400

    output = execute_code(user_code)
    return jsonify({"output": output})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
