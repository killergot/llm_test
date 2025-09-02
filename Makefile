# Сборка Docker-образа
build:
	docker build -t fastapi-app:latest .

# Запуск Minikube и применение манифестов
up: build
	minikube start
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/service.yaml

# Остановка Minikube
down:
	kubectl delete -f k8s/deployment.yaml
	kubectl delete -f k8s/service.yaml
	minikube stop

# Смотрим логи подов
logs:
	kubectl logs -l app=fastapi-app -f

# Получить доступ к сервису
service:
	minikube service fastapi-service