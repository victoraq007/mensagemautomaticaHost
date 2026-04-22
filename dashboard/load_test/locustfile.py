from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        # O sistema usa autenticação via session cookie ou form.
        # Simulando uma chamada à página de login
        # Assuma que a senha está configurada como 'admin' localmente, ou ajuste conforme a variável
        response = self.client.post("/login", data={"password": "sua-senha-aqui"})
        
    @task(3)
    def index_page(self):
        self.client.get("/")

    @task(2)
    def api_stats(self):
        self.client.get("/api/stats")

    @task(2)
    def api_tasks(self):
        self.client.get("/api/tasks")

    @task(2)
    def api_groups(self):
        self.client.get("/api/groups")

    @task(1)
    def export_endpoint(self):
        self.client.get("/api/export")
