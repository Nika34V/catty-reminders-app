import os
import subprocess
import threading
import logging
from flask import Flask, request, jsonify

class WebhookHandler:
    """Класс для обработки вебхуков GitHub и автоматического деплоя."""
    
    def __init__(self, repo_dir, env_file, service_name, log_file):
        self.repo_dir = repo_dir
        self.env_file = env_file
        self.service_name = service_name
        self.logger = self._setup_logger(log_file)
        self.app = Flask(__name__)
        self._register_routes()

    def _setup_logger(self, log_file):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _register_routes(self):
        @self.app.route('/', methods=['POST'])
        def handle():
            if request.headers.get('X-GitHub-Event') == 'push':
                sha = request.json.get('after')
                if sha and sha != "0000000000000000000000000000000000000000":
                    threading.Thread(target=self._run_deploy, args=(sha,)).start()
                    return jsonify({"status": "ok"}), 202
            return jsonify({"status": "ignored"}), 200

    def _run_deploy(self, sha):
        try:
            # 1. Обновляем код
            subprocess.run(["git", "-C", self.repo_dir, "fetch", "--all"], check=True)
            subprocess.run(["git", "-C", self.repo_dir, "reset", "--hard", sha], check=True)
            
            # 2. Пишем хэш в файл окружения
            with open(self.env_file, "w") as f:
                f.write(f"DEPLOY_REF={sha}\n")
            
            # 3. Перезапускаем сервис
            subprocess.run(["sudo", "systemctl", "restart", self.service_name], check=True)
            
            self.logger.info(f"Successfully deployed commit {sha}")
        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")

    def run(self, host='0.0.0.0', port=8080):
        self.app.run(host=host, port=port)


if __name__ == '__main__':
    handler = WebhookHandler(
        repo_dir="/home/password_123/catty-reminders-app",
        env_file="/etc/catty-app-env",
        service_name="catty",
        log_file="/home/password_123/deploy.log"
    )
    handler.run()
